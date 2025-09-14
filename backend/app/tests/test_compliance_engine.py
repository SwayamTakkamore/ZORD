"""Test cases for compliance engine"""

import pytest
from decimal import Decimal

from app.core.compliance_engine import (
    ComplianceEngine, 
    ComplianceEvidence, 
    ComplianceRuleType,
    evaluate_transaction_compliance
)
from app.models.transaction import DecisionEnum


class TestComplianceEvidence:
    """Test ComplianceEvidence class"""
    
    def test_evidence_creation(self):
        """Test creating compliance evidence"""
        evidence = ComplianceEvidence()
        
        assert evidence.rules_applied == []
        assert evidence.risk_score == 0
        assert evidence.flags == []
        assert evidence.metadata == {}
    
    def test_add_rule_passed(self):
        """Test adding a passed rule"""
        evidence = ComplianceEvidence()
        evidence.add_rule(ComplianceRuleType.KYC_REQUIREMENT, True, "Valid KYC provided")
        
        assert len(evidence.rules_applied) == 1
        assert evidence.rules_applied[0]["rule"] == "KYC_REQUIREMENT"
        assert evidence.rules_applied[0]["passed"] == True
        assert evidence.risk_score == 0
        assert evidence.flags == []
    
    def test_add_rule_failed(self):
        """Test adding a failed rule"""
        evidence = ComplianceEvidence()
        evidence.add_rule(ComplianceRuleType.BLACKLIST_CHECK, False, "Wallet is blacklisted")
        
        assert len(evidence.rules_applied) == 1
        assert evidence.rules_applied[0]["passed"] == False
        assert evidence.risk_score == 100  # High risk for blacklist
        assert len(evidence.flags) == 1
        assert "BLACKLIST_CHECK" in evidence.flags[0]
    
    def test_evidence_hash_deterministic(self):
        """Test that evidence hash is deterministic"""
        evidence1 = ComplianceEvidence()
        evidence1.add_rule(ComplianceRuleType.KYC_REQUIREMENT, True, "Valid KYC")
        
        evidence2 = ComplianceEvidence()
        evidence2.add_rule(ComplianceRuleType.KYC_REQUIREMENT, True, "Valid KYC")
        
        hash1 = evidence1.compute_hash()
        hash2 = evidence2.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex string


