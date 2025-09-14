"""
Merkle tree implementation for compliance evidence aggregation
"""

import hashlib
import json
import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from math import ceil, log2

logger = logging.getLogger(__name__)


@dataclass
class MerkleNode:
    """Represents a node in the Merkle tree"""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[str] = None  # Only for leaf nodes
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node"""
        return self.left is None and self.right is None
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary for serialization"""
        return {
            "hash": self.hash,
            "data": self.data,
            "is_leaf": self.is_leaf()
        }


@dataclass
class MerkleProof:
    """Merkle proof for a specific leaf"""
    leaf_hash: str
    leaf_index: int
    proof_hashes: List[str]
    proof_directions: List[str]  # 'left' or 'right'
    root_hash: str
    
    def to_dict(self) -> Dict:
        """Convert proof to dictionary for serialization"""
        return {
            "leaf_hash": self.leaf_hash,
            "leaf_index": self.leaf_index,
            "proof_hashes": self.proof_hashes,
            "proof_directions": self.proof_directions,
            "root_hash": self.root_hash
        }
    
    def verify(self) -> bool:
        """Verify this Merkle proof"""
        current_hash = self.leaf_hash
        
        for i, proof_hash in enumerate(self.proof_hashes):
            direction = self.proof_directions[i]
            
            if direction == 'left':
                # Proof hash is on the left, current hash on the right
                combined = proof_hash + current_hash
            else:
                # Current hash on the left, proof hash on the right
                combined = current_hash + proof_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == self.root_hash


class MerkleTree:
    """
    Merkle tree for aggregating transaction evidence hashes
    
    Features:
    - Deterministic leaf ordering
    - Efficient proof generation
    - Incremental updates
    - Serialization support
    """
    
    def __init__(self):
        self.leaves: List[str] = []  # Store leaf data/hashes
        self.leaf_hashes: List[str] = []  # Computed leaf hashes
        self.root: Optional[MerkleNode] = None
        self._tree_cache: Dict[int, List[MerkleNode]] = {}  # Cache tree levels
        
        logger.info("Merkle tree initialized")
    
    def add_leaf(self, data: str) -> str:
        """
        Add a leaf to the tree
        
        Args:
            data: Data to add as a leaf (e.g., evidence hash)
            
        Returns:
            The computed leaf hash
        """
        # Compute deterministic hash of the data
        leaf_hash = self._hash_data(data)
        
        self.leaves.append(data)
        self.leaf_hashes.append(leaf_hash)
        
        # Invalidate cache since tree structure changed
        self._tree_cache.clear()
        self.root = None
        
        logger.debug(f"Added leaf: {data[:20]}... -> {leaf_hash[:16]}...")
        return leaf_hash
    
    def build_tree(self) -> str:
        """
        Build the complete Merkle tree
        
        Returns:
            Root hash of the tree
        """
        if not self.leaf_hashes:
            # Empty tree
            empty_hash = self._hash_data("")
            self.root = MerkleNode(hash=empty_hash)
            return empty_hash
        
        if len(self.leaf_hashes) == 1:
            # Single leaf tree
            self.root = MerkleNode(hash=self.leaf_hashes[0], data=self.leaves[0])
            return self.root.hash
        
        # Build tree bottom-up
        current_level = [
            MerkleNode(hash=leaf_hash, data=data) 
            for leaf_hash, data in zip(self.leaf_hashes, self.leaves)
        ]
        
        level_index = 0
        self._tree_cache[level_index] = current_level.copy()
        
        while len(current_level) > 1:
            next_level = []
            level_index += 1
            
            # Process pairs of nodes
            for i in range(0, len(current_level), 2):
                left_node = current_level[i]
                
                if i + 1 < len(current_level):
                    # Pair exists
                    right_node = current_level[i + 1]
                else:
                    # Odd number of nodes, duplicate the last one
                    right_node = current_level[i]
                
                # Create parent node
                combined_hash = left_node.hash + right_node.hash
                parent_hash = self._hash_data(combined_hash)
                parent_node = MerkleNode(
                    hash=parent_hash,
                    left=left_node,
                    right=right_node
                )
                
                next_level.append(parent_node)
            
            self._tree_cache[level_index] = next_level.copy()
            current_level = next_level
        
        self.root = current_level[0]
        logger.info(f"Built Merkle tree with {len(self.leaf_hashes)} leaves, root: {self.root.hash[:16]}...")
        return self.root.hash
    
    def get_root(self) -> str:
        """Get the root hash, building tree if necessary"""
        if self.root is None:
            return self.build_tree()
        return self.root.hash
    
    def get_proof(self, leaf_data: str) -> Optional[MerkleProof]:
        """
        Generate Merkle proof for a specific leaf
        
        Args:
            leaf_data: The original leaf data
            
        Returns:
            MerkleProof object or None if leaf not found
        """
        try:
            leaf_index = self.leaves.index(leaf_data)
        except ValueError:
            logger.warning(f"Leaf data not found in tree: {leaf_data[:20]}...")
            return None
        
        return self.get_proof_by_index(leaf_index)
    
    def get_proof_by_index(self, leaf_index: int) -> Optional[MerkleProof]:
        """
        Generate Merkle proof for a leaf by index
        
        Args:
            leaf_index: Index of the leaf in the tree
            
        Returns:
            MerkleProof object or None if index invalid
        """
        if leaf_index < 0 or leaf_index >= len(self.leaf_hashes):
            logger.warning(f"Invalid leaf index: {leaf_index}")
            return None
        
        # Ensure tree is built
        root_hash = self.get_root()
        
        if len(self.leaf_hashes) == 1:
            # Special case: single leaf tree
            return MerkleProof(
                leaf_hash=self.leaf_hashes[0],
                leaf_index=0,
                proof_hashes=[],
                proof_directions=[],
                root_hash=root_hash
            )
        
        proof_hashes = []
        proof_directions = []
        current_index = leaf_index
        
        # Traverse up the tree collecting sibling hashes
        for level in range(len(self._tree_cache) - 1):
            level_nodes = self._tree_cache[level]
            
            # Find sibling
            if current_index % 2 == 0:
                # Current node is left child, sibling is right
                sibling_index = current_index + 1
                direction = 'right'
            else:
                # Current node is right child, sibling is left
                sibling_index = current_index - 1
                direction = 'left'
            
            # Add sibling hash to proof
            if sibling_index < len(level_nodes):
                sibling_hash = level_nodes[sibling_index].hash
            else:
                # No sibling (odd number of nodes), use current node's hash
                sibling_hash = level_nodes[current_index].hash
            
            proof_hashes.append(sibling_hash)
            proof_directions.append(direction)
            
            # Move to parent level
            current_index = current_index // 2
        
        return MerkleProof(
            leaf_hash=self.leaf_hashes[leaf_index],
            leaf_index=leaf_index,
            proof_hashes=proof_hashes,
            proof_directions=proof_directions,
            root_hash=root_hash
        )
    
    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verify a Merkle proof against this tree
        
        Args:
            proof: MerkleProof to verify
            
        Returns:
            True if proof is valid, False otherwise
        """
        expected_root = self.get_root()
        return proof.root_hash == expected_root and proof.verify()
    
    def _hash_data(self, data: str) -> str:
        """Compute SHA256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_tree_info(self) -> Dict:
        """Get information about the tree structure"""
        tree_height = len(self._tree_cache) if self._tree_cache else (1 if self.leaf_hashes else 0)
        return {
            "total_leaves": len(self.leaf_hashes),
            "tree_height": tree_height,
            "root_hash": self.get_root(),
            "is_built": self.root is not None
        }
    
    def serialize(self) -> Dict:
        """Serialize tree to dictionary"""
        return {
            "leaves": self.leaves,
            "leaf_hashes": self.leaf_hashes,
            "root_hash": self.get_root(),
            "tree_info": self.get_tree_info()
        }
    
    @classmethod
    def deserialize(cls, data: Dict) -> 'MerkleTree':
        """Create tree from serialized data"""
        tree = cls()
        tree.leaves = data["leaves"]
        tree.leaf_hashes = data["leaf_hashes"]
        
        # Rebuild tree structure
        if tree.leaf_hashes:
            tree.build_tree()
        
        return tree
    
    def export_proofs(self) -> List[Dict]:
        """Export proofs for all leaves"""
        proofs = []
        for i in range(len(self.leaves)):
            proof = self.get_proof_by_index(i)
            if proof:
                proofs.append({
                    "leaf_data": self.leaves[i],
                    "proof": proof.to_dict()
                })
        return proofs

    def verify_evidence_inclusion(self, evidence: "ComplianceEvidence") -> bool:
        """Verify that specific evidence is included in the tree"""
        evidence_hash = evidence.get_hash()
        
        if evidence_hash not in self.leaf_hashes:
            return False
            
        # Get leaf index
        leaf_index = self.leaf_hashes.index(evidence_hash)
        
        # Generate proof
        proof = self.generate_proof(leaf_index)
        
        # Verify proof - the proof should already have the correct root hash
        return proof.verify()


