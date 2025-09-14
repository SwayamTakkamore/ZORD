pragma circom 2.0.0;

include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/gates.circom";
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/mimcsponge.circom";
include "circomlib/circuits/bitify.circom";

/*
 * Compliance Verification Circuit
 * 
 * This circuit proves that a transaction satisfies compliance requirements
 * without revealing sensitive information like exact amounts or wallet addresses.
 * 
 * Public inputs:
 * - merkle_root: The Merkle root of compliance evidence
 * - compliance_hash: Hash of the compliance decision
 * 
 * Private inputs:
 * - transaction_amount: The transaction amount (private)
 * - source_wallet_hash: Hash of source wallet address
 * - dest_wallet_hash: Hash of destination wallet address
 * - kyc_status: KYC verification status (0/1)
 * - threshold_amount: Maximum allowed amount without additional checks
 * - blacklist_proof: Proof that wallets are not blacklisted
 * - merkle_path: Merkle path for evidence inclusion
 * - merkle_siblings: Sibling hashes for Merkle proof
 */

template ComplianceVerification(levels) {
    // Public inputs
    signal input merkle_root;
    signal input compliance_hash;
    
    // Private inputs - transaction details
    signal input transaction_amount;
    signal input source_wallet_hash;
    signal input dest_wallet_hash;
    signal input kyc_status;
    signal input threshold_amount;
    
    // Private inputs - compliance proofs
    signal input blacklist_proof;
    signal input merkle_path[levels];
    signal input merkle_siblings[levels];
    
    // Outputs
    signal output valid;
    
    // Internal components
    component poseidon = Poseidon(4);
    component amount_check = LessEqThan(64);
    component kyc_check = IsEqual();
    component blacklist_check = IsEqual();
    component merkle_verifier = MerkleTreeVerifier(levels);
    
    // 1. Verify transaction amount is within threshold
    amount_check.in[0] <== transaction_amount;
    amount_check.in[1] <== threshold_amount;
    
    // 2. Verify KYC status is valid (1 = verified)
    kyc_check.in[0] <== kyc_status;
    kyc_check.in[1] <== 1;
    
    // 3. Verify blacklist proof is valid (1 = not blacklisted)
    blacklist_check.in[0] <== blacklist_proof;
    blacklist_check.in[1] <== 1;
    
    // 4. Generate compliance evidence hash
    poseidon.inputs[0] <== transaction_amount;
    poseidon.inputs[1] <== source_wallet_hash;
    poseidon.inputs[2] <== dest_wallet_hash;
    poseidon.inputs[3] <== kyc_status;
    
    // 5. Verify Merkle proof for evidence inclusion
    merkle_verifier.leaf <== poseidon.out;
    merkle_verifier.root <== merkle_root;
    for (var i = 0; i < levels; i++) {
        merkle_verifier.pathElements[i] <== merkle_siblings[i];
        merkle_verifier.pathIndices[i] <== merkle_path[i];
    }
    
    // 6. Final compliance check - all conditions must pass
    component and_gate1 = AND();
    component and_gate2 = AND();
    component and_gate3 = AND();
    
    and_gate1.a <== amount_check.out;
    and_gate1.b <== kyc_check.out;
    
    and_gate2.a <== and_gate1.out;
    and_gate2.b <== blacklist_check.out;
    
    and_gate3.a <== and_gate2.out;
    and_gate3.b <== merkle_verifier.out;
    
    // 7. Verify compliance hash matches expected value
    component compliance_hasher = Poseidon(2);
    compliance_hasher.inputs[0] <== poseidon.out;
    compliance_hasher.inputs[1] <== and_gate3.out;
    
    component final_check = IsEqual();
    final_check.in[0] <== compliance_hasher.out;
    final_check.in[1] <== compliance_hash;
    
    valid <== final_check.out;
}

/*
 * Merkle Tree Verifier Component
 * Verifies that a leaf is included in a Merkle tree with given root
 */
template MerkleTreeVerifier(levels) {
    signal input leaf;
    signal input root;
    signal input pathElements[levels];
    signal input pathIndices[levels];
    
    signal output out;
    
    component hashers[levels];
    component selectors[levels];
    
    for (var i = 0; i < levels; i++) {
        selectors[i] = DualMux();
        selectors[i].in[0] <== i == 0 ? leaf : hashers[i-1].out;
        selectors[i].in[1] <== pathElements[i];
        selectors[i].s <== pathIndices[i];
        
        hashers[i] = Poseidon(2);
        hashers[i].inputs[0] <== selectors[i].out[0];
        hashers[i].inputs[1] <== selectors[i].out[1];
    }
    
    component final_check = IsEqual();
    final_check.in[0] <== levels > 0 ? hashers[levels-1].out : leaf;
    final_check.in[1] <== root;
    
    out <== final_check.out;
}

/*
 * Dual Multiplexer - selects between two inputs based on selector
 */
template DualMux() {
    signal input in[2];
    signal input s;
    signal output out[2];
    
    component mux1 = Mux1();
    component mux2 = Mux1();
    
    mux1.c[0] <== in[0];
    mux1.c[1] <== in[1];
    mux1.s <== s;
    
    mux2.c[0] <== in[1];
    mux2.c[1] <== in[0];
    mux2.s <== s;
    
    out[0] <== mux1.out;
    out[1] <== mux2.out;
}

// Main component with 10 levels for Merkle tree (supports up to 1024 leaves)
component main = ComplianceVerification(10);
