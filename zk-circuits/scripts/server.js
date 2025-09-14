const express = require("express");
const cors = require("cors");
const { ProofGenerator } = require("./prove");
const { ProofVerifier } = require("./verify");
const fs = require("fs");
const path = require("path");

/**
 * ZK Proof Service Server
 * 
 * HTTP API for generating and verifying zero-knowledge proofs
 * for compliance verification
 */

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json({ limit: "10mb" }));

// Initialize proof services
const prover = new ProofGenerator();
const verifier = new ProofVerifier();

// Health check
app.get("/health", (req, res) => {
    res.json({
        status: "healthy",
        service: "zk-proof-service",
        version: "1.0.0",
        timestamp: new Date().toISOString()
    });
});

// Get service info
app.get("/info", (req, res) => {
    try {
        const vkInfo = verifier.getVerificationKeyInfo();
        
        res.json({
            service: "ZK Proof Service for Compliance Verification",
            version: "1.0.0",
            circuit: "compliance",
            verification_key_loaded: !!vkInfo,
            verification_key_info: vkInfo,
            endpoints: {
                "POST /prove": "Generate ZK proof",
                "POST /prove/compliance": "Generate compliance proof from transaction data",
                "POST /verify": "Verify ZK proof",
                "POST /verify/compliance": "Verify compliance proof with additional checks",
                "GET /proofs": "List all generated proofs",
                "GET /proofs/:id": "Get specific proof",
                "DELETE /proofs/:id": "Delete specific proof"
            }
        });
    } catch (error) {
        res.status(500).json({
            error: "Failed to get service info",
            message: error.message
        });
    }
});

// Generate ZK proof from circuit input
app.post("/prove", async (req, res) => {
    try {
        const { input } = req.body;
        
        if (!input) {
            return res.status(400).json({
                error: "Missing required field: input"
            });
        }
        
        const result = await prover.generateProof(input);
        
        res.json({
            success: true,
            proof_id: result.proofId,
            proof: result.proof,
            public_signals: result.publicSignals,
            timestamp: result.timestamp,
            path: result.proofPath
        });
        
    } catch (error) {
        console.error("Proof generation error:", error);
        res.status(500).json({
            error: "Proof generation failed",
            message: error.message
        });
    }
});

// Generate compliance proof from transaction data
app.post("/prove/compliance", async (req, res) => {
    try {
        const { transaction_data, compliance_evidence, merkle_proof } = req.body;
        
        // Validate required fields
        if (!transaction_data || !compliance_evidence || !merkle_proof) {
            return res.status(400).json({
                error: "Missing required fields",
                required: ["transaction_data", "compliance_evidence", "merkle_proof"]
            });
        }
        
        const result = await prover.proveCompliance(
            transaction_data,
            compliance_evidence,
            merkle_proof
        );
        
        res.json({
            success: true,
            proof_id: result.proofId,
            proof: result.proof,
            public_signals: result.publicSignals,
            merkle_root: result.publicSignals[0],
            compliance_hash: result.publicSignals[1],
            timestamp: result.timestamp,
            path: result.proofPath
        });
        
    } catch (error) {
        console.error("Compliance proof generation error:", error);
        res.status(500).json({
            error: "Compliance proof generation failed",
            message: error.message
        });
    }
});

// Verify ZK proof
app.post("/verify", async (req, res) => {
    try {
        const { proof, public_signals } = req.body;
        
        if (!proof || !public_signals) {
            return res.status(400).json({
                error: "Missing required fields",
                required: ["proof", "public_signals"]
            });
        }
        
        const valid = await verifier.verifyProof(proof, public_signals);
        
        res.json({
            valid,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error("Proof verification error:", error);
        res.status(500).json({
            error: "Proof verification failed",
            message: error.message
        });
    }
});

// Verify compliance proof with additional checks
app.post("/verify/compliance", async (req, res) => {
    try {
        const { proof_data, expected_public_inputs } = req.body;
        
        if (!proof_data) {
            return res.status(400).json({
                error: "Missing required field: proof_data"
            });
        }
        
        const result = await verifier.verifyComplianceProof(
            proof_data,
            expected_public_inputs
        );
        
        res.json(result);
        
    } catch (error) {
        console.error("Compliance verification error:", error);
        res.status(500).json({
            error: "Compliance verification failed",
            message: error.message
        });
    }
});

// List all generated proofs
app.get("/proofs", (req, res) => {
    try {
        const proofs = prover.listProofs();
        
        res.json({
            count: proofs.length,
            proofs: proofs
        });
        
    } catch (error) {
        console.error("List proofs error:", error);
        res.status(500).json({
            error: "Failed to list proofs",
            message: error.message
        });
    }
});

// Get specific proof
app.get("/proofs/:id", (req, res) => {
    try {
        const proofId = req.params.id;
        const proof = prover.loadProof(proofId);
        
        res.json(proof);
        
    } catch (error) {
        if (error.message.includes("not found")) {
            res.status(404).json({
                error: "Proof not found",
                proof_id: req.params.id
            });
        } else {
            console.error("Get proof error:", error);
            res.status(500).json({
                error: "Failed to get proof",
                message: error.message
            });
        }
    }
});

// Delete specific proof
app.delete("/proofs/:id", (req, res) => {
    try {
        const proofId = req.params.id;
        const proofPath = path.join(prover.proofsPath, `proof_${proofId}.json`);
        
        if (!fs.existsSync(proofPath)) {
            return res.status(404).json({
                error: "Proof not found",
                proof_id: proofId
            });
        }
        
        fs.unlinkSync(proofPath);
        
        res.json({
            success: true,
            message: "Proof deleted successfully",
            proof_id: proofId
        });
        
    } catch (error) {
        console.error("Delete proof error:", error);
        res.status(500).json({
            error: "Failed to delete proof",
            message: error.message
        });
    }
});

// Batch verify proofs
app.post("/verify/batch", async (req, res) => {
    try {
        const { proof_ids } = req.body;
        
        if (!proof_ids || !Array.isArray(proof_ids)) {
            return res.status(400).json({
                error: "Missing or invalid field: proof_ids (must be array)"
            });
        }
        
        const results = await verifier.batchVerify(proof_ids);
        
        const summary = {
            total: results.length,
            valid: results.filter(r => r.valid).length,
            invalid: results.filter(r => !r.valid).length
        };
        
        res.json({
            summary,
            results
        });
        
    } catch (error) {
        console.error("Batch verification error:", error);
        res.status(500).json({
            error: "Batch verification failed",
            message: error.message
        });
    }
});

// Export verification key for smart contracts
app.get("/verification-key/contract", (req, res) => {
    try {
        const contractKey = verifier.exportVerificationKeyForContract();
        
        res.json({
            verification_key: contractKey,
            format: "solidity_compatible",
            usage: "Deploy this key to your smart contract verifier"
        });
        
    } catch (error) {
        console.error("Export verification key error:", error);
        res.status(500).json({
            error: "Failed to export verification key",
            message: error.message
        });
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error("Unhandled error:", error);
    res.status(500).json({
        error: "Internal server error",
        message: error.message
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: "Endpoint not found",
        path: req.path,
        method: req.method
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 ZK Proof Service running on port ${PORT}`);
    console.log(`🔗 API endpoint: http://localhost:${PORT}`);
    console.log(`🔍 Health check: http://localhost:${PORT}/health`);
    console.log(`📖 Service info: http://localhost:${PORT}/info`);
});

module.exports = app;
