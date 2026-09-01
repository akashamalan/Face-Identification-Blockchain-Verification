"""Deploy VerificationRegistry contract to Ethereum Sepolia testnet.

Usage:
    python scripts/deploy_contract.py

Requires environment variables:
    BLOCKCHAIN_RPC_URL   - Alchemy/Infura Sepolia endpoint
    BLOCKCHAIN_PRIVATE_KEY - Deployer wallet private key (must have Sepolia ETH)

The script prints the deployed contract address which you should set as
CONTRACT_ADDRESS in your .env file.

ALTERNATIVE: Deploy via Remix IDE (recommended for simplicity):
1. Open https://remix.ethereum.org
2. Create VerificationRegistry.sol and paste the contract code
3. Compile with Solidity 0.8.19+
4. Deploy to Sepolia via MetaMask (Injected Provider)
5. Copy the contract address to your .env
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from solcx import compile_standard, install_solc
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

RPC_URL = os.environ.get("BLOCKCHAIN_RPC_URL", "")
PRIVATE_KEY = os.environ.get("BLOCKCHAIN_PRIVATE_KEY", "")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "11155111"))

if not RPC_URL or not PRIVATE_KEY:
    print("ERROR: Set BLOCKCHAIN_RPC_URL and BLOCKCHAIN_PRIVATE_KEY in backend/.env")
    sys.exit(1)

# Read contract source
contract_path = Path(__file__).parent.parent / "contracts" / "VerificationRegistry.sol"
source = contract_path.read_text()

print("Installing Solidity compiler...")
install_solc("0.8.19")

print("Compiling contract...")
compiled = compile_standard(
    {
        "language": "Solidity",
        "sources": {"VerificationRegistry.sol": {"content": source}},
        "settings": {
            "outputSelection": {
                "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
            }
        },
    },
    solc_version="0.8.19",
)

contract_data = compiled["contracts"]["VerificationRegistry.sol"]["VerificationRegistry"]
abi = contract_data["abi"]
bytecode = contract_data["evm"]["bytecode"]["object"]

# Save ABI
abi_path = Path(__file__).parent.parent / "contracts" / "VerificationRegistry_abi.json"
abi_path.write_text(json.dumps(abi, indent=2))
print(f"ABI saved to {abi_path}")

# Deploy
print(f"Connecting to {RPC_URL[:40]}...")
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

account = w3.eth.account.from_key(PRIVATE_KEY)
print(f"Deployer address: {account.address}")

balance = w3.eth.get_balance(account.address)
print(f"Balance: {w3.from_wei(balance, 'ether')} ETH")

if balance == 0:
    print("ERROR: No Sepolia ETH. Get free testnet ETH from https://sepoliafaucet.com")
    sys.exit(1)

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(account.address)

tx = contract.constructor().build_transaction({
    "chainId": CHAIN_ID,
    "from": account.address,
    "nonce": nonce,
    "gas": 1_000_000,
    "gasPrice": w3.eth.gas_price,
})

signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Deployment tx: 0x{tx_hash.hex()}")
print("Waiting for confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
contract_address = receipt["contractAddress"]

print(f"\n{'='*60}")
print(f"CONTRACT DEPLOYED SUCCESSFULLY")
print(f"Address: {contract_address}")
print(f"Block:   {receipt['blockNumber']}")
print(f"TX:      https://sepolia.etherscan.io/tx/0x{tx_hash.hex()}")
print(f"{'='*60}")
print(f"\nAdd this to backend/.env:")
print(f"CONTRACT_ADDRESS={contract_address}")
