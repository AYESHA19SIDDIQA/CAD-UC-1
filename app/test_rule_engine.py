"""
Test script to demonstrate the rule-based document selection system
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.sanction_schema import SanctionData, FacilityData
from app.services.rule_engine import RuleEngine


def test_multi_facility_documents():
    """Test document generation rules for multiple facilities"""
    
    print("="*80)
    print("RULE-BASED DOCUMENT GENERATION TEST")
    print("="*80)
    
    # Create sample sanction data with multiple facilities
    sanction_data = SanctionData(
        customer_name="ABC Corporation",
        sanction_date="2026-03-07",
        facilities=[
            FacilityData(
                facility_type="Murabaha",
                facility_amount="PKR 50.00 millions",
                currency="PKR",
                tenor="36 months",
                profit_rate="KIBOR + 3%",
                purpose="Working Capital",
                security="Hypothecation of stock and receivables"
            ),
            FacilityData(
                facility_type="LC",
                facility_amount="PKR 30.00 millions",
                currency="PKR",
                tenor="At Sight",
                profit_rate="4% per annum",
                purpose="Import of raw materials",
                security="Lien on imported goods"
            )
        ],
        terms_conditions=[
            "Quarterly financial statements required",
            "Insurance of collateral mandatory",
            "Annual business plan submission"
        ]
    )
    
    # Initialize rule engine
    rule_engine = RuleEngine()
    
    # Get document requirements
    print(f"\nCustomer: {sanction_data.customer_name}")
    print(f"Number of Facilities: {len(sanction_data.facilities)}")
    print("\nFacilities:")
    for i, facility in enumerate(sanction_data.facilities, 1):
        print(f"  {i}. {facility.facility_type} - {facility.facility_amount}")
    
    print("\n" + "-"*80)
    print("REQUIRED DOCUMENTS (by Category)")
    print("-"*80)
    
    required_docs = rule_engine.determine_required_documents(sanction_data)
    
    # Display compulsory documents
    print("\n📋 COMPULSORY DOCUMENTS (for all sanctions):")
    for i, doc in enumerate(required_docs["compulsory"], 1):
        print(f"  {i}. {doc}")
    
    # Display general documents
    print("\n📄 GENERAL DOCUMENTS:")
    for i, doc in enumerate(required_docs["general"], 1):
        print(f"  {i}. {doc}")
    
    # Display facility-specific documents
    print("\n🏦 FACILITY-SPECIFIC DOCUMENTS:")
    for i, doc in enumerate(required_docs["facility_specific"], 1):
        print(f"  {i}. {doc}")
    
    # Display collateral documents
    if required_docs["collateral"]:
        print("\n🔒 COLLATERAL DOCUMENTS:")
        for i, doc in enumerate(required_docs["collateral"], 1):
            print(f"  {i}. {doc}")
    else:
        print("\n🔒 COLLATERAL DOCUMENTS: None required")
    
    # Get document summary
    print("\n" + "-"*80)
    print("DOCUMENT GENERATION SUMMARY")
    print("-"*80)
    
    summary = rule_engine.get_document_summary(sanction_data)
    print(f"\nCustomer: {summary['customer_name']}")
    print(f"Total Facilities: {summary['facility_count']}")
    print(f"Facilities: {', '.join(summary['facilities'])}")
    print(f"Total Documents to Generate: {summary['total_document_count']}")
    print(f"Has Collateral: {'Yes' if summary['has_collateral'] else 'No'}")
    
    # Validate sanction data
    print("\n" + "-"*80)
    print("VALIDATION RESULTS")
    print("-"*80)
    
    validation = rule_engine.validate_sanction_data(sanction_data)
    print(f"\nOverall Valid: {'✓ Yes' if validation['valid'] else '✗ No'}")
    print(f"Total Facilities Validated: {validation['total_facilities']}")
    
    print("\nPer-Facility Validation:")
    for fv in validation['facility_validations']:
        status = "✓ PASS" if fv['valid'] else "✗ FAIL"
        print(f"\n  Facility {fv['facility_number']}: {fv['facility_type']} - {status}")
        if fv['issues']:
            for issue in fv['issues']:
                print(f"    - Issue: {issue}")
    
    # Save summary as JSON
    output_dir = Path(__file__).parent.parent / "extracted_json"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "document_requirements_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n💾 Summary saved to: {output_file}")
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


def test_single_facility_without_collateral():
    """Test with a single facility without collateral"""
    
    print("\n\n" + "="*80)
    print("TEST: Single Facility Without Collateral")
    print("="*80)
    
    sanction_data = SanctionData(
        customer_name="XYZ Limited",
        sanction_date="2026-03-07",
        facilities=[
            FacilityData(
                facility_type="Musharaka",
                facility_amount="PKR 100.00 millions",
                currency="PKR",
                tenor="60 months",
                profit_rate="KIBOR + 2.5%",
                purpose="Business Expansion",
                security="Not Specified"  # No collateral
            )
        ],
        terms_conditions=["Annual audit required"]
    )
    
    rule_engine = RuleEngine()
    required_docs = rule_engine.determine_required_documents(sanction_data)
    
    print(f"\nCustomer: {sanction_data.customer_name}")
    print(f"Facility: {sanction_data.facilities[0].facility_type}")
    print(f"Security: {sanction_data.facilities[0].security}")
    
    print("\nRequired Documents:")
    print(f"  Compulsory: {len(required_docs['compulsory'])} documents")
    print(f"  General: {len(required_docs['general'])} documents")
    print(f"  Facility-Specific: {len(required_docs['facility_specific'])} documents")
    print(f"  Collateral: {len(required_docs['collateral'])} documents")
    
    if not required_docs['collateral']:
        print("\n✓ No collateral documents required (no security specified)")


if __name__ == "__main__":
    test_multi_facility_documents()
    test_single_facility_without_collateral()