# Convenience functions for transaction evidence aggregation

def create_evidence_tree(evidence_hashes: List[str]) -> MerkleTree:
    """
    Create a Merkle tree from a list of evidence hashes
    
    Args:
        evidence_hashes: List of evidence hashes to include
        
    Returns:
        Built MerkleTree instance
    """
    tree = MerkleTree()
    
    for evidence_hash in evidence_hashes:
        tree.add_leaf(evidence_hash)
    
    tree.build_tree()
    return tree


def verify_evidence_inclusion(
    evidence_hash: str, 
    proof: Dict, 
    expected_root: str
) -> bool:
    """
    Verify that an evidence hash is included in a Merkle root
    
    Args:
        evidence_hash: Hash to verify (original input data, will be hashed)
        proof: Merkle proof dictionary
        expected_root: Expected root hash
        
    Returns:
        True if evidence is included, False otherwise
    """
    try:
        # Hash the evidence to get the actual leaf hash
        import hashlib
        actual_leaf_hash = hashlib.sha256(evidence_hash.encode()).hexdigest()
        
        merkle_proof = MerkleProof(
            leaf_hash=proof["leaf_hash"],
            leaf_index=proof["leaf_index"],
            proof_hashes=proof["proof_hashes"],
            proof_directions=proof["proof_directions"],
            root_hash=proof["root_hash"]
        )
        
        return (
            merkle_proof.leaf_hash == actual_leaf_hash and 
            merkle_proof.root_hash == expected_root and
            merkle_proof.verify()
        )
    except Exception as e:
        logger.error(f"Error verifying evidence inclusion: {e}")
        return False
