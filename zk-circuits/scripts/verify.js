const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

/**
 * Proof Verification Script
 * 
 * This script verifies ZK proofs for compliance verification
 */

class ProofVerifier {
    constructor() {
        this.circuitName = "compliance";
        this.vkeyPath = path.join(__dirname, "../keys", `${this.circuitName}_vkey.json`);
        this.proofsPath = path.join(__dirname, "../proofs");
        
        // Load verification key
        if (fs.existsSync(this.vkeyPath)) {
            this.verificationKey = JSON.parse(fs.readFileSync(this.vkeyPath, "utf8"));
        } else {
            console.warn("⚠️ Verification key not found. Run setup first.");
        }
    }
    
    /**
     * Verify a ZK proof
     * @param {Object} proof - The proof object
     * @param {Array} publicSignals - Public signals
     * @returns {boolean} - Verification result
     */
    async verifyProof(proof, publicSignals) {
        try {
            console.log("🔍 Verifying ZK proof...");
            
            if (!this.verificationKey) {
                throw new Error("Verification key not loaded");
            }
            
            const result = await snarkjs.groth16.verify(
                this.verificationKey,
                publicSignals,
                proof
            );
            
            if (result) {
                console.log("✅ Proof verification successful!");
            } else {
                console.log("❌ Proof verification failed!");
            }
            
            return result;
            
        } catch (error) {
            console.error("❌ Verification error:", error);
            return false;
        }
    }
    
    /**
     * Verify a proof from file
     * @param {string} proofId - Proof identifier
     * @returns {boolean} - Verification result
     */
    async verifyProofById(proofId) {
        try {
            const proofPath = path.join(this.proofsPath, `proof_${proofId}.json`);
            
            if (!fs.existsSync(proofPath)) {
                throw new Error(`Proof not found: ${proofId}`);
            }
            
            const proofData = JSON.parse(fs.readFileSync(proofPath, "utf8"));
            
            console.log(`📄 Verifying proof: ${proofId}`);
            console.log(`🕐 Generated: ${proofData.timestamp}`);
            console.log(`🔧 Circuit: ${proofData.circuit} v${proofData.version}`);
            
            return await this.verifyProof(proofData.proof, proofData.publicSignals);
            
        } catch (error) {
            console.error("❌ Proof verification failed:", error);
            return false;
        }
    }
    
    /**
     * Verify compliance proof with additional checks
     * @param {Object} proofData - Complete proof data
     * @param {Object} expectedPublicInputs - Expected public inputs
     * @returns {Object} - Detailed verification result
     */
    async verifyComplianceProof(proofData, expectedPublicInputs = {}) {
        try {
            console.log("🛡️ Verifying compliance proof...");
            
            const result = {
                valid: false,
                checks: {
                    proof_valid: false,
                    public_inputs_valid: false,
                    merkle_root_valid: false,
                    compliance_hash_valid: false,
                    circuit_version_valid: false
                },
                details: {}
            };
            
            // 1. Verify the cryptographic proof
            result.checks.proof_valid = await this.verifyProof(
                proofData.proof, 
                proofData.publicSignals
            );
            
            if (!result.checks.proof_valid) {
                result.details.error = "Cryptographic proof verification failed";
                return result;
            }
            
            // 2. Verify public inputs structure
            if (proofData.publicSignals.length >= 2) {
                result.checks.public_inputs_valid = true;
                
                const [merkle_root, compliance_hash] = proofData.publicSignals;
                result.details.merkle_root = merkle_root;
                result.details.compliance_hash = compliance_hash;
            }
            
            // 3. Verify expected Merkle root (if provided)
            if (expectedPublicInputs.merkle_root) {
                result.checks.merkle_root_valid = 
                    proofData.publicSignals[0] === expectedPublicInputs.merkle_root;
            } else {
                result.checks.merkle_root_valid = true; // Skip if not provided
            }
            
            // 4. Verify expected compliance hash (if provided)
            if (expectedPublicInputs.compliance_hash) {
                result.checks.compliance_hash_valid = 
                    proofData.publicSignals[1] === expectedPublicInputs.compliance_hash;
            } else {
                result.checks.compliance_hash_valid = true; // Skip if not provided
            }
            
            // 5. Verify circuit version
            result.checks.circuit_version_valid = 
                proofData.circuit === this.circuitName && 
                proofData.version === "1.0.0";
            
            // Final validation
            result.valid = Object.values(result.checks).every(check => check === true);
            
            if (result.valid) {
                console.log("✅ Compliance proof is valid!");
            } else {
                console.log("❌ Compliance proof validation failed!");
                console.log("Failed checks:", 
                    Object.entries(result.checks)
                        .filter(([_, valid]) => !valid)
                        .map(([check]) => check)
                );
            }
            
            return result;
            
        } catch (error) {
            console.error("❌ Compliance verification failed:", error);
            return {
                valid: false,
                error: error.message
            };
        }
    }
    
