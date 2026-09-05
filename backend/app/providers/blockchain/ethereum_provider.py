"""Ethereum (Sepolia) blockchain provider using Web3.py.

All credentials come from environment variables — never hardcoded.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.core.exceptions import BlockchainError, BlockchainNotConfiguredError, RecordNotFoundError
from app.core.logging import get_logger
from app.models.domain import BlockchainRecord
from app.providers.blockchain.base import BlockchainProvider

log = get_logger(__name__)

# Pre-compiled ABI (matches VerificationRegistry.sol)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_fingerprint", "type": "bytes32"},
            {"internalType": "string", "name": "_sourceUrl", "type": "string"},
        ],
        "name": "registerRecord",
        "outputs": [{"internalType": "bytes32", "name": "recordId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_recordId", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "bytes32", "name": "fingerprint", "type": "bytes32"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_recordId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "_fingerprint", "type": "bytes32"},
        ],
        "name": "verifyFingerprint",
        "outputs": [{"internalType": "bool", "name": "verified", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "recordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "recordId", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "fingerprint", "type": "bytes32"},
            {"indexed": False, "internalType": "string", "name": "sourceUrl", "type": "string"},
            {"indexed": True, "internalType": "address", "name": "submitter", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "RecordRegistered",
        "type": "event",
    },
]

SEPOLIA_EXPLORER = "https://sepolia.etherscan.io"


def _hex(value) -> str:
    """Normalise bytes / HexBytes / str to bare lowercase hex with no 0x prefix.

    hexbytes >= 2.0 returns HexBytes.hex() without the 0x prefix, but 1.x returned
    it *with* one, and hexbytes is a transitive dependency we do not pin directly.
    Normalising here keeps on-chain values comparable to our bare SHA-256 hex
    regardless of which version resolves.
    """
    if isinstance(value, str):
        raw = value
    elif hasattr(value, "hex"):
        raw = value.hex()
    else:
        raw = bytes(value).hex()
    return raw.removeprefix("0x").removeprefix("0X").lower()


class EthereumProvider(BlockchainProvider):
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        chain_id: int = 11155111,
        timeout: int = 120,
    ):
        if not all([rpc_url, private_key, contract_address]):
            raise BlockchainNotConfiguredError()

        self._rpc_url = rpc_url
        self._private_key = private_key
        self._contract_address = contract_address
        self._chain_id = chain_id
        self._timeout = timeout

        self._w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": timeout}))
        # POA middleware for testnets
        self._w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self._account = self._w3.eth.account.from_key(private_key)
        self._contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=CONTRACT_ABI,
        )

    async def health_check(self) -> str:
        try:
            connected = await asyncio.to_thread(self._w3.is_connected)
            return "connected" if connected else "disconnected"
        except Exception:
            return "disconnected"

    async def register_fingerprint(self, fingerprint_hex: str, source_url: str) -> BlockchainRecord:
        t0 = time.perf_counter()

        fp_bytes = bytes.fromhex(fingerprint_hex)
        if len(fp_bytes) != 32:
            raise BlockchainError("Fingerprint must be exactly 32 bytes (64 hex chars).")

        try:
            nonce = await asyncio.to_thread(
                self._w3.eth.get_transaction_count, self._account.address
            )

            tx = self._contract.functions.registerRecord(
                fp_bytes, source_url
            ).build_transaction({
                "chainId": self._chain_id,
                "from": self._account.address,
                "nonce": nonce,
                "gas": 300_000,
                "gasPrice": await asyncio.to_thread(self._w3.eth.gas_price.__int__) if hasattr(self._w3.eth.gas_price, '__int__') else await asyncio.to_thread(lambda: self._w3.eth.gas_price),
            })

            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
            tx_hash = await asyncio.to_thread(
                self._w3.eth.send_raw_transaction, signed.raw_transaction
            )

            log.info("Blockchain tx submitted: %s", tx_hash.hex())

            receipt = await asyncio.to_thread(
                self._w3.eth.wait_for_transaction_receipt, tx_hash, timeout=self._timeout
            )

            # A reverted tx still produces a receipt. Without this check a revert
            # would be reported as a successful registration.
            if receipt.get("status") != 1:
                raise BlockchainError(
                    f"Transaction 0x{_hex(tx_hash)} reverted on-chain "
                    f"(status={receipt.get('status')}, block {receipt['blockNumber']})."
                )

            # Extract recordId from the event log. This is the ONLY way to obtain it —
            # the contract computes it as keccak256(fingerprint, sender, block.timestamp),
            # which we cannot reproduce off-chain (we do not know the block timestamp).
            # Failing to decode it means the record can never be read back, so this is
            # a hard error rather than something to swallow.
            logs = self._contract.events.RecordRegistered().process_receipt(receipt)
            if not logs:
                raise BlockchainError(
                    f"Transaction 0x{_hex(tx_hash)} succeeded but emitted no "
                    "RecordRegistered event; the record id cannot be recovered."
                )
            record_id = _hex(logs[0]["args"]["recordId"])

            elapsed = (time.perf_counter() - t0) * 1000

            return BlockchainRecord(
                network="sepolia",
                record_id=record_id,
                transaction_hash=_hex(tx_hash),
                block_number=receipt["blockNumber"],
                fingerprint=_hex(fingerprint_hex),
                source_url=source_url,
                timestamp=int(time.time()),
                submitter=self._account.address,
                explorer_url=f"{SEPOLIA_EXPLORER}/tx/0x{_hex(tx_hash)}",
                submission_time_ms=round(elapsed, 1),
            )

        except BlockchainError:
            raise
        except Exception as exc:
            log.error("Blockchain registration failed: %s", exc)
            raise BlockchainError(f"Blockchain transaction failed: {exc}") from exc

    async def get_record(self, record_id: str) -> BlockchainRecord:
        try:
            rid_bytes = bytes.fromhex(_hex(record_id))
            result = await asyncio.to_thread(
                self._contract.functions.getRecord(rid_bytes).call
            )
            fingerprint, source_url, timestamp, submitter = result

            return BlockchainRecord(
                network="sepolia",
                record_id=_hex(record_id),
                fingerprint=_hex(fingerprint),
                source_url=source_url,
                timestamp=timestamp,
                submitter=submitter,
            )
        except Exception as exc:
            if "Record not found" in str(exc):
                raise RecordNotFoundError(record_id)
            raise BlockchainError(f"Failed to retrieve record: {exc}") from exc

    async def verify_fingerprint(self, record_id: str, fingerprint_hex: str) -> bool:
        try:
            rid_bytes = bytes.fromhex(_hex(record_id))
            fp_bytes = bytes.fromhex(_hex(fingerprint_hex))
            result = await asyncio.to_thread(
                self._contract.functions.verifyFingerprint(rid_bytes, fp_bytes).call
            )
            return result
        except Exception as exc:
            raise BlockchainError(f"Verification call failed: {exc}") from exc
