// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title ComplianceAnchor
 * @dev Minimal gas-efficient contract for anchoring Merkle roots to blockchain
 * @notice Stores compliance evidence roots with timestamp and anchorer information
 */
contract ComplianceAnchor {
    // Events
    event RootAnchored(
        bytes32 indexed root,
        uint256 timestamp,
        address indexed by
    );

    // Owner for optional access control
    address public owner;
    
    // Modifier for owner-only functions (optional)
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    /**
     * @dev Constructor sets the contract deployer as owner
     */
    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Anchor a Merkle root to the blockchain
     * @param root The Merkle root hash to anchor
     * @notice Emits RootAnchored event with root, timestamp, and anchorer address
     */
    function anchorRoot(bytes32 root) external {
        require(root != bytes32(0), "Root cannot be zero");
        
        emit RootAnchored(root, block.timestamp, msg.sender);
    }

    /**
     * @dev Owner-only version of anchorRoot for restricted access
     * @param root The Merkle root hash to anchor
     */
    function anchorRootOwnerOnly(bytes32 root) external onlyOwner {
        require(root != bytes32(0), "Root cannot be zero");
        
        emit RootAnchored(root, block.timestamp, msg.sender);
    }

    /**
     * @dev Transfer ownership to a new address
     * @param newOwner The address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        owner = newOwner;
    }

    /**
     * @dev Get contract version for debugging
     * @return version string
     */
    function version() external pure returns (string memory) {
        return "1.0.0";
    }
}
