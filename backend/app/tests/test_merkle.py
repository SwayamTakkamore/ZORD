"""Test cases for Merkle tree implementation"""

import pytest
from app.core.merkle import (
    MerkleTree, 
    MerkleNode, 
    MerkleProof,
    create_evidence_tree,
    verify_evidence_inclusion
)


class TestMerkleNode:
    """Test MerkleNode class"""
    
    def test_leaf_node_creation(self):
        """Test creating a leaf node"""
        node = MerkleNode(hash="abc123", data="test_data")
        
        assert node.hash == "abc123"
        assert node.data == "test_data"
        assert node.is_leaf() == True
        assert node.left is None
        assert node.right is None
    
    def test_internal_node_creation(self):
        """Test creating an internal node"""
        left = MerkleNode(hash="left123", data="left_data")
        right = MerkleNode(hash="right123", data="right_data")
        parent = MerkleNode(hash="parent123", left=left, right=right)
        
        assert parent.hash == "parent123"
        assert parent.data is None
        assert parent.is_leaf() == False
        assert parent.left == left
        assert parent.right == right
    
    def test_node_serialization(self):
        """Test node serialization to dictionary"""
        node = MerkleNode(hash="abc123", data="test_data")
        serialized = node.to_dict()
        
        assert serialized["hash"] == "abc123"
        assert serialized["data"] == "test_data"
        assert serialized["is_leaf"] == True


class TestMerkleProof:
    """Test MerkleProof class"""
    
    def test_proof_creation(self):
        """Test creating a Merkle proof"""
        proof = MerkleProof(
            leaf_hash="leaf123",
            leaf_index=0,
            proof_hashes=["sibling123"],
            proof_directions=["right"],
            root_hash="root123"
        )
        
        assert proof.leaf_hash == "leaf123"
        assert proof.leaf_index == 0
        assert proof.proof_hashes == ["sibling123"]
        assert proof.proof_directions == ["right"]
        assert proof.root_hash == "root123"
    
    def test_proof_serialization(self):
        """Test proof serialization to dictionary"""
        proof = MerkleProof(
            leaf_hash="leaf123",
            leaf_index=0,
            proof_hashes=["sibling123"],
            proof_directions=["right"],
            root_hash="root123"
        )
        
        serialized = proof.to_dict()
        
        assert serialized["leaf_hash"] == "leaf123"
        assert serialized["leaf_index"] == 0
        assert serialized["proof_hashes"] == ["sibling123"]
        assert serialized["proof_directions"] == ["right"]
        assert serialized["root_hash"] == "root123"
    
    def test_proof_verification_valid(self):
        """Test valid proof verification"""
        # Create a simple 2-leaf tree manually
        # Left leaf: hash("data1") = sha256("data1")
        # Right leaf: hash("data2") = sha256("data2")  
        # Root: hash(left_hash + right_hash)
        
        import hashlib
        
        leaf1_hash = hashlib.sha256("data1".encode()).hexdigest()
        leaf2_hash = hashlib.sha256("data2".encode()).hexdigest()
        root_hash = hashlib.sha256((leaf1_hash + leaf2_hash).encode()).hexdigest()
        
        # Proof for leaf1 (sibling is leaf2)
        proof = MerkleProof(
            leaf_hash=leaf1_hash,
            leaf_index=0,
            proof_hashes=[leaf2_hash],
            proof_directions=["right"],
            root_hash=root_hash
        )
        
        assert proof.verify() == True
    
    def test_proof_verification_invalid(self):
        """Test invalid proof verification"""
        proof = MerkleProof(
            leaf_hash="wrong_leaf",
            leaf_index=0,
            proof_hashes=["sibling123"],
            proof_directions=["right"],
            root_hash="wrong_root"
        )
        
        assert proof.verify() == False


