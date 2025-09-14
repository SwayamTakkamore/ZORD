const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

/**
 * Proof Generation Script
 * 
 * This script generates ZK proofs for compliance verification
 */

class ProofGenerator {
    constructor() {
        this.circuitName = "compliance";
        this.wasmPath = path.join(__dirname, "../build", `${this.circuitName}.wasm`);
        this.zkeyPath = path.join(__dirname, "../keys", `${this.circuitName}.zkey`);
        this.proofsPath = path.join(__dirname, "../proofs");
        
        if (!fs.existsSync(this.proofsPath)) {
            fs.mkdirSync(this.proofsPath, { recursive: true });
        }
    }
    
    /**
     * Generate a proof for compliance verification
     * @param {Object} input - The circuit input
     * @returns {Object} - The generated proof and public signals
     */
    async generateProof(input) {
        try {
            console.log("🔍 Generating ZK proof...");
            
            // Validate input
            this.validateInput(input);
            
            // Generate witness
            console.log("📊 Computing witness...");
            const { proof, publicSignals } = await snarkjs.groth16.fullProve(
                input,
                this.wasmPath,
                this.zkeyPath
            );
            
            // Create proof object with metadata
            const proofWithMetadata = {
                proof,
                publicSignals,
                timestamp: new Date().toISOString(),
                input_hash: this.hashInput(input),
                circuit: this.circuitName,
                version: "1.0.0"
            };
            
            // Save proof to file
            const proofId = crypto.randomBytes(16).toString("hex");
            const proofPath = path.join(this.proofsPath, `proof_${proofId}.json`);
            fs.writeFileSync(proofPath, JSON.stringify(proofWithMetadata, null, 2));
            
            console.log(`✅ Proof generated successfully!`);
            console.log(`📁 Proof saved to: ${proofPath}`);
            console.log(`🆔 Proof ID: ${proofId}`);
            
            return {
                ...proofWithMetadata,
                proofId,
                proofPath
            };
            
        } catch (error) {
            console.error("❌ Proof generation failed:", error);
            throw error;
        }
    }
    
    /**
     * Generate proof from transaction data and compliance evidence
     * @param {Object} transactionData - Transaction details
     * @param {Object} complianceEvidence - Compliance checking results
     * @param {Object} merkleProof - Merkle proof for evidence inclusion
     * @returns {Object} - The generated proof
     */
    async proveCompliance(transactionData, complianceEvidence, merkleProof) {
        try {
            console.log("🛡️ Proving transaction compliance...");
            
            // Convert transaction data to circuit input format
            const circuitInput = this.prepareCircuitInput(
                transactionData, 
                complianceEvidence, 
                merkleProof
            );
            
            return await this.generateProof(circuitInput);
            
        } catch (error) {
            console.error("❌ Compliance proving failed:", error);
            throw error;
        }
    }
    
    /**
     * Prepare circuit input from high-level data
     */
    prepareCircuitInput(transactionData, complianceEvidence, merkleProof) {
        // Hash wallet addresses for privacy
        const sourceHash = this.hashWallet(transactionData.wallet_from);
        const destHash = this.hashWallet(transactionData.wallet_to);
        
        // Convert amount to circuit-compatible format
        const amount = Math.floor(parseFloat(transactionData.amount) * 1e6); // 6 decimal precision
        
        // Generate compliance hash
        const complianceHash = this.hashCompliance(complianceEvidence);
        
        return {
            // Public inputs
            merkle_root: merkleProof.root,
            compliance_hash: complianceHash,
            
            // Private inputs
            transaction_amount: amount.toString(),
            source_wallet_hash: sourceHash,
            dest_wallet_hash: destHash,
            kyc_status: transactionData.kyc_proof_id ? "1" : "0",
            threshold_amount: "10000000000", // 10k with 6 decimal precision
            blacklist_proof: complianceEvidence.blacklist_passed ? "1" : "0",
            merkle_path: merkleProof.pathIndices || Array(10).fill("0"),
            merkle_siblings: merkleProof.pathElements || Array(10).fill("0")
        };
    }
    
    /**
     * Hash wallet address for privacy
     */
    hashWallet(address) {
        return crypto.createHash("sha256")
            .update(address.toLowerCase())
            .digest("hex");
    }
    
    /**
     * Generate compliance evidence hash
     */
    hashCompliance(evidence) {
        const data = {
            decision: evidence.decision,
            risk_score: evidence.risk_score,
            rules_passed: evidence.rules_passed || [],
            timestamp: evidence.timestamp
        };
        
        return crypto.createHash("sha256")
            .update(JSON.stringify(data))
            .digest("hex");
    }
    
    /**
     * Hash input for verification
     */
    hashInput(input) {
        return crypto.createHash("sha256")
            .update(JSON.stringify(input))
            .digest("hex");
    }
    
    /**
     * Validate circuit input format
     */
    validateInput(input) {
        const requiredFields = [
            "merkle_root", "compliance_hash", "transaction_amount",
            "source_wallet_hash", "dest_wallet_hash", "kyc_status",
            "threshold_amount", "blacklist_proof", "merkle_path", "merkle_siblings"
        ];
        
        for (const field of requiredFields) {
            if (!(field in input)) {
                throw new Error(`Missing required field: ${field}`);
            }
        }
        
        // Validate array lengths
        if (input.merkle_path.length !== 10) {
            throw new Error("merkle_path must have exactly 10 elements");
        }
        if (input.merkle_siblings.length !== 10) {
            throw new Error("merkle_siblings must have exactly 10 elements");
        }
        
        console.log("✅ Input validation passed");
    }
    
    /**
     * Load proof from file
     */
    loadProof(proofId) {
        const proofPath = path.join(this.proofsPath, `proof_${proofId}.json`);
        if (!fs.existsSync(proofPath)) {
            throw new Error(`Proof not found: ${proofId}`);
        }
        
        return JSON.parse(fs.readFileSync(proofPath, "utf8"));
    }
    
    /**
     * List all generated proofs
     */
    listProofs() {
        const files = fs.readdirSync(this.proofsPath)
            .filter(f => f.startsWith("proof_") && f.endsWith(".json"));
        
        return files.map(f => {
            const proofId = f.replace("proof_", "").replace(".json", "");
            const proofPath = path.join(this.proofsPath, f);
            const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
            
            return {
                proofId,
                timestamp: proof.timestamp,
                circuit: proof.circuit,
                version: proof.version,
                path: proofPath
            };
        });
    }
}

// CLI interface
async function main() {
    const prover = new ProofGenerator();
    
    if (process.argv[2] === "list") {
        const proofs = prover.listProofs();
        console.log("📋 Generated proofs:");
        proofs.forEach(p => {
            console.log(`  ${p.proofId} - ${p.timestamp} (${p.circuit} v${p.version})`);
        });
        return;
    }
    
    if (process.argv[2] === "test") {
        // Test with sample input
        const inputPath = path.join(__dirname, "../test/sample_input.json");
        if (!fs.existsSync(inputPath)) {
            console.error("❌ Sample input not found. Run setup first.");
            process.exit(1);
        }
        
        const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
        await prover.generateProof(input);
        return;
    }
    
    if (process.argv[2] && fs.existsSync(process.argv[2])) {
        // Generate proof from input file
        const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
        await prover.generateProof(input);
        return;
    }
    
    console.log("Usage:");
    console.log("  node prove.js test                 - Generate proof with sample input");
    console.log("  node prove.js <input.json>         - Generate proof from input file");
    console.log("  node prove.js list                 - List all generated proofs");
}

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { ProofGenerator };
