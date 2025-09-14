/**
 * HTTP API Tests for ZK Proof Service
 */

const { expect } = require('chai');
const request = require('supertest');
const app = require('../server/index');

describe('ZK Proof Service HTTP API', () => {
    
    describe('GET /health', () => {
        it('should return health status', async () => {
            const response = await request(app)
                .get('/health')
                .expect(200);
            
            expect(response.body).to.have.property('status', 'healthy');
            expect(response.body).to.have.property('service', 'zk-proof-service');
            expect(response.body).to.have.property('version', '1.0.0');
            expect(response.body).to.have.property('timestamp');
        });
    });
    
    describe('GET /info', () => {
        it('should return service information', async () => {
            const response = await request(app)
                .get('/info')
                .expect(200);
            
            expect(response.body).to.have.property('service');
            expect(response.body).to.have.property('version', '1.0.0');
            expect(response.body).to.have.property('circuit', 'compliance_verification');
            expect(response.body).to.have.property('verification_key_loaded', true);
            expect(response.body).to.have.property('verification_key_info');
            expect(response.body).to.have.property('endpoints');
            
            const vkInfo = response.body.verification_key_info;
            expect(vkInfo).to.have.property('protocol', 'groth16');
            expect(vkInfo).to.have.property('curve', 'bn128');
            expect(vkInfo).to.have.property('nPublic', 2);
            expect(vkInfo).to.have.property('loaded', true);
        });
    });
    
    describe('POST /prove/compliance', () => {
        it('should generate compliance proof successfully', async () => {
            const requestBody = {
                transactionData: {
                    tx_uuid: 'test-tx-api-123',
                    wallet_from: '0x742d35Cc6634C0532925a3b8D4d0C123456789AB',
                    wallet_to: '0x123d35Cc6634C0532925a3b8D4d0C123456789CD',
                    amount: '1000.5',
                    currency: 'ETH',
                    kyc_proof_id: 'kyc_12345'
                },
                complianceEvidence: {
                    decision: 'PASS',
                    risk_score: 10,
                    rules_evaluated: [
                        { rule_type: 'BLACKLIST_CHECK', passed: true },
                        { rule_type: 'AMOUNT_THRESHOLD', passed: true },
                        { rule_type: 'KYC_REQUIREMENT', passed: true }
                    ]
                },
                merkleProof: {
                    root_hash: '21663839004416932945382355908790599925860083875847006286441766793392576948380',
                    path_indices: [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                    path_elements: [
                        '12345678901234567890123456789012345678901234567890123456789012345678901234',
                        '23456789012345678901234567890123456789012345678901234567890123456789012345',
                        '34567890123456789012345678901234567890123456789012345678901234567890123456',
                        '45678901234567890123456789012345678901234567890123456789012345678901234567',
                        '56789012345678901234567890123456789012345678901234567890123456789012345678',
                        '67890123456789012345678901234567890123456789012345678901234567890123456789',
                        '78901234567890123456789012345678901234567890123456789012345678901234567890',
                        '89012345678901234567890123456789012345678901234567890123456789012345678901',
                        '90123456789012345678901234567890123456789012345678901234567890123456789012',
                        '01234567890123456789012345678901234567890123456789012345678901234567890123'
                    ]
                }
            };
            
            const response = await request(app)
                .post('/prove/compliance')
                .send(requestBody)
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('proof_id');
            expect(response.body).to.have.property('proof');
            expect(response.body).to.have.property('public_signals');
            expect(response.body).to.have.property('timestamp');
            expect(response.body).to.have.property('transaction_id', 'test-tx-api-123');
            expect(response.body).to.have.property('compliance_decision', 'PASS');
            
            // Validate proof structure
            const proof = response.body.proof;
            expect(proof).to.have.property('pi_a');
            expect(proof).to.have.property('pi_b');
            expect(proof).to.have.property('pi_c');
            expect(proof).to.have.property('protocol', 'groth16');
            expect(proof).to.have.property('curve', 'bn128');
            
            // Validate public signals
            expect(response.body.public_signals).to.be.an('array');
            expect(response.body.public_signals).to.have.length(2);
        });
        
        it('should return 400 for missing fields', async () => {
            const incompleteRequestBody = {
                transactionData: {
                    tx_uuid: 'test-incomplete'
                }
                // Missing complianceEvidence and merkleProof
            };
            
            const response = await request(app)
                .post('/prove/compliance')
                .send(incompleteRequestBody)
                .expect(400);
            
            expect(response.body).to.have.property('error', 'Missing required fields');
            expect(response.body).to.have.property('required');
            expect(response.body.required).to.include('transactionData');
            expect(response.body.required).to.include('complianceEvidence');
            expect(response.body.required).to.include('merkleProof');
        });
    });
    
    describe('POST /verify', () => {
        let generatedProofId;
        let generatedProof;
        let generatedPublicSignals;
        
        beforeEach(async () => {
            // Generate a proof first
            const requestBody = {
                transactionData: {
                    tx_uuid: 'test-verify-api',
                    wallet_from: '0xVERIFY',
                    wallet_to: '0xTEST',
                    amount: '500',
                    currency: 'ETH'
                },
                complianceEvidence: {
                    decision: 'PASS',
                    risk_score: 5
                },
                merkleProof: {
                    root_hash: '98765432109876543210987654321098765432109876543210987654321098765432',
                    path_indices: [1, 0, 1],
                    path_elements: ['111', '222', '333']
                }
            };
            
            const response = await request(app)
                .post('/prove/compliance')
                .send(requestBody)
                .expect(200);
            
            generatedProofId = response.body.proof_id;
            generatedProof = response.body.proof;
            generatedPublicSignals = response.body.public_signals;
        });
        
        it('should verify proof by ID', async () => {
            const response = await request(app)
                .post('/verify')
                .send({ proofId: generatedProofId })
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('verification_result');
            expect(response.body).to.have.property('verified_at');
            
            const result = response.body.verification_result;
            expect(result).to.have.property('isValid', true);
            expect(result).to.have.property('proofId', generatedProofId);
            expect(result).to.have.property('transactionId', 'test-verify-api');
            expect(result).to.have.property('complianceDecision', 'PASS');
        });
        
        it('should verify proof by providing proof and public signals', async () => {
            const response = await request(app)
                .post('/verify')
                .send({
                    proof: generatedProof,
                    publicSignals: generatedPublicSignals
                })
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('verification_result');
            
            const result = response.body.verification_result;
            expect(result).to.have.property('isValid', true);
            expect(result).to.have.property('timestamp');
        });
        
        it('should return 400 for missing verification data', async () => {
            const response = await request(app)
                .post('/verify')
                .send({})
                .expect(400);
            
            expect(response.body).to.have.property('error', 'Missing required fields');
            expect(response.body).to.have.property('required');
        });
        
        it('should handle non-existent proof ID', async () => {
            const response = await request(app)
                .post('/verify')
                .send({ proofId: 'non-existent-id' })
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            const result = response.body.verification_result;
            expect(result).to.have.property('isValid', false);
            expect(result).to.have.property('error');
        });
    });
    
    describe('GET /proofs', () => {
        beforeEach(async () => {
            // Generate some proofs
            const requestBody1 = {
                transactionData: { tx_uuid: 'list-test-1', amount: '100' },
                complianceEvidence: { decision: 'PASS' },
                merkleProof: { root_hash: '12345' }
            };
            
            const requestBody2 = {
                transactionData: { tx_uuid: 'list-test-2', amount: '200' },
                complianceEvidence: { decision: 'HOLD' },
                merkleProof: { root_hash: '67890' }
            };
            
            await request(app).post('/prove/compliance').send(requestBody1);
            await request(app).post('/prove/compliance').send(requestBody2);
        });
        
        it('should list all generated proofs', async () => {
            const response = await request(app)
                .get('/proofs')
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('count');
            expect(response.body).to.have.property('proofs');
            expect(response.body.proofs).to.be.an('array');
            expect(response.body.count).to.be.at.least(2);
            
            const txIds = response.body.proofs.map(p => p.transactionId);
            expect(txIds).to.include('list-test-1');
            expect(txIds).to.include('list-test-2');
        });
    });
    
    describe('GET /proofs/:id', () => {
        let testProofId;
        
        beforeEach(async () => {
            // Generate a proof
            const requestBody = {
                transactionData: { tx_uuid: 'get-test', amount: '300' },
                complianceEvidence: { decision: 'PASS' },
                merkleProof: { root_hash: '54321' }
            };
            
            const response = await request(app)
                .post('/prove/compliance')
                .send(requestBody)
                .expect(200);
            
            testProofId = response.body.proof_id;
        });
        
        it('should get specific proof by ID', async () => {
            const response = await request(app)
                .get(`/proofs/${testProofId}`)
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('proof_id', testProofId);
            expect(response.body).to.have.property('verification_result');
            
            const result = response.body.verification_result;
            expect(result).to.have.property('isValid', true);
            expect(result).to.have.property('transactionId', 'get-test');
            expect(result).to.have.property('complianceDecision', 'PASS');
        });
        
        it('should return 404 for non-existent proof', async () => {
            const response = await request(app)
                .get('/proofs/non-existent-id')
                .expect(404);
            
            expect(response.body).to.have.property('error', 'Proof not found');
        });
    });
    
    describe('DELETE /proofs/:id', () => {
        let testProofId;
        
        beforeEach(async () => {
            // Generate a proof
            const requestBody = {
                transactionData: { tx_uuid: 'delete-test', amount: '400' },
                complianceEvidence: { decision: 'PASS' },
                merkleProof: { root_hash: '11111' }
            };
            
            const response = await request(app)
                .post('/prove/compliance')
                .send(requestBody)
                .expect(200);
            
            testProofId = response.body.proof_id;
        });
        
        it('should delete proof successfully', async () => {
            const response = await request(app)
                .delete(`/proofs/${testProofId}`)
                .expect(200);
            
            expect(response.body).to.have.property('success', true);
            expect(response.body).to.have.property('message', 'Proof deleted successfully');
            expect(response.body).to.have.property('proof_id', testProofId);
            
            // Verify proof is deleted
            await request(app)
                .get(`/proofs/${testProofId}`)
                .expect(404);
        });
        
        it('should return 404 when deleting non-existent proof', async () => {
            const response = await request(app)
                .delete('/proofs/non-existent-id')
                .expect(404);
            
            expect(response.body).to.have.property('error', 'Proof not found');
        });
    });
    
    describe('Error Handling', () => {
        it('should return 404 for unknown endpoints', async () => {
            const response = await request(app)
                .get('/unknown-endpoint')
                .expect(404);
            
            expect(response.body).to.have.property('error', 'Endpoint not found');
            expect(response.body).to.have.property('path', '/unknown-endpoint');
            expect(response.body).to.have.property('method', 'GET');
        });
    });
});
