const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

/**
 * Setup Script for ZK Circuit
 * 
 * This script:
 * 1. Compiles the Circom circuit
 * 2. Generates the trusted setup (Powers of Tau)
 * 3. Creates proving and verifying keys
 * 4. Exports the verification key for smart contract deployment
 */

async function setup() {
    console.log("🔧 Starting ZK Circuit Setup...");
    
    const circuitName = "compliance";
    const circuitPath = path.join(__dirname, "../circuits", `${circuitName}.circom`);
    const buildPath = path.join(__dirname, "../build");
    const keysPath = path.join(__dirname, "../keys");
    
    // Ensure directories exist
    if (!fs.existsSync(buildPath)) {
        fs.mkdirSync(buildPath, { recursive: true });
    }
    if (!fs.existsSync(keysPath)) {
        fs.mkdirSync(keysPath, { recursive: true });
    }
    
    try {
        console.log("📝 Compiling circuit...");
        
        // For this demo, we'll use a pre-computed trusted setup
        // In production, you'd want to participate in a ceremony
        console.log("⚡ Setting up Powers of Tau...");
        
        const ptauPath = path.join(keysPath, "pot12_final.ptau");
        
        // Download or generate Powers of Tau file (for demo, we'll create a small one)
        if (!fs.existsSync(ptauPath)) {
            console.log("📦 Generating Powers of Tau (this may take a while)...");
            await snarkjs.powersOfTau.newAccumulator(
                "bn128",
                12, // 2^12 = 4096 constraints max
                ptauPath + "_0000.ptau"
            );
            
            await snarkjs.powersOfTau.contribute(
                ptauPath + "_0000.ptau",
                ptauPath + "_0001.ptau",
                "compliance-copilot-contribution",
                "random entropy for demo"
            );
            
            await snarkjs.powersOfTau.preparePhase2(
                ptauPath + "_0001.ptau",
                ptauPath
            );
            
            // Cleanup intermediate files
            fs.unlinkSync(ptauPath + "_0000.ptau");
            fs.unlinkSync(ptauPath + "_0001.ptau");
        }
        
        console.log("🔑 Generating circuit-specific setup...");
        
        const r1csPath = path.join(buildPath, `${circuitName}.r1cs`);
        const wasmPath = path.join(buildPath, `${circuitName}.wasm`);
        const zkeyPath = path.join(keysPath, `${circuitName}.zkey`);
        const vkeyPath = path.join(keysPath, `${circuitName}_vkey.json`);
        
        // Assume circuit compilation was done via CLI
        // circom circuits/compliance.circom --r1cs --wasm --sym -o build/
        
        if (!fs.existsSync(r1csPath)) {
            console.log("❌ Circuit not compiled. Please run: npm run compile");
            process.exit(1);
        }
        
        // Generate zkey (circuit-specific setup)
        await snarkjs.groth16.setup(r1csPath, ptauPath, zkeyPath);
        
        // Export verification key
        const vKey = await snarkjs.zKey.exportVerificationKey(zkeyPath);
        fs.writeFileSync(vkeyPath, JSON.stringify(vKey, null, 2));
        
        // Generate Solidity verifier contract
        const solidityVerifier = await snarkjs.zKey.exportSolidityVerifier(zkeyPath);
        const verifierPath = path.join(keysPath, "verifier.sol");
        fs.writeFileSync(verifierPath, solidityVerifier);
        
        console.log("✅ Setup completed successfully!");
        console.log(`📁 Proving key: ${zkeyPath}`);
        console.log(`📁 Verification key: ${vkeyPath}`);
        console.log(`📁 Solidity verifier: ${verifierPath}`);
        
        // Generate sample input for testing
        const sampleInput = {
            merkle_root: "21663839004416932945382355908790599925860083875847006286441766793392576948380",
            compliance_hash: "12345678901234567890123456789012345678901234567890123456789012345678901234",
            transaction_amount: "1000",
            source_wallet_hash: "11111111111111111111111111111111111111111111111111111111111111111111111111",
            dest_wallet_hash: "22222222222222222222222222222222222222222222222222222222222222222222222222",
            kyc_status: "1",
            threshold_amount: "10000",
            blacklist_proof: "1",
            merkle_path: ["0", "1", "0", "1", "0", "1", "0", "1", "0", "1"],
            merkle_siblings: [
                "0", "0", "0", "0", "0", "0", "0", "0", "0", "0"
            ]
        };
        
        const inputPath = path.join(__dirname, "../test", "sample_input.json");
        const testDir = path.dirname(inputPath);
        if (!fs.existsSync(testDir)) {
            fs.mkdirSync(testDir, { recursive: true });
        }
        fs.writeFileSync(inputPath, JSON.stringify(sampleInput, null, 2));
        console.log(`📁 Sample input: ${inputPath}`);
        
    } catch (error) {
        console.error("❌ Setup failed:", error);
        process.exit(1);
    }
}

// Run setup if called directly
if (require.main === module) {
    setup().catch(console.error);
}

module.exports = { setup };