class TestComplianceEngine:
    """Test ComplianceEngine class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.engine = ComplianceEngine()
    
    def test_engine_initialization(self):
        """Test compliance engine initialization"""
        assert len(self.engine.blacklisted_wallets) >= 3
        assert self.engine.amount_threshold == Decimal("1000.0")
        assert self.engine.kyc_required == True
        assert self.engine.max_risk_score == 100
    
    def test_blacklist_check_passed(self):
        """Test blacklist check with clean wallets"""
        passed, reason = self.engine._check_blacklist(
            "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "0x123d35Cc6634C0532925a3b8D4d0C123456789CD"
        )
        
        assert passed == True
        assert "No blacklisted" in reason
    
    def test_blacklist_check_failed_source(self):
        """Test blacklist check with blacklisted source"""
        passed, reason = self.engine._check_blacklist(
            "0x000000000000000000000000000000000000dead",
            "0x123d35Cc6634C0532925a3b8D4d0C123456789CD"
        )
        
        assert passed == False
        assert "Source wallet" in reason
        assert "blacklisted" in reason
    
    def test_blacklist_check_failed_destination(self):
        """Test blacklist check with blacklisted destination"""
        passed, reason = self.engine._check_blacklist(
            "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "0x000000000000000000000000000000000000dead"
        )
        
        assert passed == False
        assert "Destination wallet" in reason
        assert "blacklisted" in reason
    
    def test_amount_threshold_passed(self):
        """Test amount threshold check with low amount"""
        passed, reason = self.engine._check_amount_threshold(Decimal("500.0"), "ETH")
        
        assert passed == True
        assert "within acceptable threshold" in reason
    
    def test_amount_threshold_failed(self):
        """Test amount threshold check with high amount"""
        passed, reason = self.engine._check_amount_threshold(Decimal("1500.0"), "ETH")
        
        assert passed == False
        assert "exceeds threshold" in reason
    
    def test_kyc_requirement_passed(self):
        """Test KYC requirement with valid proof"""
        passed, reason = self.engine._check_kyc_requirement("kyc_12345")
        
        assert passed == True
        assert "Valid KYC proof provided" in reason
    
    def test_kyc_requirement_failed_missing(self):
        """Test KYC requirement with missing proof"""
        passed, reason = self.engine._check_kyc_requirement(None)
        
        assert passed == False
        assert "KYC proof required but not provided" in reason
    
    def test_kyc_requirement_failed_invalid(self):
        """Test KYC requirement with invalid proof"""
        passed, reason = self.engine._check_kyc_requirement("abc")
        
        assert passed == False
        assert "Invalid KYC proof format" in reason
    
    def test_evaluate_transaction_pass(self):
        """Test transaction evaluation that should pass"""
        decision, reason, evidence = self.engine.evaluate_transaction(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        assert decision == DecisionEnum.PASS
        assert "compliance checks passed" in reason
        assert evidence.risk_score < 50
    
    def test_evaluate_transaction_reject_blacklist(self):
        """Test transaction evaluation that should be rejected"""
        decision, reason, evidence = self.engine.evaluate_transaction(
            wallet_from="0x000000000000000000000000000000000000dead",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        assert decision == DecisionEnum.REJECT
        assert "blacklisted" in reason
        assert evidence.risk_score >= 100
    
    def test_evaluate_transaction_hold_amount(self):
        """Test transaction evaluation that should be held for high amount"""
        decision, reason, evidence = self.engine.evaluate_transaction(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("1500.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        assert decision == DecisionEnum.HOLD
        assert "risk score" in reason or "flagged" in reason
        assert evidence.risk_score >= 50
    
    def test_evaluate_transaction_hold_no_kyc(self):
        """Test transaction evaluation that should be held for missing KYC"""
        decision, reason, evidence = self.engine.evaluate_transaction(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id=None
        )
        
        assert decision == DecisionEnum.HOLD
        assert len(evidence.flags) > 0
    
    def test_blacklist_management(self):
        """Test adding and removing from blacklist"""
        test_wallet = "0xTEST123456789"
        
        # Add to blacklist
        added = self.engine.add_to_blacklist(test_wallet)
        assert added == True
        assert test_wallet.lower() in self.engine.blacklisted_wallets
        
        # Try to add again (should return False)
        added_again = self.engine.add_to_blacklist(test_wallet)
        assert added_again == False
        
        # Remove from blacklist
        removed = self.engine.remove_from_blacklist(test_wallet)
        assert removed == True
        assert test_wallet.lower() not in self.engine.blacklisted_wallets
        
        # Try to remove again (should return False)
        removed_again = self.engine.remove_from_blacklist(test_wallet)
        assert removed_again == False
    
    def test_compliance_summary(self):
        """Test getting compliance summary"""
        summary = self.engine.get_compliance_summary()
        
        assert "blacklisted_wallets_count" in summary
        assert "amount_threshold_usd" in summary
        assert "kyc_required" in summary
        assert "max_risk_score" in summary
        assert "supported_rules" in summary
        
        assert isinstance(summary["blacklisted_wallets_count"], int)
        assert isinstance(summary["supported_rules"], list)


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_evaluate_transaction_compliance(self):
        """Test the convenience function"""
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        assert isinstance(decision, DecisionEnum)
        assert isinstance(reason, str)
        assert isinstance(evidence_hash, str)
        assert len(evidence_hash) == 64  # SHA256 hex string
    
    def test_evaluate_transaction_compliance_deterministic(self):
        """Test that convenience function produces deterministic results"""
        # Same inputs should produce same results
        decision1, reason1, hash1 = evaluate_transaction_compliance(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        decision2, reason2, hash2 = evaluate_transaction_compliance(
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_12345"
        )
        
        assert decision1 == decision2
        assert reason1 == reason2
        assert hash1 == hash2
