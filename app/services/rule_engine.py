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
        Load business rules configuration for different facility types
        Documents are categorized into: general, facility_specific, and collateral
        """
        return {
            "Murabaha": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Master Murabaha Agreement",
                    "Murabaha Purchase Order",
                    "Agency Agreement",
                    "Asset Purchase Agreement",
                    "Murabaha Sale Agreement",
                    "Murabaha Repayment Schedule"
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement",
                    "Pledge Agreement"
                ],
                "min_amount": 0,
                "max_tenor_months": 60
            },
            "Musharaka": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Master Musharaka Agreement",
                    "Musharaka Capital Contribution Agreement",
                    "Profit and Loss Sharing Agreement",
                    "Musharaka Repayment Schedule"
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement",
                    "Pledge Agreement"
                ],
                "min_amount": 0,
                "max_tenor_months": 120
            },
            "Ijarah": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Master Ijarah Agreement",
                    "Asset Lease Agreement",
                    "Asset Schedule",
                    "Ijarah Rental Schedule"
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Security Deposit Agreement"
                ],
                "min_amount": 0,
                "max_tenor_months": 84
            },
            "Diminishing Musharaka": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Master Diminishing Musharaka Agreement",
                    "Purchase Undertaking",
                    "Sale Undertaking",
                    "Unit Redemption Schedule"
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation Agreement"
                ],
                "min_amount": 0,
                "max_tenor_months": 240
            },
            "LC": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Letter of Credit Application",
                    "LC Master Agreement",
                    "Trust Receipt Agreement"
                ],
                "collateral_documents": [
                    "Mortgage Deed Draft",
                    "Memorandum of Title Deposits",
                    "Hypothecation of Goods"
                ],
                "min_amount": 0,
                "max_tenor_months": 12
            },
            "Bank Guarantee": {
                "general_documents": [
                    "Offer Letter",
                    "Demand Promissory Note"
                ],
                "facility_specific_documents": [
                    "Bank Guarantee Application",
                    "Counter Guarantee Agreement",
                    "Indemnity Agreement"
                ],
                "collateral_documents": [
                    "Cash Margin Agreement",
                    "Lien on Fixed Deposits",
                    "Counter Guarantee"
                ],
                "min_amount": 0,
                "max_tenor_months": 36
            }
        }
    
    def _has_collateral(self, facility: FacilityData) -> bool:
        """
        Check if a facility has collateral/security
        
        Args:
            facility: Facility data to check
            
        Returns:
            True if collateral is present and not empty
        """
        if not facility.security:
            return False
        
        # Check if security is meaningful (not just "Not Specified", "None", etc.)
        security_str = str(facility.security).lower().strip()
        empty_markers = ["not specified", "none", "n/a", "na", "nil", ""]
        
        return security_str not in empty_markers
    
    def determine_required_documents(self, sanction_data: SanctionData) -> Dict[str, List[str]]:
        """
        Determine which documents need to be generated based on all facilities
        
        Args:
            sanction_data: Extracted sanction data with multiple facilities
            
        Returns:
            Dictionary with categorized document lists:
            {
                "compulsory": [...],
                "general": [...],
                "facility_specific": [...],
                "collateral": [...]
            }
        """
        # Compulsory documents for all sanction letters
        compulsory_docs = [
            "Sanction Letter",
            "Terms and Conditions Sheet"
        ]
        
        # Collect all document types
        general_docs: Set[str] = set()
        facility_specific_docs: Set[str] = set()
        collateral_docs: Set[str] = set()
        needs_collateral = False
        
        # Process each facility
        for facility in sanction_data.facilities:
            facility_type = self._normalize_facility_type(facility.facility_type)
            
            if facility_type in self.rules:
                rules = self.rules[facility_type]
                
                # Add general documents for this facility type
                general_docs.update(rules.get("general_documents", []))
                
                # Add facility-specific documents
                facility_specific_docs.update(rules.get("facility_specific_documents", []))
                
                # Check if this facility has collateral
                if self._has_collateral(facility):
                    needs_collateral = True
                    collateral_docs.update(rules.get("collateral_documents", []))
            else:
                # Unknown facility type - add default documents
                general_docs.update(["Offer Letter", "Demand Promissory Note"])
        
        # Build final document structure
        required_documents = {
            "compulsory": compulsory_docs,
            "general": sorted(list(general_docs)),
            "facility_specific": sorted(list(facility_specific_docs)),
            "collateral": sorted(list(collateral_docs)) if needs_collateral else []
        }
        
        return required_documents
    
    def _normalize_facility_type(self, facility_type: str) -> str:
        """
        Normalize facility type names to match rule keys
        
        Args:
            facility_type: Raw facility type from extraction
            
        Returns:
            Normalized facility type
        """
        facility_type = facility_type.strip().lower()
        
        # Mapping for variations
        mappings = {
            "murabaha": "Murabaha",
            "murabha": "Murabaha",
            "musharaka": "Musharaka",
            "musharakah": "Musharaka",
            "diminishing musharaka": "Diminishing Musharaka",
            "ijarah": "Ijarah",
            "ijara": "Ijarah",
            "lc": "LC",
            "letter of credit": "LC",
            "bg": "Bank Guarantee",
            "bank guarantee": "Bank Guarantee",
            "guarantee": "Bank Guarantee"
        }
        
        return mappings.get(facility_type, facility_type.title())
    
    def get_document_summary(self, sanction_data: SanctionData) -> Dict:
        """
        Get a complete summary of documents to be generated
        
        Args:
            sanction_data: Sanction data
            
        Returns:
            Dictionary with document summary and counts
        """
        required_docs = self.determine_required_documents(sanction_data)
        
        # Calculate totals
        total_count = (
            len(required_docs["compulsory"]) +
            len(required_docs["general"]) +
            len(required_docs["facility_specific"]) +
            len(required_docs["collateral"])
        )
        
        return {
            "customer_name": sanction_data.customer_name,
            "facility_count": len(sanction_data.facilities),
            "facilities": [f.facility_type for f in sanction_data.facilities],
            "documents": required_docs,
            "total_document_count": total_count,
            "has_collateral": len(required_docs["collateral"]) > 0
        }
    
    def validate_sanction_data(self, sanction_data: SanctionData) -> Dict[str, any]:
        """
        Validate sanction data against business rules for all facilities
        
        Args:
            sanction_data: Sanction data to validate
            
        Returns:
            Dictionary with validation results including per-facility validation
        """
        if not sanction_data.facilities or len(sanction_data.facilities) == 0:
            return {
                "valid": False,
                "reason": "No facilities found in sanction data",
                "facility_validations": []
            }
        
        facility_validations = []
        all_valid = True
        
        # Validate each facility
        for i, facility in enumerate(sanction_data.facilities, 1):
            facility_type = self._normalize_facility_type(facility.facility_type)
            
            validation_result = {
                "facility_number": i,
                "facility_type": facility_type,
                "valid": True,
                "issues": []
            }
            
            if facility_type not in self.rules:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Unknown facility type: {facility_type}")
                all_valid = False
            else:
                rules = self.rules[facility_type]
                
                # Validate tenor if specified
                if facility.tenor and "month" in facility.tenor.lower():
                    try:
                        tenor_months = int(''.join(filter(str.isdigit, facility.tenor)))
                        max_tenor = rules.get("max_tenor_months", 999)
                        
                        if tenor_months > max_tenor:
                            validation_result["valid"] = False
                            validation_result["issues"].append(
                                f"Tenor ({tenor_months} months) exceeds maximum allowed ({max_tenor} months)"
                            )
                            all_valid = False
                    except ValueError:
                        validation_result["issues"].append("Could not parse tenor value")
                
                # Check if collateral is required but missing
                if rules.get("requires_collateral", False) and not self._has_collateral(facility):
                    validation_result["issues"].append("Collateral is required but not specified")
            
            facility_validations.append(validation_result)
        
        return {
            "valid": all_valid,
            "facility_validations": facility_validations,
            "total_facilities": len(sanction_data.facilities)
        }
    
    def validate_facility(self, facility: FacilityData) -> Dict[str, any]:
        """
        Validate a single facility against business rules
        
        Args:
            facility: Facility data to validate
            
        Returns:
            Dictionary with validation results
        """
        facility_type = self._normalize_facility_type(facility.facility_type)
        
        if facility_type not in self.rules:
            return {
                "valid": False,
                "reason": f"Unknown facility type: {facility_type}"
            }
        
        rules = self.rules[facility_type]
        issues = []
        
        # Validate tenor
        if facility.tenor and "month" in facility.tenor.lower():
            try:
                tenor_months = int(''.join(filter(str.isdigit, facility.tenor)))
                max_tenor = rules.get("max_tenor_months", 999)
                
                if tenor_months > max_tenor:
                    issues.append(f"Tenor exceeds maximum of {max_tenor} months")
            except ValueError:
                issues.append("Invalid tenor format")
        
        if issues:
            return {"valid": False, "issues": issues}
        
        return {"valid": True}