class TestMerkleTree:
    """Test MerkleTree class"""
    
    def test_empty_tree(self):
        """Test empty Merkle tree"""
        tree = MerkleTree()
        
        assert len(tree.leaves) == 0
        assert len(tree.leaf_hashes) == 0
        
        root = tree.get_root()
        assert len(root) == 64  # SHA256 hex string
        
        tree_info = tree.get_tree_info()
        assert tree_info["total_leaves"] == 0
        assert tree_info["tree_height"] == 0
    
    def test_single_leaf_tree(self):
        """Test Merkle tree with single leaf"""
        tree = MerkleTree()
        
        leaf_hash = tree.add_leaf("single_data")
        assert len(leaf_hash) == 64
        
        root = tree.get_root()
        assert root == leaf_hash  # Root should equal the only leaf
        
        tree_info = tree.get_tree_info()
        assert tree_info["total_leaves"] == 1
        assert tree_info["tree_height"] == 1
    
    def test_two_leaf_tree(self):
        """Test Merkle tree with two leaves"""
        tree = MerkleTree()
        
        leaf1_hash = tree.add_leaf("data1")
        leaf2_hash = tree.add_leaf("data2")
        
        root = tree.get_root()
        assert root != leaf1_hash
        assert root != leaf2_hash
        assert len(root) == 64
        
        tree_info = tree.get_tree_info()
        assert tree_info["total_leaves"] == 2
        assert tree_info["tree_height"] == 2
    
    def test_multiple_leaf_tree(self):
        """Test Merkle tree with multiple leaves"""
        tree = MerkleTree()
        
        data_items = [f"data_{i}" for i in range(7)]  # Odd number to test padding
        leaf_hashes = []
        
        for data in data_items:
            leaf_hash = tree.add_leaf(data)
            leaf_hashes.append(leaf_hash)
        
        root = tree.get_root()
        assert len(root) == 64
        
        tree_info = tree.get_tree_info()
        assert tree_info["total_leaves"] == 7
        assert tree_info["tree_height"] > 2  # Should have multiple levels
    
    def test_deterministic_hash(self):
        """Test that tree produces deterministic hashes"""
        tree1 = MerkleTree()
        tree2 = MerkleTree()
        
        data_items = ["data1", "data2", "data3"]
        
        for data in data_items:
            tree1.add_leaf(data)
            tree2.add_leaf(data)
        
        root1 = tree1.get_root()
        root2 = tree2.get_root()
        
        assert root1 == root2
    
    def test_proof_generation_single_leaf(self):
        """Test proof generation for single leaf tree"""
        tree = MerkleTree()
        tree.add_leaf("single_data")
        
        proof = tree.get_proof("single_data")
        
        assert proof is not None
        assert proof.leaf_index == 0
        assert proof.proof_hashes == []  # No siblings in single leaf tree
        assert proof.proof_directions == []
        assert proof.root_hash == tree.get_root()
    
    def test_proof_generation_two_leaves(self):
        """Test proof generation for two leaf tree"""
        tree = MerkleTree()
        tree.add_leaf("data1")
        tree.add_leaf("data2")
        
        # Test proof for first leaf
        proof1 = tree.get_proof("data1")
        assert proof1 is not None
        assert proof1.leaf_index == 0
        assert len(proof1.proof_hashes) == 1  # One sibling
        assert proof1.proof_directions == ["right"]  # Sibling is on the right
        
        # Test proof for second leaf
        proof2 = tree.get_proof("data2")
        assert proof2 is not None
        assert proof2.leaf_index == 1
        assert len(proof2.proof_hashes) == 1
        assert proof2.proof_directions == ["left"]  # Sibling is on the left
    
    def test_proof_generation_multiple_leaves(self):
        """Test proof generation for multiple leaf tree"""
        tree = MerkleTree()
        
        data_items = [f"evidence_{i}" for i in range(5)]
        for data in data_items:
            tree.add_leaf(data)
        
        # Test proof for each leaf
        for i, data in enumerate(data_items):
            proof = tree.get_proof(data)
            assert proof is not None
            assert proof.leaf_index == i
            assert len(proof.proof_hashes) > 0  # Should have at least one proof hash
            assert len(proof.proof_directions) == len(proof.proof_hashes)
    
    def test_proof_verification(self):
        """Test proof verification"""
        tree = MerkleTree()
        
        data_items = ["evidence_1", "evidence_2", "evidence_3", "evidence_4"]
        for data in data_items:
            tree.add_leaf(data)
        
        # Generate and verify proof for each leaf
        for data in data_items:
            proof = tree.get_proof(data)
            assert proof is not None
            
            # Verify using tree method
            is_valid = tree.verify_proof(proof)
            assert is_valid == True
            
            # Verify using proof method
            proof_valid = proof.verify()
            assert proof_valid == True
    
    def test_proof_not_found(self):
        """Test proof generation for non-existent leaf"""
        tree = MerkleTree()
        tree.add_leaf("data1")
        tree.add_leaf("data2")
        
        proof = tree.get_proof("non_existent_data")
        assert proof is None
    
    def test_proof_by_index(self):
        """Test proof generation by index"""
        tree = MerkleTree()
        
        data_items = ["data1", "data2", "data3"]
        for data in data_items:
            tree.add_leaf(data)
        
        # Test valid indices
        for i in range(len(data_items)):
            proof = tree.get_proof_by_index(i)
            assert proof is not None
            assert proof.leaf_index == i
        
        # Test invalid indices
        invalid_proof = tree.get_proof_by_index(-1)
        assert invalid_proof is None
        
        invalid_proof = tree.get_proof_by_index(10)
        assert invalid_proof is None
    
    def test_tree_serialization(self):
        """Test tree serialization and deserialization"""
        tree = MerkleTree()
        
        data_items = ["data1", "data2", "data3"]
        for data in data_items:
            tree.add_leaf(data)
        
        # Serialize
        serialized = tree.serialize()
        
        assert "leaves" in serialized
        assert "leaf_hashes" in serialized
        assert "root_hash" in serialized
        assert "tree_info" in serialized
        
        # Deserialize
        new_tree = MerkleTree.deserialize(serialized)
        
        assert new_tree.leaves == tree.leaves
        assert new_tree.leaf_hashes == tree.leaf_hashes
        assert new_tree.get_root() == tree.get_root()
    
    def test_export_proofs(self):
        """Test exporting all proofs"""
        tree = MerkleTree()
        
        data_items = ["evidence_1", "evidence_2", "evidence_3"]
        for data in data_items:
            tree.add_leaf(data)
        
        proofs = tree.export_proofs()
        
        assert len(proofs) == 3
        for i, proof_data in enumerate(proofs):
            assert "leaf_data" in proof_data
            assert "proof" in proof_data
            assert proof_data["leaf_data"] == data_items[i]


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_create_evidence_tree(self):
        """Test creating evidence tree from hash list"""
        evidence_hashes = [
            "hash1_abc123",
            "hash2_def456", 
            "hash3_ghi789"
        ]
        
        tree = create_evidence_tree(evidence_hashes)
        
        assert tree.get_tree_info()["total_leaves"] == 3
        assert len(tree.get_root()) == 64
        
        # Verify all hashes are in the tree
        for evidence_hash in evidence_hashes:
            proof = tree.get_proof(evidence_hash)
            assert proof is not None
    
    def test_verify_evidence_inclusion(self):
        """Test verifying evidence inclusion"""
        # Create tree
        evidence_hashes = ["hash1", "hash2", "hash3"]
        tree = create_evidence_tree(evidence_hashes)
        
        # Get proof for first evidence
        evidence_hash = "hash1"
        proof = tree.get_proof(evidence_hash)
        assert proof is not None
        
        # Verify inclusion
        is_included = verify_evidence_inclusion(
            evidence_hash=evidence_hash,
            proof=proof.to_dict(),
            expected_root=tree.get_root()
        )
        
        assert is_included == True
    
    def test_verify_evidence_inclusion_invalid(self):
        """Test verifying evidence inclusion with invalid proof"""
        evidence_hashes = ["hash1", "hash2", "hash3"]
        tree = create_evidence_tree(evidence_hashes)
        
        # Create invalid proof
        invalid_proof = {
            "leaf_hash": "wrong_hash",
            "leaf_index": 0,
            "proof_hashes": ["wrong_sibling"],
            "proof_directions": ["right"],
            "root_hash": "wrong_root"
        }
        
        is_included = verify_evidence_inclusion(
            evidence_hash="wrong_hash",
            proof=invalid_proof,
            expected_root=tree.get_root()
        )
        
        assert is_included == False
    
    def test_verify_evidence_inclusion_malformed_proof(self):
        """Test verifying evidence inclusion with malformed proof"""
        is_included = verify_evidence_inclusion(
            evidence_hash="some_hash",
            proof={"invalid": "proof"},
            expected_root="some_root"
        )
        
        assert is_included == False
