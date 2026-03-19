"""
Business rules engine for document generation
"""
from typing import Dict, List, Set
from app.schemas.sanction_schema import SanctionData, FacilityData


class RuleEngine:
    """Apply business rules to determine document requirements"""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """
        Load business rules configuration for different facility types.

        Keys are the canonical facility names used throughout the engine.
        Each entry lists which documents to generate and optional constraints.
        """
        return {
            "Murabaha": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Master Murabaha Agreement",
                    "Murabaha Purchase Order",
                    "Agency Agreement",
                    "Asset Purchase Agreement",
                    "Murabaha Sale Agreement",
                    "Murabaha Repayment Schedule",
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement",
                    "Pledge Agreement",
                ],
                "max_tenor_months": 60,
            },
            "Musharaka": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Master Musharaka Agreement",
                    "Musharaka Capital Contribution Agreement",
                    "Profit and Loss Sharing Agreement",
                    "Musharaka Repayment Schedule",
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement",
                    "Pledge Agreement",
                ],
                "max_tenor_months": 120,
            },
            "Ijarah": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Master Ijarah Agreement",
                    "Asset Lease Agreement",
                    "Asset Schedule",
                    "Ijarah Rental Schedule",
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Security Deposit Agreement",
                ],
                "max_tenor_months": 84,
            },
            "Diminishing Musharaka": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Master Diminishing Musharaka Agreement",
                    "Purchase Undertaking",
                    "Sale Undertaking",
                    "Unit Redemption Schedule",
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement",
                ],
                "max_tenor_months": 240,
            },
            "LC": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Letter of Credit Application",
                    "LC Master Agreement",
                    "Trust Receipt Agreement",
                    "MSFA Agreement",
                ],
                "collateral_documents": [
                    "Letter of Lien and Set-off",
                    "Lien over Import Documents",
                    "Personal Guarantee",
                    "Cash Margin Agreement",
                ],
                "max_tenor_months": 12,
            },
            "Bank Guarantee": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note",
                ],
                "facility_specific_documents": [
                    "Bank Guarantee Application",
                    "Counter Guarantee Agreement",
                    "Indemnity Agreement",
                ],
                "collateral_documents": [
                    "Cash Margin Agreement",
                    "Lien on Fixed Deposits",
                    "Counter Guarantee",
                ],
                "max_tenor_months": 36,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_facility_type(self, raw: str) -> str:
        """
        Map any raw facility-type string (as it comes out of the LLM) to one
        of the canonical rule-dict keys.

        Strategy:
          1. Exact-match lookups (lower-cased, stripped).
          2. Prefix / substring matches so that strings like
             "LC Sight (Foreign) under MSFA" still resolve to "LC".
        """
        if not raw:
            return "Unknown"

        cleaned = raw.strip().lower()

        # --- exact / common aliases ---
        exact_map = {
            "murabaha": "Murabaha",
            "murabha": "Murabaha",
            "musharaka": "Musharaka",
            "musharakah": "Musharaka",
            "diminishing musharaka": "Diminishing Musharaka",
            "diminishing musharakah": "Diminishing Musharaka",
            "ijarah": "Ijarah",
            "ijara": "Ijarah",
            "lc": "LC",
            "letter of credit": "LC",
            "lc sight": "LC",
            "lc usance": "LC",
            "bg": "Bank Guarantee",
            "bank guarantee": "Bank Guarantee",
            "guarantee": "Bank Guarantee",
        }
        if cleaned in exact_map:
            return exact_map[cleaned]

        # --- prefix / substring matching for longer descriptions ---
        # These cover strings like "LC Sight (Foreign) under MSFA",
        # "LC Usance (Foreign) without MSFA – Sub Limit of Facility 1", etc.
        substring_map = [
            # Order matters: more-specific patterns first
            ("diminishing musharaka", "Diminishing Musharaka"),
            ("diminishing musharakah", "Diminishing Musharaka"),
            ("murabaha", "Murabaha"),
            ("musharaka", "Musharaka"),
            ("musharakah", "Musharaka"),
            ("ijarah", "Ijarah"),
            ("ijara", "Ijarah"),
            ("bank guarantee", "Bank Guarantee"),
            # LC must come after longer patterns that might also contain "lc"
            ("letter of credit", "LC"),
            ("lc sight", "LC"),
            ("lc usance", "LC"),
            ("lc ", "LC"),          # "LC " with trailing space catches "LC Sight…"
        ]
        for pattern, canonical in substring_map:
            if pattern in cleaned:
                return canonical

        # Fallback: return title-cased original so at least it's readable
        return raw.strip().title()

    def _has_collateral(self, facility: FacilityData) -> bool:
        """Return True if the facility has meaningful collateral/security text."""
        security = facility.security
        if not security:
            return False
        text = str(security).lower().strip()
        empty_markers = {"not specified", "none", "n/a", "na", "nil", ""}
        return text not in empty_markers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def determine_required_documents(self, sanction_data: SanctionData) -> Dict[str, List[str]]:
        """
        Walk all facilities and collect the union of required documents,
        grouped by category.

        Returns:
            {
                "compulsory":        [...],   # always generated
                "general":           [...],   # offer letter, DPN etc.
                "facility_specific": [...],   # per facility-type docs
                "collateral":        [...],   # only when security is present
            }
        """
        compulsory = [
            "Sanction Letter",
            "Terms and Conditions Sheet",
        ]

        general_docs: Set[str] = set()
        facility_specific_docs: Set[str] = set()
        collateral_docs: Set[str] = set()
        needs_collateral = False

        for facility in sanction_data.facilities:
            canonical = self._normalize_facility_type(facility.facility_type)

            if canonical in self.rules:
                rules = self.rules[canonical]
                general_docs.update(rules.get("general_documents", []))
                facility_specific_docs.update(rules.get("facility_specific_documents", []))

                if self._has_collateral(facility):
                    needs_collateral = True
                    collateral_docs.update(rules.get("collateral_documents", []))
            else:
                # Unknown type — add safe defaults and warn
                print(f"[RuleEngine] WARNING: unrecognised facility type '{facility.facility_type}' "
                      f"(normalised to '{canonical}'). Using default documents.")
                general_docs.update(["Offer Letter", "Demand Promissory Note"])

        return {
            "compulsory": compulsory,
            "general": sorted(general_docs),
            "facility_specific": sorted(facility_specific_docs),
            "collateral": sorted(collateral_docs) if needs_collateral else [],
        }

    def get_document_summary(self, sanction_data: SanctionData) -> Dict:
        """Return a serialisable summary including doc counts."""
        required_docs = self.determine_required_documents(sanction_data)
        total = sum(len(v) for v in required_docs.values())

        return {
            "customer_name": sanction_data.customer_name,
            "facility_count": len(sanction_data.facilities),
            "facilities": [f.facility_type for f in sanction_data.facilities],
            "documents": required_docs,
            "total_document_count": total,
            "has_collateral": len(required_docs["collateral"]) > 0,
        }

    def validate_sanction_data(self, sanction_data: SanctionData) -> Dict:
        """
        Validate every facility against business rules.

        Returns a dict with overall 'valid' flag plus per-facility detail.
        """
        if not sanction_data.facilities:
            return {
                "valid": False,
                "reason": "No facilities found in sanction data",
                "facility_validations": [],
                "total_facilities": 0,
            }

        facility_validations = []
        all_valid = True

        for i, facility in enumerate(sanction_data.facilities, 1):
            canonical = self._normalize_facility_type(facility.facility_type)
            result = {
                "facility_number": i,
                "facility_type": canonical,
                "raw_facility_type": facility.facility_type,
                "valid": True,
                "issues": [],
            }

            if canonical not in self.rules:
                result["valid"] = False
                result["issues"].append(f"Unrecognised facility type: '{canonical}'")
                all_valid = False
            else:
                rules = self.rules[canonical]
                # Validate tenor only when it looks like "N months"
                tenor = facility.tenor or ""
                if "month" in tenor.lower():
                    digits = "".join(c for c in tenor if c.isdigit())
                    if digits:
                        tenor_months = int(digits)
                        max_tenor = rules.get("max_tenor_months", 9999)
                        if tenor_months > max_tenor:
                            result["valid"] = False
                            result["issues"].append(
                                f"Tenor {tenor_months}m exceeds max allowed {max_tenor}m"
                            )
                            all_valid = False

            facility_validations.append(result)

        return {
            "valid": all_valid,
            "facility_validations": facility_validations,
            "total_facilities": len(sanction_data.facilities),
        }