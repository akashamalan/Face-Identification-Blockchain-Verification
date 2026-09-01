// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title VerificationRegistry
 * @notice Stores SHA-256 fingerprints of discovered web/social content
 *         for tamper-proof verification.
 * @dev    Only the fingerprint hash and minimal metadata are stored on-chain.
 *         No personal data, face embeddings, or raw images are recorded.
 */
contract VerificationRegistry {

    struct Record {
        bytes32  fingerprint;
        string   sourceUrl;
        uint256  timestamp;
        address  submitter;
    }

    /// @dev  recordId (keccak256 of fingerprint + submitter) => Record
    mapping(bytes32 => Record) private _records;

    /// @dev  Tracks all record IDs for enumeration (optional)
    bytes32[] private _recordIds;

    event RecordRegistered(
        bytes32 indexed recordId,
        bytes32 fingerprint,
        string  sourceUrl,
        address indexed submitter,
        uint256 timestamp
    );

    /**
     * @notice Register a new fingerprint record.
     * @param  _fingerprint  SHA-256 hash of the canonical post data (as bytes32).
     * @param  _sourceUrl    Public URL of the discovered content.
     * @return recordId      Unique identifier for the stored record.
     */
    function registerRecord(
        bytes32 _fingerprint,
        string calldata _sourceUrl
    ) external returns (bytes32 recordId) {
        recordId = keccak256(abi.encodePacked(_fingerprint, msg.sender, block.timestamp));

        _records[recordId] = Record({
            fingerprint: _fingerprint,
            sourceUrl:   _sourceUrl,
            timestamp:   block.timestamp,
            submitter:   msg.sender
        });

        _recordIds.push(recordId);

        emit RecordRegistered(recordId, _fingerprint, _sourceUrl, msg.sender, block.timestamp);
    }

    /**
     * @notice Retrieve a record by its ID.
     */
    function getRecord(bytes32 _recordId)
        external
        view
        returns (
            bytes32  fingerprint,
            string memory sourceUrl,
            uint256  timestamp,
            address  submitter
        )
    {
        Record storage r = _records[_recordId];
        require(r.timestamp != 0, "Record not found");
        return (r.fingerprint, r.sourceUrl, r.timestamp, r.submitter);
    }

    /**
     * @notice Verify whether a given fingerprint matches the stored record.
     * @return verified  True if fingerprints match.
     */
    function verifyFingerprint(bytes32 _recordId, bytes32 _fingerprint)
        external
        view
        returns (bool verified)
    {
        Record storage r = _records[_recordId];
        require(r.timestamp != 0, "Record not found");
        return r.fingerprint == _fingerprint;
    }

    /**
     * @notice Get total number of registered records.
     */
    function recordCount() external view returns (uint256) {
        return _recordIds.length;
    }
}
