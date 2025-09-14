"""
Enhanced compliance engine with deterministic rules and evidence tracking
"""

import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from enum import Enum

from app.models.transaction import DecisionEnum

logger = logging.getLogger(__name__)


class ComplianceRuleType(str, Enum):
    """Types of compliance rules"""
    BLACKLIST_CHECK = "BLACKLIST_CHECK"
    AMOUNT_THRESHOLD = "AMOUNT_THRESHOLD" 
    KYC_REQUIREMENT = "KYC_REQUIREMENT"
    VELOCITY_CHECK = "VELOCITY_CHECK"
    JURISDICTION_CHECK = "JURISDICTION_CHECK"


class ComplianceEvidence:
    """Evidence collected during compliance checking"""
    
    def __init__(self):
        self.rules_applied: List[str] = []
        self.risk_score: int = 0
        self.flags: List[str] = []
        self.metadata: Dict = {}
    
    def add_rule(self, rule_type: ComplianceRuleType, passed: bool, details: str):
        """Add evidence of a rule being applied"""
        self.rules_applied.append({
            "rule": rule_type.value,
            "passed": passed,
            "details": details,
            "timestamp": "2025-09-10T08:00:00Z"  # In real app, use actual timestamp
        })
        
        if not passed:
            self.risk_score += self._get_risk_weight(rule_type)
            self.flags.append(f"{rule_type.value}: {details}")
    
    def _get_risk_weight(self, rule_type: ComplianceRuleType) -> int:
        """Get risk weight for different rule types"""
        weights = {
            ComplianceRuleType.BLACKLIST_CHECK: 100,
            ComplianceRuleType.AMOUNT_THRESHOLD: 30,
            ComplianceRuleType.KYC_REQUIREMENT: 50,
            ComplianceRuleType.VELOCITY_CHECK: 20,
            ComplianceRuleType.JURISDICTION_CHECK: 40
        }
        return weights.get(rule_type, 10)
    
    def to_dict(self) -> Dict:
        """Convert evidence to dictionary for serialization"""
        return {
            "rules_applied": self.rules_applied,
            "risk_score": self.risk_score,
            "flags": self.flags,
            "metadata": self.metadata
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of evidence"""
        evidence_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(evidence_str.encode()).hexdigest()


class ComplianceEngine:
    """Enhanced compliance engine with configurable rules"""
    
    def __init__(self):
        # Configuration - in production, load from database/config
        self.blacklisted_wallets = {
            "0x000000000000000000000000000000000000dead",
            "0x1111111111111111111111111111111111111111",
            "0x0000000000000000000000000000000000000000"
        }
        self.amount_threshold = Decimal("1000.0")
        self.kyc_required = True
        self.max_risk_score = 100
        
        logger.info(f"Compliance engine initialized with {len(self.blacklisted_wallets)} blacklisted addresses")
    
    def evaluate_transaction(
        self,
        wallet_from: str,
        wallet_to: str,
        amount: Decimal,
        currency: str,
        kyc_proof_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[DecisionEnum, str, ComplianceEvidence]:
        """
        Evaluate a transaction against all compliance rules
        
        Args:
            wallet_from: Source wallet address
            wallet_to: Destination wallet address
            amount: Transaction amount
            currency: Currency code
            kyc_proof_id: KYC proof identifier
            metadata: Additional transaction metadata
            
        Returns:
            Tuple of (decision, reason, evidence)
        """
        evidence = ComplianceEvidence()
        evidence.metadata = metadata or {}
        
        logger.info(f"Evaluating transaction: {wallet_from} -> {wallet_to}, amount: {amount} {currency}")
        
        # Rule 1: Blacklist Check (highest priority)
        blacklist_passed, blacklist_reason = self._check_blacklist(wallet_from, wallet_to)
        evidence.add_rule(ComplianceRuleType.BLACKLIST_CHECK, blacklist_passed, blacklist_reason)
        
        if not blacklist_passed:
            decision = DecisionEnum.REJECT
            reason = f"REJECT: {blacklist_reason}"
            logger.warning(f"Transaction rejected: {reason}")
            return decision, reason, evidence
        
        # Rule 2: Amount Threshold Check
        amount_passed, amount_reason = self._check_amount_threshold(amount, currency)
        evidence.add_rule(ComplianceRuleType.AMOUNT_THRESHOLD, amount_passed, amount_reason)
        
        # Rule 3: KYC Requirement Check
        kyc_passed, kyc_reason = self._check_kyc_requirement(kyc_proof_id)
        evidence.add_rule(ComplianceRuleType.KYC_REQUIREMENT, kyc_passed, kyc_reason)
        
        # Rule 4: Velocity Check (placeholder for future enhancement)
        velocity_passed, velocity_reason = self._check_velocity(wallet_from, amount)
        evidence.add_rule(ComplianceRuleType.VELOCITY_CHECK, velocity_passed, velocity_reason)
        
        # Decision logic based on accumulated evidence
        decision, reason = self._make_decision(evidence)
        
        logger.info(f"Transaction decision: {decision.value}, risk_score: {evidence.risk_score}")
        return decision, reason, evidence
    
    def _check_blacklist(self, wallet_from: str, wallet_to: str) -> Tuple[bool, str]:
        """Check if wallets are blacklisted"""
        wallet_from_lower = wallet_from.lower()
        wallet_to_lower = wallet_to.lower()
        
        if wallet_from_lower in self.blacklisted_wallets:
            return False, f"Source wallet {wallet_from} is blacklisted"
        
        if wallet_to_lower in self.blacklisted_wallets:
            return False, f"Destination wallet {wallet_to} is blacklisted"
        
        return True, "No blacklisted wallets detected"
    
    def _check_amount_threshold(self, amount: Decimal, currency: str) -> Tuple[bool, str]:
        """Check if amount exceeds threshold"""
        # Convert to USD equivalent (simplified - in production, use real exchange rates)
        usd_amount = amount  # Assuming 1:1 for demo
        
        if usd_amount > self.amount_threshold:
            return False, f"Amount {usd_amount} {currency} exceeds threshold {self.amount_threshold} USD"
        
        return True, f"Amount {usd_amount} {currency} within acceptable threshold"
    
    def _check_kyc_requirement(self, kyc_proof_id: Optional[str]) -> Tuple[bool, str]:
        """Check KYC requirements"""
        if self.kyc_required and not kyc_proof_id:
            return False, "KYC proof required but not provided"
        
        if kyc_proof_id:
            # In production, verify KYC proof validity
            if len(kyc_proof_id) < 5:
                return False, f"Invalid KYC proof format: {kyc_proof_id}"
            
            return True, f"Valid KYC proof provided: {kyc_proof_id}"
        
        return True, "KYC not required for this transaction"
    
    def _check_velocity(self, wallet_from: str, amount: Decimal) -> Tuple[bool, str]:
        """Check transaction velocity (placeholder for future implementation)"""
        # In production, check transaction frequency and amounts over time
        # For now, simple rule: flag if amount > 500
        if amount > 500:
            return False, f"High velocity detected: amount {amount} exceeds velocity threshold"
        
        return True, f"Transaction velocity within normal limits"
    
    def _make_decision(self, evidence: ComplianceEvidence) -> Tuple[DecisionEnum, str]:
        """Make final decision based on collected evidence"""
        
        # Check for any critical failures (should already be handled)
        critical_rules = [ComplianceRuleType.BLACKLIST_CHECK]
        for rule_evidence in evidence.rules_applied:
            if rule_evidence["rule"] in [r.value for r in critical_rules] and not rule_evidence["passed"]:
                return DecisionEnum.REJECT, f"Critical rule failure: {rule_evidence['details']}"
        
        # Risk-based decision making
        if evidence.risk_score >= self.max_risk_score:
            return DecisionEnum.REJECT, f"Risk score {evidence.risk_score} exceeds maximum threshold"
        elif evidence.risk_score >= 50:
            return DecisionEnum.HOLD, f"Elevated risk score {evidence.risk_score} requires manual review"
        elif len(evidence.flags) > 0:
            return DecisionEnum.HOLD, f"Transaction flagged for review: {'; '.join(evidence.flags)}"
        else:
            return DecisionEnum.PASS, "All compliance checks passed"
    
    def add_to_blacklist(self, wallet_address: str) -> bool:
        """Add wallet to blacklist"""
        wallet_lower = wallet_address.lower()
        if wallet_lower not in self.blacklisted_wallets:
            self.blacklisted_wallets.add(wallet_lower)
            logger.info(f"Added {wallet_address} to blacklist")
            return True
        return False
    
    def remove_from_blacklist(self, wallet_address: str) -> bool:
        """Remove wallet from blacklist"""
        wallet_lower = wallet_address.lower()
        if wallet_lower in self.blacklisted_wallets:
            self.blacklisted_wallets.remove(wallet_lower)
            logger.info(f"Removed {wallet_address} from blacklist")
            return True
        return False
    
    def get_compliance_summary(self) -> Dict:
        """Get compliance engine configuration summary"""
        return {
            "blacklisted_wallets_count": len(self.blacklisted_wallets),
            "amount_threshold_usd": str(self.amount_threshold),
            "kyc_required": self.kyc_required,
            "max_risk_score": self.max_risk_score,
            "supported_rules": [rule.value for rule in ComplianceRuleType]
        }


# Singleton instance for use across the application
compliance_engine = ComplianceEngine()


def evaluate_transaction_compliance(
    wallet_from: str,
    wallet_to: str, 
    amount: Decimal,
    currency: str,
    kyc_proof_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Tuple[DecisionEnum, str, str]:
    """
    Convenience function to evaluate transaction compliance
    
    Returns:
        Tuple of (decision, reason, evidence_hash)
    """
    decision, reason, evidence = compliance_engine.evaluate_transaction(
        wallet_from=wallet_from,
        wallet_to=wallet_to,
        amount=amount,
        currency=currency,
        kyc_proof_id=kyc_proof_id,
        metadata=metadata
    )
    
    evidence_hash = evidence.compute_hash()
    return decision, reason, evidence_hash
