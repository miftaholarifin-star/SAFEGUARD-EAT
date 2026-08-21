// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/// @title SAFEGUARD EAT Quality Gate Reference Contract
/// @notice Reference only. An independent security audit and approved oracle
///         design are required before any deployment with real funds.
contract SafeguardEatQualityGate {
    enum Status { NONE, FUNDED, PASSED, FAILED, RELEASED, REFUNDED }

    struct BatchEscrow {
        address payable supplier;
        uint256 amount;
        Status status;
        bytes32 evidenceHash;
        uint256 updatedAt;
    }

    address public immutable administrator;
    bool private entered;
    mapping(bytes32 => BatchEscrow) public batches;

    event BatchFunded(bytes32 indexed batchId, address indexed supplier, uint256 amount);
    event QualityEvaluated(bytes32 indexed batchId, Status status, bytes32 evidenceHash);
    event PaymentReleased(bytes32 indexed batchId, address indexed supplier, uint256 amount);
    event PaymentRefunded(bytes32 indexed batchId, address indexed administrator, uint256 amount);

    modifier onlyAdministrator() {
        require(msg.sender == administrator, "administrator only");
        _;
    }

    modifier nonReentrant() {
        require(!entered, "reentrant call");
        entered = true;
        _;
        entered = false;
    }

    constructor() {
        administrator = msg.sender;
    }

    function batchId(string calldata batchCode) public pure returns (bytes32) {
        return keccak256(bytes(batchCode));
    }

    function fundBatch(string calldata batchCode, address payable supplier)
        external
        payable
        onlyAdministrator
    {
        require(bytes(batchCode).length > 0, "empty batch code");
        require(supplier != address(0), "invalid supplier");
        require(msg.value > 0, "funding required");
        bytes32 id = batchId(batchCode);
        require(batches[id].status == Status.NONE, "batch already registered");
        batches[id] = BatchEscrow(supplier, msg.value, Status.FUNDED, bytes32(0), block.timestamp);
        emit BatchFunded(id, supplier, msg.value);
    }

    function evaluateQuality(
        string calldata batchCode,
        bool temperatureOk,
        bool nutritionOk,
        bool deliveryOk,
        bool documentsOk,
        bytes32 evidenceHash
    ) external onlyAdministrator {
        bytes32 id = batchId(batchCode);
        BatchEscrow storage batch = batches[id];
        require(batch.status == Status.FUNDED, "batch is not funded");
        require(evidenceHash != bytes32(0), "evidence hash required");
        bool passed = temperatureOk && nutritionOk && deliveryOk && documentsOk;
        batch.status = passed ? Status.PASSED : Status.FAILED;
        batch.evidenceHash = evidenceHash;
        batch.updatedAt = block.timestamp;
        emit QualityEvaluated(id, batch.status, evidenceHash);
    }

    function releasePayment(string calldata batchCode)
        external
        onlyAdministrator
        nonReentrant
    {
        bytes32 id = batchId(batchCode);
        BatchEscrow storage batch = batches[id];
        require(batch.status == Status.PASSED, "quality gate not passed");
        uint256 amount = batch.amount;
        address payable supplier = batch.supplier;
        batch.amount = 0;
        batch.status = Status.RELEASED;
        batch.updatedAt = block.timestamp;
        (bool sent, ) = supplier.call{value: amount}("");
        require(sent, "payment failed");
        emit PaymentReleased(id, supplier, amount);
    }

    function refundFailedBatch(string calldata batchCode)
        external
        onlyAdministrator
        nonReentrant
    {
        bytes32 id = batchId(batchCode);
        BatchEscrow storage batch = batches[id];
        require(batch.status == Status.FAILED, "batch is not failed");
        uint256 amount = batch.amount;
        batch.amount = 0;
        batch.status = Status.REFUNDED;
        batch.updatedAt = block.timestamp;
        (bool sent, ) = payable(administrator).call{value: amount}("");
        require(sent, "refund failed");
        emit PaymentRefunded(id, administrator, amount);
    }
}
