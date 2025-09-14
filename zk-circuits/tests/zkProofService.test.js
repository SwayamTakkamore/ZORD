/**
 * Tests for ZK Proof Service
 */

const { expect } = require('chai');
const { MockZKProofService } = require('../server/zkProofService');

describe('ZK Proof Service', () => {
    let zkService;
    
    beforeEach(() => {
        zkService = new MockZKProofService();
    });
    
    describe('Proof Generation', () => {
        it('should generate a compliance proof successfully', async () => {
            const transactionData = {
                tx_uuid: 'test-tx-123',
                wallet_from: '0x742d35Cc6634C0532925a3b8D4d0C123456789AB',
                wallet_to: '0x123d35Cc6634C0532925a3b8D4d0C123456789CD',
                amount: '1000.5',
                currency: 'ETH',
                kyc_proof_id: 'kyc_12345'
            };
            
            const complianceEvidence = {
                decision: 'PASS',
                risk_score: 10,
                rules_evaluated: [
                    { rule_type: 'BLACKLIST_CHECK', passed: true },
                    { rule_type: 'AMOUNT_THRESHOLD', passed: true },
                    { rule_type: 'KYC_REQUIREMENT', passed: true }
                ]
            };
            
            const merkleProof = {
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
            };
            
            const result = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            expect(result).to.have.property('proofId');
            expect(result).to.have.property('proof');
            expect(result).to.have.property('publicSignals');
            expect(result).to.have.property('timestamp');
            expect(result.transaction_id).to.equal('test-tx-123');
            expect(result.compliance_decision).to.equal('PASS');
            
            // Validate proof structure
            expect(result.proof).to.have.property('pi_a');
            expect(result.proof).to.have.property('pi_b');
            expect(result.proof).to.have.property('pi_c');
            expect(result.proof.protocol).to.equal('groth16');
            expect(result.proof.curve).to.equal('bn128');
            
            // Validate public signals
            expect(result.publicSignals).to.be.an('array');
            expect(result.publicSignals).to.have.length(2);
        });
        
        it('should create deterministic proofs for same input', async () => {
            const transactionData = {
                tx_uuid: 'test-tx-deterministic',
                wallet_from: '0xSAME',
                wallet_to: '0xSAME',
                amount: '100',
                currency: 'ETH'
            };
            
            const complianceEvidence = {
                decision: 'PASS',
                risk_score: 0
            };
            
            const merkleProof = {
                root_hash: '12345',
                path_indices: [0],
                path_elements: ['67890']
            };
            
            const result1 = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            const result2 = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            // Different proof IDs but same proof content for same input
            expect(result1.proofId).to.not.equal(result2.proofId);
            expect(result1.input_hash).to.equal(result2.input_hash);
        });
    });
    
    describe('Proof Verification', () => {
        it('should verify a valid proof', async () => {
            // First generate a proof
            const transactionData = {
                tx_uuid: 'test-tx-verify',
                wallet_from: '0xVERIFY',
                wallet_to: '0xTEST',
                amount: '500',
                currency: 'ETH',
                kyc_proof_id: 'kyc_verify'
            };
            
            const complianceEvidence = {
                decision: 'PASS',
                risk_score: 5
            };
            
            const merkleProof = {
                root_hash: '98765432109876543210987654321098765432109876543210987654321098765432',
                path_indices: [1, 0, 1],
                path_elements: ['111', '222', '333']
            };
            
            const generated = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            // Verify the proof
            const isValid = await zkService.verifyProof(
                generated.proof,
                generated.publicSignals
            );
            
            expect(isValid).to.be.true;
        });
        
        it('should reject invalid proof structure', async () => {
            const invalidProof = {
                pi_a: ['invalid'], // Missing elements
                pi_b: [['invalid']],
                pi_c: []
            };
            
            const publicSignals = ['signal1', 'signal2'];
            
            const isValid = await zkService.verifyProof(invalidProof, publicSignals);
            expect(isValid).to.be.false;
        });
        
        it('should reject invalid public signals', async () => {
            const validProof = {
                pi_a: ['1', '2', '1'],
                pi_b: [['1', '2'], ['3', '4'], ['1', '0']],
                pi_c: ['5', '6', '1'],
                protocol: 'groth16',
                curve: 'bn128'
            };
            
            const invalidPublicSignals = ['only_one_signal']; // Should have 2
            
            const isValid = await zkService.verifyProof(validProof, invalidPublicSignals);
            expect(isValid).to.be.false;
        });
    });
    
    describe('Proof Management', () => {
        it('should verify proof by ID', async () => {
            // Generate a proof
            const transactionData = { tx_uuid: 'test-tx-id', amount: '100' };
            const complianceEvidence = { decision: 'PASS' };
            const merkleProof = { root_hash: '12345' };
            
            const generated = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            // Verify by ID
            const verificationResult = await zkService.verifyProofById(generated.proofId);
            
            expect(verificationResult.isValid).to.be.true;
            expect(verificationResult.proofId).to.equal(generated.proofId);
            expect(verificationResult.transactionId).to.equal('test-tx-id');
            expect(verificationResult.complianceDecision).to.equal('PASS');
        });
        
        it('should handle non-existent proof ID', async () => {
            const fakeId = 'non-existent-proof-id';
            const verificationResult = await zkService.verifyProofById(fakeId);
            
            expect(verificationResult.isValid).to.be.false;
            expect(verificationResult.error).to.include('not found');
        });
        
        it('should list generated proofs', async () => {
            // Generate multiple proofs
            const transactionData1 = { tx_uuid: 'tx-1', amount: '100' };
            const transactionData2 = { tx_uuid: 'tx-2', amount: '200' };
            const complianceEvidence = { decision: 'PASS' };
            const merkleProof = { root_hash: '12345' };
            
            await zkService.generateComplianceProof(transactionData1, complianceEvidence, merkleProof);
            await zkService.generateComplianceProof(transactionData2, complianceEvidence, merkleProof);
            
            const proofs = zkService.getProofs();
            
            expect(proofs).to.be.an('array');
            expect(proofs.length).to.be.at.least(2);
            
            const txIds = proofs.map(p => p.transactionId);
            expect(txIds).to.include('tx-1');
            expect(txIds).to.include('tx-2');
        });
        
        it('should delete proofs', async () => {
            // Generate a proof
            const transactionData = { tx_uuid: 'test-delete', amount: '100' };
            const complianceEvidence = { decision: 'PASS' };
            const merkleProof = { root_hash: '12345' };
            
            const generated = await zkService.generateComplianceProof(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            // Delete the proof
            const deleted = zkService.deleteProof(generated.proofId);
            expect(deleted).to.be.true;
            
            // Verify it's gone
            const verificationResult = await zkService.verifyProofById(generated.proofId);
            expect(verificationResult.isValid).to.be.false;
        });
    });
    
    describe('Utility Functions', () => {
        it('should hash objects deterministically', () => {
            const obj1 = { a: 1, b: 2, c: 3 };
            const obj2 = { c: 3, a: 1, b: 2 }; // Same content, different order
            
            const hash1 = zkService.hashObject(obj1);
            const hash2 = zkService.hashObject(obj2);
            
            expect(hash1).to.equal(hash2);
            expect(hash1).to.be.a('string');
            expect(hash1).to.have.length(64); // SHA256 hex
        });
        
        it('should prepare circuit input correctly', () => {
            const transactionData = {
                amount: '1000',
                wallet_from: '0xABC',
                wallet_to: '0xDEF',
                kyc_proof_id: 'kyc123'
            };
            
            const complianceEvidence = { decision: 'PASS' };
            const merkleProof = { root_hash: '12345' };
            
            const input = zkService.prepareCircuitInput(
                transactionData,
                complianceEvidence,
                merkleProof
            );
            
            expect(input).to.have.property('merkle_root');
            expect(input).to.have.property('compliance_hash');
            expect(input).to.have.property('transaction_amount');
            expect(input).to.have.property('source_wallet_hash');
            expect(input).to.have.property('dest_wallet_hash');
            expect(input).to.have.property('kyc_status');
            expect(input).to.have.property('threshold_amount');
            expect(input).to.have.property('blacklist_proof');
            expect(input).to.have.property('merkle_path');
            expect(input).to.have.property('merkle_siblings');
            
            expect(input.transaction_amount).to.equal('1000');
            expect(input.kyc_status).to.equal('1'); // Has KYC
            expect(input.blacklist_proof).to.equal('1'); // PASS decision
        });
        
        it('should get verification key info', () => {
            const vkInfo = zkService.getVerificationKeyInfo();
            
            expect(vkInfo).to.have.property('protocol');
            expect(vkInfo).to.have.property('curve');
            expect(vkInfo).to.have.property('nPublic');
            expect(vkInfo).to.have.property('loaded');
            
            expect(vkInfo.protocol).to.equal('groth16');
            expect(vkInfo.curve).to.equal('bn128');
            expect(vkInfo.nPublic).to.equal(2);
            expect(vkInfo.loaded).to.be.true;
        });
    });
});
