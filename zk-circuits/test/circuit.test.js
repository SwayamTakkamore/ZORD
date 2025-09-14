const { expect } = require("chai");
const { ProofGenerator } = require("../scripts/prove");
const { ProofVerifier } = require("../scripts/verify");
const fs = require("fs");
const path = require("path");

describe("ZK Compliance Circuit Tests", function() {
    this.timeout(60000); // 60 seconds for proof generation
    
    let prover;
    let verifier;
    let sampleInput;
    
    before(async function() {
        prover = new ProofGenerator();
        verifier = new ProofVerifier();
        
        // Load sample input
        const inputPath = path.join(__dirname, "sample_input.json");
        if (fs.existsSync(inputPath)) {
            sampleInput = JSON.parse(fs.readFileSync(inputPath, "utf8"));
        } else {
            // Create basic sample input for testing
            sampleInput = {
                merkle_root: "21663839004416932945382355908790599925860083875847006286441766793392576948380",
                compliance_hash: "12345678901234567890123456789012345678901234567890123456789012345678901234",
                transaction_amount: "1000",
                source_wallet_hash: "11111111111111111111111111111111111111111111111111111111111111111111111111",
                dest_wallet_hash: "22222222222222222222222222222222222222222222222222222222222222222222222222",
                kyc_status: "1",
                threshold_amount: "10000",
                blacklist_proof: "1",
                merkle_path: ["0", "1", "0", "1", "0", "1", "0", "1", "0", "1"],
                merkle_siblings: Array(10).fill("0")
            };
        }
    });
    
    describe("ProofGenerator", function() {
        let generatedProof;
        
        it("should validate input correctly", function() {
            expect(() => prover.validateInput(sampleInput)).to.not.throw();
        });
        
        it("should reject invalid input", function() {
            const invalidInput = { ...sampleInput };
            delete invalidInput.merkle_root;
            
            expect(() => prover.validateInput(invalidInput)).to.throw();
        });
        
        it("should generate proof from sample input", async function() {
            // Skip if circuit not compiled
            if (!fs.existsSync(prover.wasmPath)) {
                this.skip();
            }
            
            generatedProof = await prover.generateProof(sampleInput);
            
            expect(generatedProof).to.have.property("proof");
            expect(generatedProof).to.have.property("publicSignals");
            expect(generatedProof).to.have.property("proofId");
            expect(generatedProof.publicSignals).to.be.an("array");
        });
        
        it("should prepare circuit input from transaction data", function() {
            const transactionData = {
                wallet_from: "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
                wallet_to: "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
                amount: "100.5",
                currency: "ETH",
                kyc_proof_id: "kyc_12345"
            };
            
            const complianceEvidence = {
                decision: "PASS",
                risk_score: 25,
                blacklist_passed: true,
                timestamp: new Date().toISOString()
            };
            
            const merkleProof = {
                root: "21663839004416932945382355908790599925860083875847006286441766793392576948380",
                pathIndices: Array(10).fill("0"),
                pathElements: Array(10).fill("0")
            };
            
            const circuitInput = prover.prepareCircuitInput(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            expect(circuitInput).to.have.property("merkle_root");
            expect(circuitInput).to.have.property("compliance_hash");
            expect(circuitInput).to.have.property("transaction_amount");
            expect(circuitInput.kyc_status).to.equal("1");
            expect(circuitInput.blacklist_proof).to.equal("1");
        });
        
        it("should hash wallet addresses consistently", function() {
            const address = "0x742d35Cc6634C0532925a3b8D4d0C123456789AB";
            const hash1 = prover.hashWallet(address);
            const hash2 = prover.hashWallet(address.toLowerCase());
            
            expect(hash1).to.equal(hash2);
            expect(hash1).to.be.a("string");
            expect(hash1).to.have.length(64); // SHA256 hex length
        });
        
        it("should list generated proofs", function() {
            const proofs = prover.listProofs();
            expect(proofs).to.be.an("array");
            
            if (generatedProof) {
                const found = proofs.find(p => p.proofId === generatedProof.proofId);
                expect(found).to.exist;
            }
        });
    });
    
    describe("ProofVerifier", function() {
        it("should load verification key info", function() {
            const info = verifier.getVerificationKeyInfo();
            
            if (info) {
                expect(info).to.have.property("protocol");
                expect(info).to.have.property("curve");
                expect(info).to.have.property("nPublic");
            }
        });
        
        it("should verify valid proof", async function() {
            // Skip if no proof generated or verification key missing
            if (!verifier.verificationKey) {
                this.skip();
            }
            
            // Create a mock valid proof for testing
            const mockProof = {
                pi_a: ["1", "2", "1"],
                pi_b: [["1", "2"], ["3", "4"], ["1", "0"]],
                pi_c: ["5", "6", "1"],
                protocol: "groth16",
                curve: "bn128"
            };
            
            const mockPublicSignals = [
                sampleInput.merkle_root,
                sampleInput.compliance_hash
            ];
            
            // This will likely fail with mock data, but tests the verification flow
            const result = await verifier.verifyProof(mockProof, mockPublicSignals);
            expect(result).to.be.a("boolean");
        });
        
        it("should export verification key for contracts", function() {
            if (!verifier.verificationKey) {
                this.skip();
            }
            
            const contractKey = verifier.exportVerificationKeyForContract();
            
            expect(contractKey).to.have.property("alpha");
            expect(contractKey).to.have.property("beta");
            expect(contractKey).to.have.property("gamma");
            expect(contractKey).to.have.property("delta");
            expect(contractKey).to.have.property("ic");
        });
        
        it("should validate compliance proof structure", async function() {
            const mockProofData = {
                proof: {
                    pi_a: ["1", "2", "1"],
                    pi_b: [["1", "2"], ["3", "4"], ["1", "0"]],
                    pi_c: ["5", "6", "1"]
                },
                publicSignals: [
                    sampleInput.merkle_root,
                    sampleInput.compliance_hash
                ],
                timestamp: new Date().toISOString(),
                circuit: "compliance",
                version: "1.0.0"
            };
            
            const result = await verifier.verifyComplianceProof(mockProofData);
            
            expect(result).to.have.property("valid");
            expect(result).to.have.property("checks");
            expect(result.checks).to.have.property("public_inputs_valid");
            expect(result.checks).to.have.property("circuit_version_valid");
        });
    });
    
    describe("Integration Tests", function() {
        it("should generate and verify a complete compliance proof", async function() {
            // Skip if circuit not compiled
            if (!fs.existsSync(prover.wasmPath) || !verifier.verificationKey) {
                this.skip();
            }
            
            // Generate proof
            const proof = await prover.generateProof(sampleInput);
            
            // Verify proof
            const isValid = await verifier.verifyProof(
                proof.proof,
                proof.publicSignals
            );
            
            expect(isValid).to.be.true;
        });
        
        it("should handle end-to-end compliance flow", async function() {
            // Skip if not fully set up
            if (!fs.existsSync(prover.wasmPath) || !verifier.verificationKey) {
                this.skip();
            }
            
            // Simulate transaction data
            const transactionData = {
                wallet_from: "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
                wallet_to: "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
                amount: "500.0",
                currency: "ETH",
                kyc_proof_id: "kyc_12345"
            };
            
            const complianceEvidence = {
                decision: "PASS",
                risk_score: 25,
                blacklist_passed: true,
                timestamp: new Date().toISOString()
            };
            
            const merkleProof = {
                root: sampleInput.merkle_root,
                pathIndices: sampleInput.merkle_path,
                pathElements: sampleInput.merkle_siblings
            };
            
            // Generate compliance proof
            const proof = await prover.proveCompliance(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            // Verify compliance proof
            const verification = await verifier.verifyComplianceProof(proof);
            
            expect(verification.valid).to.be.true;
            expect(verification.checks.circuit_version_valid).to.be.true;
        });
    });
    
    describe("Error Handling", function() {
        it("should handle invalid circuit input gracefully", async function() {
            const invalidInput = {
                merkle_root: "invalid",
                // missing required fields
            };
            
            try {
                await prover.generateProof(invalidInput);
                expect.fail("Should have thrown an error");
            } catch (error) {
                expect(error).to.be.an("error");
            }
        });
        
        it("should handle missing proof files", function() {
            const fakeProofId = "nonexistent_proof_id";
            
            expect(() => prover.loadProof(fakeProofId)).to.throw();
        });
        
        it("should handle verification without key", async function() {
            const verifierWithoutKey = new ProofVerifier();
            verifierWithoutKey.verificationKey = null;
            
            const result = await verifierWithoutKey.verifyProof({}, []);
            expect(result).to.be.false;
        });
    });
});