    /**
     * Batch verify multiple proofs
     * @param {Array} proofIds - Array of proof identifiers
     * @returns {Array} - Verification results
     */
    async batchVerify(proofIds) {
        console.log(`🔍 Batch verifying ${proofIds.length} proofs...`);
        
        const results = [];
        
        for (const proofId of proofIds) {
            console.log(`\n📄 Verifying ${proofId}...`);
            const result = await this.verifyProofById(proofId);
            results.push({
                proofId,
                valid: result
            });
        }
        
        const validCount = results.filter(r => r.valid).length;
        console.log(`\n📊 Batch verification complete: ${validCount}/${proofIds.length} valid`);
        
        return results;
    }
    
    /**
     * Get verification key info
     */
    getVerificationKeyInfo() {
        if (!this.verificationKey) {
            return null;
        }
        
        return {
            protocol: this.verificationKey.protocol,
            curve: this.verificationKey.curve,
            nPublic: this.verificationKey.nPublic,
            vk_alpha_1: this.verificationKey.vk_alpha_1,
            vk_beta_2: this.verificationKey.vk_beta_2,
            vk_gamma_2: this.verificationKey.vk_gamma_2,
            vk_delta_2: this.verificationKey.vk_delta_2,
            IC_length: this.verificationKey.IC ? this.verificationKey.IC.length : 0
        };
    }
    
    /**
     * Export verification key for on-chain verification
     */
    exportVerificationKeyForContract() {
        if (!this.verificationKey) {
            throw new Error("Verification key not loaded");
        }
        
        // Format for Solidity contract
        return {
            alpha: this.verificationKey.vk_alpha_1,
            beta: this.verificationKey.vk_beta_2,
            gamma: this.verificationKey.vk_gamma_2,
            delta: this.verificationKey.vk_delta_2,
            ic: this.verificationKey.IC
        };
    }
}

// CLI interface
async function main() {
    const verifier = new ProofVerifier();
    
    if (process.argv[2] === "info") {
        const info = verifier.getVerificationKeyInfo();
        if (info) {
            console.log("🔑 Verification Key Info:");
            console.log(`  Protocol: ${info.protocol}`);
            console.log(`  Curve: ${info.curve}`);
            console.log(`  Public inputs: ${info.nPublic}`);
            console.log(`  IC length: ${info.IC_length}`);
        } else {
            console.log("❌ Verification key not found");
        }
        return;
    }
    
    if (process.argv[2] === "all") {
        // Verify all proofs
        const proofFiles = fs.readdirSync(verifier.proofsPath)
            .filter(f => f.startsWith("proof_") && f.endsWith(".json"));
        
        if (proofFiles.length === 0) {
            console.log("📭 No proofs found");
            return;
        }
        
        const proofIds = proofFiles.map(f => 
            f.replace("proof_", "").replace(".json", "")
        );
        
        await verifier.batchVerify(proofIds);
        return;
    }
    
    if (process.argv[2]) {
        // Verify specific proof
        const proofId = process.argv[2];
        await verifier.verifyProofById(proofId);
        return;
    }
    
    console.log("Usage:");
    console.log("  node verify.js <proof_id>          - Verify specific proof");
    console.log("  node verify.js all                 - Verify all proofs");
    console.log("  node verify.js info                - Show verification key info");
}

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { ProofVerifier };
