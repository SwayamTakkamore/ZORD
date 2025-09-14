/**
 * ZK Proof Service HTTP Server
 * 
 * Provides REST API endpoints for generating and verifying
 * zero-knowledge proofs for compliance verification
 */

const express = require('express');
const cors = require('cors');
const { MockZKProofService } = require('./zkProofService');

const app = express();
const PORT = process.env.PORT || 3001;

// Initialize ZK proof service
const zkService = new MockZKProofService();

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Request logging
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
    next();
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'zk-proof-service',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

// Service information
app.get('/info', (req, res) => {
    try {
        const vkInfo = zkService.getVerificationKeyInfo();
        
        res.json({
            service: 'ZK Proof Service for Compliance Verification',
            version: '1.0.0',
            circuit: 'compliance_verification',
            verification_key_loaded: vkInfo.loaded,
            verification_key_info: vkInfo,
            endpoints: {
                'POST /prove/compliance': 'Generate ZK proof for compliance verification',
                'POST /verify': 'Verify ZK proof',
                'GET /proofs': 'List all generated proofs',
                'GET /proofs/:id': 'Get specific proof',
                'DELETE /proofs/:id': 'Delete specific proof',
                'GET /info': 'Get service information',
                'GET /health': 'Health check'
            }
        });
    } catch (error) {
        res.status(500).json({
            error: 'Failed to get service info',
            message: error.message
        });
    }
});

// Generate ZK proof for compliance verification
app.post('/prove/compliance', async (req, res) => {
    try {
        const { transactionData, complianceEvidence, merkleProof } = req.body;
        
        // Validate required fields
        if (!transactionData || !complianceEvidence || !merkleProof) {
            return res.status(400).json({
                error: 'Missing required fields',
                required: ['transactionData', 'complianceEvidence', 'merkleProof']
            });
        }
        
        // Generate proof
        const result = await zkService.generateComplianceProof(
            transactionData,
            complianceEvidence,
            merkleProof
        );
        
        res.json({
            success: true,
            proof_id: result.proofId,
            proof: result.proof,
            public_signals: result.publicSignals,
            timestamp: result.timestamp,
            transaction_id: result.transaction_id,
            compliance_decision: result.compliance_decision
        });
        
    } catch (error) {
        console.error('❌ Proof generation failed:', error);
        res.status(500).json({
            error: 'Proof generation failed',
            message: error.message
        });
    }
});

// Verify ZK proof
app.post('/verify', async (req, res) => {
    try {
        const { proof, publicSignals, proofId } = req.body;
        
        let verificationResult;
        
        if (proofId) {
            // Verify by ID
            verificationResult = await zkService.verifyProofById(proofId);
        } else if (proof && publicSignals) {
            // Verify provided proof
            const isValid = await zkService.verifyProof(proof, publicSignals);
            verificationResult = {
                isValid,
                timestamp: new Date().toISOString()
            };
        } else {
            return res.status(400).json({
                error: 'Missing required fields',
                required: 'Either proofId OR (proof AND publicSignals)'
            });
        }
        
        res.json({
            success: true,
            verification_result: verificationResult,
            verified_at: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('❌ Proof verification failed:', error);
        res.status(500).json({
            error: 'Proof verification failed',
            message: error.message
        });
    }
});

// List all proofs
app.get('/proofs', (req, res) => {
    try {
        const proofs = zkService.getProofs();
        
        res.json({
            success: true,
            count: proofs.length,
            proofs: proofs
        });
        
    } catch (error) {
        console.error('❌ Failed to list proofs:', error);
        res.status(500).json({
            error: 'Failed to list proofs',
            message: error.message
        });
    }
});

// Get specific proof
app.get('/proofs/:id', async (req, res) => {
    try {
        const proofId = req.params.id;
        const verificationResult = await zkService.verifyProofById(proofId);
        
        if (!verificationResult.isValid && verificationResult.error) {
            return res.status(404).json({
                error: 'Proof not found',
                proof_id: proofId
            });
        }
        
        res.json({
            success: true,
            proof_id: proofId,
            verification_result: verificationResult
        });
        
    } catch (error) {
        console.error('❌ Failed to get proof:', error);
        res.status(500).json({
            error: 'Failed to get proof',
            message: error.message
        });
    }
});

// Delete specific proof
app.delete('/proofs/:id', (req, res) => {
    try {
        const proofId = req.params.id;
        const deleted = zkService.deleteProof(proofId);
        
        if (deleted) {
            res.json({
                success: true,
                message: 'Proof deleted successfully',
                proof_id: proofId
            });
        } else {
            res.status(404).json({
                error: 'Proof not found',
                proof_id: proofId
            });
        }
        
    } catch (error) {
        console.error('❌ Failed to delete proof:', error);
        res.status(500).json({
            error: 'Failed to delete proof',
            message: error.message
        });
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('❌ Server error:', error);
    res.status(500).json({
        error: 'Internal server error',
        message: error.message
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Endpoint not found',
        path: req.path,
        method: req.method
    });
});

// Start server
const server = app.listen(PORT, () => {
    console.log(`🚀 ZK Proof Service running on port ${PORT}`);
    console.log(`📖 API Documentation: http://localhost:${PORT}/info`);
    console.log(`❤️ Health Check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

module.exports = app;
