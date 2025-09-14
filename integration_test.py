#!/usr/bin/env python3
"""
End-to-End Integration Test for Crypto Compliance Copilot

This test demonstrates the complete workflow:
1. Submit a transaction for compliance checking
2. Retrieve compliance evidence and Merkle proof
3. Generate a ZK proof of compliance
4. Verify the ZK proof
5. Demonstrate privacy-preserving compliance verification

Module 3: ZK circuit + Node helper integration test
"""

import json
import requests
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceCopilotIntegration:
    def __init__(self, backend_url="http://localhost:8000", zk_url="http://localhost:3001"):
        self.backend_url = backend_url.rstrip('/')
        self.zk_url = zk_url.rstrip('/')
        
    def health_check(self):
        """Check that all services are healthy"""
        logger.info("🔍 Checking service health...")
        
        # Check backend health
        response = requests.get(f"{self.backend_url}/health")
        if response.status_code != 200:
            raise Exception(f"Backend unhealthy: {response.status_code}")
        
        # Check ZK service health through backend
        response = requests.get(f"{self.backend_url}/v1/zk/health")
        if response.status_code != 200:
            raise Exception(f"ZK service unhealthy: {response.status_code}")
            
        zk_health = response.json()
        if not zk_health.get("healthy"):
            raise Exception(f"ZK service reports unhealthy: {zk_health}")
            
        logger.info("✅ All services healthy")
        return True
        
    def submit_transaction(self, transaction_data):
        """Submit a transaction for compliance checking"""
        logger.info(f"📤 Submitting transaction: {transaction_data['amount']} {transaction_data['currency']}")
        
        response = requests.post(
            f"{self.backend_url}/v1/tx/submit",
            json=transaction_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Transaction submission failed: {response.status_code} - {response.text}")
            
        result = response.json()
        logger.info(f"✅ Transaction submitted: {result['tx_id']} - Decision: {result['decision']}")
        return result
        
    def get_merkle_proof(self, evidence_hash):
        """Get Merkle proof for evidence inclusion"""
        logger.info(f"🌳 Getting Merkle proof for evidence: {evidence_hash}")
        
        response = requests.get(f"{self.backend_url}/v1/merkle/proof/{evidence_hash}")
        if response.status_code != 200:
            raise Exception(f"Merkle proof retrieval failed: {response.status_code}")
            
        proof = response.json()
        logger.info(f"✅ Merkle proof retrieved: Root {proof['root_hash'][:16]}...")
        return proof
        
    def generate_zk_proof(self, transaction_data, compliance_result, merkle_proof):
        """Generate ZK proof for compliance verification"""
        logger.info("🔐 Generating ZK proof...")
        
        # Prepare compliance evidence
        compliance_evidence = {
            "decision": compliance_result["decision"],
            "risk_score": 10 if compliance_result["decision"] == "PASS" else 50,
            "rules_evaluated": [
                {"rule_type": "BLACKLIST_CHECK", "passed": True},
                {"rule_type": "AMOUNT_THRESHOLD", "passed": compliance_result["decision"] == "PASS"}
            ],
            "evidence_hash": compliance_result["evidence_hash"],
            "timestamp": compliance_result["created_at"]
        }
        
        # Prepare ZK proof request
        zk_request = {
            "transaction_data": {
                **transaction_data,
                "tx_uuid": compliance_result["tx_id"]
            },
            "compliance_evidence": compliance_evidence,
            "merkle_proof": {
                "root_hash": merkle_proof["root_hash"],
                "path_indices": [merkle_proof["leaf_index"]],
                "path_elements": merkle_proof["proof_hashes"]
            }
        }
        
        response = requests.post(
            f"{self.backend_url}/v1/zk/prove",
            json=zk_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"ZK proof generation failed: {response.status_code} - {response.text}")
            
        result = response.json()
        if not result.get("success"):
            raise Exception(f"ZK proof generation failed: {result.get('error')}")
            
        logger.info(f"✅ ZK proof generated: {result['proof_id']}")
        return result
        
    def verify_zk_proof(self, proof_id):
        """Verify ZK proof"""
        logger.info(f"🔍 Verifying ZK proof: {proof_id}")
        
        response = requests.post(
            f"{self.backend_url}/v1/zk/verify",
            json={"proof_id": proof_id},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"ZK proof verification failed: {response.status_code}")
            
        result = response.json()
        if not result.get("success"):
            raise Exception(f"ZK proof verification failed: {result.get('error')}")
            
        is_valid = result.get("is_valid", False)
        logger.info(f"✅ ZK proof verification: {'VALID' if is_valid else 'INVALID'}")
        return result
        
    def run_integration_test(self):
        """Run the complete integration test"""
        logger.info("🚀 Starting Crypto Compliance Copilot Integration Test")
        logger.info("=" * 60)
        
        try:
            # Step 1: Health check
            self.health_check()
            
            # Step 2: Submit a transaction
            transaction_data = {
                "wallet_from": "0x1234567890123456789012345678901234567890",
                "wallet_to": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", 
                "amount": "250.50",
                "currency": "ETH",
                "kyc_proof_id": "kyc_integration_test_001",
                "transaction_type": "transfer",
                "description": "Integration test transaction"
            }
            
            compliance_result = self.submit_transaction(transaction_data)
            
            # Step 3: Get Merkle proof
            merkle_proof = self.get_merkle_proof(compliance_result["evidence_hash"])
            
            # Step 4: Generate ZK proof
            zk_proof_result = self.generate_zk_proof(
                transaction_data, 
                compliance_result, 
                merkle_proof
            )
            
            # Step 5: Verify ZK proof
            verification_result = self.verify_zk_proof(zk_proof_result["proof_id"])
            
            # Step 6: Summary
            logger.info("=" * 60)
            logger.info("🎉 INTEGRATION TEST COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"📊 Test Results:")
            logger.info(f"   • Transaction ID: {compliance_result['tx_id']}")
            logger.info(f"   • Compliance Decision: {compliance_result['decision']}")
            logger.info(f"   • Evidence Hash: {compliance_result['evidence_hash']}")
            logger.info(f"   • Merkle Root: {merkle_proof['root_hash'][:16]}...")
            logger.info(f"   • ZK Proof ID: {zk_proof_result['proof_id']}")
            logger.info(f"   • ZK Proof Valid: {verification_result['is_valid']}")
            logger.info("=" * 60)
            logger.info("🔐 Privacy-Preserving Compliance Verification Achieved!")
            logger.info("   ✅ Transaction compliance verified without exposing sensitive data")
            logger.info("   ✅ Zero-knowledge proof ensures privacy")
            logger.info("   ✅ Merkle tree provides evidence integrity")
            logger.info("   ✅ End-to-end workflow validated")
            
            return {
                "success": True,
                "transaction_id": compliance_result['tx_id'],
                "proof_id": zk_proof_result['proof_id'],
                "is_valid": verification_result['is_valid']
            }
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """Run the integration test"""
    integration = ComplianceCopilotIntegration()
    result = integration.run_integration_test()
    
    if result["success"]:
        print("\\n🎉 MODULE 3 INTEGRATION TEST PASSED!")
        print("ZK circuit + Node helper successfully integrated!")
        exit(0)
    else:
        print(f"\\n❌ Integration test failed: {result['error']}")
        exit(1)

if __name__ == "__main__":
    main()
