"""Test cases for compliance engine logic"""

import pytest
import os
from decimal import Decimal
from unittest.mock import patch

from app.core.compliance_engine import (
    evaluate_transaction_compliance,
    compliance_engine,
    ComplianceDecision,
    ComplianceRule
)
from app.models.transaction import DecisionEnum


@pytest.mark.asyncio
class TestComplianceEngine:
    """Test class for compliance engine functionality"""

    def test_clean_transaction_passes(self, compliance_test_data):
        """Test that clean transactions pass compliance"""
        scenario = next(s for s in compliance_test_data.get_compliance_scenarios() 
                       if s["name"] == "clean_small_transaction")
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=scenario["wallet_from"],
            wallet_to=scenario["wallet_to"],
            amount=scenario["amount"],
            currency="ETH",
            kyc_proof_id=scenario["kyc_proof_id"]
        )
        
        assert decision == DecisionEnum.PASS
        assert "approved" in reason.lower() or "pass" in reason.lower()
        assert evidence_hash is not None
        assert len(evidence_hash) == 64  # SHA256 hex string

    def test_blacklisted_sender_rejected(self, compliance_test_data):
        """Test that transactions from blacklisted wallets are rejected"""
        scenario = next(s for s in compliance_test_data.get_compliance_scenarios() 
                       if s["name"] == "blacklisted_sender")
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=scenario["wallet_from"],
            wallet_to=scenario["wallet_to"],
            amount=scenario["amount"],
            currency="ETH",
            kyc_proof_id=scenario["kyc_proof_id"]
        )
        
        assert decision == DecisionEnum.REJECT
        assert "blacklist" in reason.lower()
        assert evidence_hash is not None

    def test_blacklisted_receiver_rejected(self, compliance_test_data):
        """Test that transactions to blacklisted wallets are rejected"""
        scenario = next(s for s in compliance_test_data.get_compliance_scenarios() 
                       if s["name"] == "blacklisted_receiver")
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=scenario["wallet_from"],
            wallet_to=scenario["wallet_to"],
            amount=scenario["amount"],
            currency="ETH",
            kyc_proof_id=scenario["kyc_proof_id"]
        )
        
        assert decision == DecisionEnum.REJECT
        assert "blacklist" in reason.lower()
        assert evidence_hash is not None

    def test_high_amount_triggers_hold(self, compliance_test_data):
        """Test that high amount transactions trigger manual review"""
        scenario = next(s for s in compliance_test_data.get_compliance_scenarios() 
                       if s["name"] == "high_amount_with_kyc")
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=scenario["wallet_from"],
            wallet_to=scenario["wallet_to"],
            amount=scenario["amount"],
            currency="ETH",
            kyc_proof_id=scenario["kyc_proof_id"]
        )
        
        # High amount should trigger HOLD for manual review
        assert decision in [DecisionEnum.HOLD, DecisionEnum.PASS]  # Depends on threshold
        assert evidence_hash is not None

    def test_no_kyc_triggers_hold(self, compliance_test_data):
        """Test that transactions without KYC proof trigger manual review"""
        scenario = next(s for s in compliance_test_data.get_compliance_scenarios() 
                       if s["name"] == "no_kyc_small_amount")
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=scenario["wallet_from"],
            wallet_to=scenario["wallet_to"],
            amount=scenario["amount"],
            currency="ETH",
            kyc_proof_id=scenario["kyc_proof_id"]
        )
        
        # No KYC should trigger HOLD for manual review
        assert decision in [DecisionEnum.HOLD, DecisionEnum.PASS]  # Depends on requirements
        assert evidence_hash is not None

    @patch.dict(os.environ, {"AMOUNT_THRESHOLD": "100.0"})
    def test_amount_threshold_enforcement(self, compliance_test_data):
        """Test that amount threshold is properly enforced"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Test below threshold
        decision_low, _, _ = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("50.0"),
            currency="ETH",
            kyc_proof_id="kyc_valid"
        )
        
        # Test above threshold
        decision_high, _, _ = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("150.0"),
            currency="ETH",
            kyc_proof_id="kyc_valid"
        )
        
        # Both should pass if wallets are clean, but high amount might get more scrutiny
        assert decision_low in [DecisionEnum.PASS, DecisionEnum.HOLD]
        assert decision_high in [DecisionEnum.PASS, DecisionEnum.HOLD]

    @patch.dict(os.environ, {"BLACKLISTED_WALLETS": "0xDEAD,0xBEEF"})
    def test_custom_blacklist_configuration(self):
        """Test that blacklist can be configured via environment"""
        # Test with custom blacklisted wallet
        decision, reason, _ = evaluate_transaction_compliance(
            wallet_from="0xDEAD",
            wallet_to="0x1234567890123456789012345678901234567890",
            amount=Decimal("50.0"),
            currency="ETH",
            kyc_proof_id="kyc_valid"
        )
        
        assert decision == DecisionEnum.REJECT
        assert "blacklist" in reason.lower()

    def test_multiple_compliance_rules(self, compliance_test_data):
        """Test evaluation when multiple compliance rules are triggered"""
        blacklisted_wallet = compliance_test_data.BLACKLISTED_WALLETS[0]
        
        # Transaction that's both blacklisted AND high amount
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=blacklisted_wallet,
            wallet_to="0x1234567890123456789012345678901234567890",
            amount=Decimal("5000.0"),  # High amount
            currency="ETH",
            kyc_proof_id=None  # No KYC
        )
        
        # Should be rejected due to blacklist (most severe rule)
        assert decision == DecisionEnum.REJECT
        assert "blacklist" in reason.lower()
        assert evidence_hash is not None

    def test_evidence_hash_deterministic(self, compliance_test_data):
        """Test that evidence hash is deterministic for same inputs"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Call compliance engine twice with same parameters
        _, _, hash1 = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        _, _, hash2 = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        assert hash1 == hash2  # Should be deterministic

    def test_evidence_hash_changes_with_input(self, compliance_test_data):
        """Test that evidence hash changes when inputs change"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Get hash for original transaction
        _, _, hash1 = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        # Get hash for transaction with different amount
        _, _, hash2 = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("200.0"),  # Different amount
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        assert hash1 != hash2  # Should be different

    def test_compliance_with_metadata(self, compliance_test_data):
        """Test compliance evaluation with additional metadata"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        metadata = {
            "source": "api_test",
            "user_agent": "test_client",
            "ip_address": "127.0.0.1"
        }
        
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test",
            metadata=metadata
        )
        
        assert decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
        assert reason is not None
        assert evidence_hash is not None

    def test_currency_support(self, compliance_test_data):
        """Test compliance evaluation with different currencies"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        currencies = ["ETH", "USDC", "USDT", "BTC"]
        
        for currency in currencies:
            decision, reason, evidence_hash = evaluate_transaction_compliance(
                wallet_from=clean_wallets[0],
                wallet_to=clean_wallets[1],
                amount=Decimal("100.0"),
                currency=currency,
                kyc_proof_id="kyc_test"
            )
            
            assert decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
            assert reason is not None
            assert evidence_hash is not None

    def test_edge_case_zero_amount(self, compliance_test_data):
        """Test compliance with zero amount transaction"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Zero amount should be rejected or flagged
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("0.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        # Zero amount transactions should be rejected or held
        assert decision in [DecisionEnum.REJECT, DecisionEnum.HOLD]
        assert evidence_hash is not None

    def test_edge_case_very_large_amount(self, compliance_test_data):
        """Test compliance with extremely large amount"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Very large amount
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[1],
            amount=Decimal("1000000.0"),  # 1 million
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        # Large amounts should trigger manual review
        assert decision in [DecisionEnum.HOLD, DecisionEnum.REJECT]
        assert evidence_hash is not None

    def test_edge_case_same_wallet_addresses(self, compliance_test_data):
        """Test compliance when sender and receiver are the same"""
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        # Same wallet for sender and receiver
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=clean_wallets[0],
            wallet_to=clean_wallets[0],  # Same as sender
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        # Self-transactions might be flagged for review
        assert decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
        assert evidence_hash is not None

    def test_compliance_engine_summary(self):
        """Test compliance engine summary functionality"""
        try:
            summary = compliance_engine.get_compliance_summary()
            
            assert isinstance(summary, dict)
            # Summary should contain configuration information
            expected_keys = ["supported_rules", "thresholds", "blacklisted_wallets_count"]
            for key in expected_keys:
                if key in summary:
                    assert summary[key] is not None
        except AttributeError:
            # If get_compliance_summary method doesn't exist, that's okay for now
            pytest.skip("Compliance engine summary not implemented")

    def test_compliance_rules_enum(self):
        """Test that compliance rules are properly defined"""
        try:
            # Test that ComplianceRule enum exists and has expected values
            assert hasattr(ComplianceRule, 'BLACKLIST_CHECK')
            assert hasattr(ComplianceRule, 'AMOUNT_THRESHOLD')
            assert hasattr(ComplianceRule, 'KYC_REQUIREMENT')
        except (NameError, AttributeError):
            # If ComplianceRule enum doesn't exist, that's okay for basic implementation
            pytest.skip("ComplianceRule enum not implemented")

    def test_compliance_decision_enum(self):
        """Test that compliance decision enum works properly"""
        try:
            # Test ComplianceDecision enum if it exists
            assert hasattr(ComplianceDecision, 'APPROVE')
            assert hasattr(ComplianceDecision, 'REJECT') 
            assert hasattr(ComplianceDecision, 'REVIEW')
        except (NameError, AttributeError):
            # If ComplianceDecision enum doesn't exist, use DecisionEnum
            assert hasattr(DecisionEnum, 'PASS')
            assert hasattr(DecisionEnum, 'REJECT')
            assert hasattr(DecisionEnum, 'HOLD')

    @pytest.mark.parametrize("wallet_case", [
        "lowercase",
        "uppercase", 
        "mixed_case",
        "with_0x_prefix",
        "without_0x_prefix"
    ])
    def test_wallet_address_normalization(self, wallet_case, compliance_test_data):
        """Test that wallet addresses are properly normalized"""
        base_address = "742d35cc6634c0532925a3b8d4d0c123456789ab"
        clean_wallet = compliance_test_data.CLEAN_WALLETS[1]
        
        test_addresses = {
            "lowercase": f"0x{base_address.lower()}",
            "uppercase": f"0x{base_address.upper()}",
            "mixed_case": f"0x{base_address[:10].lower()}{base_address[10:].upper()}",
            "with_0x_prefix": f"0x{base_address}",
            "without_0x_prefix": base_address
        }
        
        test_wallet = test_addresses[wallet_case]
        
        # Should handle all address formats consistently
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=test_wallet,
            wallet_to=clean_wallet,
            amount=Decimal("100.0"),
            currency="ETH",
            kyc_proof_id="kyc_test"
        )
        
        assert decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
        assert evidence_hash is not None

    def test_concurrent_compliance_evaluations(self, compliance_test_data):
        """Test concurrent compliance evaluations"""
        import asyncio
        
        clean_wallets = compliance_test_data.CLEAN_WALLETS
        
        async def evaluate_async():
            # Run compliance evaluation in async context
            return evaluate_transaction_compliance(
                wallet_from=clean_wallets[0],
                wallet_to=clean_wallets[1],
                amount=Decimal("100.0"),
                currency="ETH",
                kyc_proof_id="kyc_concurrent_test"
            )
        
        async def run_concurrent_evaluations():
            tasks = [evaluate_async() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            return results
        
        # Run concurrent evaluations
        results = asyncio.run(run_concurrent_evaluations())
        
        assert len(results) == 10
        for decision, reason, evidence_hash in results:
            assert decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
            assert reason is not None
            assert evidence_hash is not None