"""
Test script to demonstrate the rule-based document selection system.

Run from the project root:
    python -m app.test_rule_engine
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.sanction_schema import SanctionData, FacilityData
from app.services.rule_engine import RuleEngine


def test_lc_facilities():
    """
    Reproduce the real-world case from the Global Technologies sanction:
    LC Sight + LC Usance (sub-limit).
    """
    print("=" * 80)
    print("TEST: LC Sight + LC Usance (real-world sanction data)")
    print("=" * 80)

    sanction_data = SanctionData(
        approval_no="CBD/level#03/2018/0090/18/12/2018",
        proposal_type="Renewal",
        approval_level="Level3",
        sanction_date="December 18, 2018",
        customer_name="M/s Global Technologies & Services",
        customer_location="6-L Block-6, P.E.C.H.S Sharh-e-Faisal Karachi",
        business_segment="ME",
        icrr="3 - Good",
        originating_unit_region="Shahrah e Faisal Karachi",
        facilities=[
            FacilityData(
                s_no=1,
                nature_of_limit="LC Sight (Foreign) under MSFA",
                # NOTE: facility_type is the SHORT canonical name.
                # The rule engine's _normalize_facility_type also handles
                # the full nature_of_limit string, so either works.
                facility_type="LC",
                existing_limit="50.00",
                approved_limit="50.00",
                increase_decrease="-",
                currency="PKR",
                profit_rate="85% Commission on opening, 75% Commission on retirement, PAD: K+3%",
                tenor="At Sight",
                expiry_review="Review",
                security=(
                    "100% cash backed - Cash margin / Lien over MBL Deposit. "
                    "Letter of Lien & Set-off. Lien over Import Documents. "
                    "PG of Directors."
                ),
                is_sub_limit=False,
            ),
            FacilityData(
                s_no=2,
                nature_of_limit="LC Usance (Foreign) without MSFA – Sub Limit of Facility 1",
                facility_type="LC",
                existing_limit="",
                approved_limit="50.00",
                increase_decrease="(50.00)",
                currency="PKR",
                profit_rate="85% Commission on opening, 75% Commission on retirement, APSOC",
                tenor="Max 120 Days",
                expiry_review="Fresh",
                security=(
                    "100% cash backed - Cash margin / Lien over MBL Deposit. "
                    "Letter of Lien & Set-off. Lien over Import Documents. "
                    "PG of Directors."
                ),
                is_sub_limit=True,
                parent_facility_s_no=1,
            ),
        ],
        terms_conditions=[
            "Quarterly financial statements required",
            "Insurance of collateral mandatory",
        ],
    )

    _run_test(sanction_data)


def test_murabaha_musharaka():
    """Test multi-facility with Murabaha + LC."""
    print("\n" + "=" * 80)
    print("TEST: Murabaha + LC (mixed facility types)")
    print("=" * 80)

    sanction_data = SanctionData(
        customer_name="ABC Corporation",
        sanction_date="2026-03-07",
        facilities=[
            FacilityData(
                s_no=1,
                nature_of_limit="Murabaha Working Capital",
                facility_type="Murabaha",
                approved_limit="50.00",
                currency="PKR",
                profit_rate="KIBOR + 3%",
                tenor="36 months",
                security="Hypothecation of stock and receivables",
                is_sub_limit=False,
            ),
            FacilityData(
                s_no=2,
                nature_of_limit="LC Sight (Local)",
                facility_type="LC",
                approved_limit="30.00",
                currency="PKR",
                profit_rate="4% per annum",
                tenor="At Sight",
                security="Lien on imported goods",
                is_sub_limit=False,
            ),
        ],
        terms_conditions=["Annual audit required"],
    )

    _run_test(sanction_data)


def test_no_collateral():
    """Test that collateral docs are skipped when security is blank."""
    print("\n" + "=" * 80)
    print("TEST: Musharaka without collateral")
    print("=" * 80)

    sanction_data = SanctionData(
        customer_name="XYZ Limited",
        sanction_date="2026-03-07",
        facilities=[
            FacilityData(
                s_no=1,
                nature_of_limit="Musharaka Business Expansion",
                facility_type="Musharaka",
                approved_limit="100.00",
                currency="PKR",
                profit_rate="KIBOR + 2.5%",
                tenor="60 months",
                security="Not Specified",
                is_sub_limit=False,
            ),
        ],
    )

    rule_engine = RuleEngine()
    required_docs = rule_engine.determine_required_documents(sanction_data)

    print(f"\nCustomer: {sanction_data.customer_name}")
    print(f"Security: '{sanction_data.facilities[0].security}'")
    print(f"\nCollateral documents: {len(required_docs['collateral'])}")
    assert len(required_docs["collateral"]) == 0, "Expected 0 collateral docs!"
    print("✓ No collateral documents generated (correct)")


def _run_test(sanction_data: SanctionData):
    rule_engine = RuleEngine()

    print(f"\nCustomer: {sanction_data.customer_name}")
    print(f"Facilities ({len(sanction_data.facilities)}):")
    for f in sanction_data.facilities:
        sub = " [sub-limit]" if f.is_sub_limit else ""
        print(f"  • {f.facility_type} — {f.nature_of_limit}{sub}")

    print("\n--- REQUIRED DOCUMENTS ---")
    required_docs = rule_engine.determine_required_documents(sanction_data)

    for category, docs in required_docs.items():
        if docs:
            print(f"\n{category.upper()} ({len(docs)}):")
            for d in docs:
                print(f"  • {d}")
        else:
            print(f"\n{category.upper()}: none")

    summary = rule_engine.get_document_summary(sanction_data)
    print(f"\nTotal documents to generate: {summary['total_document_count']}")
    print(f"Has collateral: {'Yes' if summary['has_collateral'] else 'No'}")

    print("\n--- VALIDATION ---")
    validation = rule_engine.validate_sanction_data(sanction_data)
    print(f"Valid: {'✓ Yes' if validation['valid'] else '✗ No'}")
    for fv in validation["facility_validations"]:
        status = "✓ PASS" if fv["valid"] else "✗ FAIL"
        raw = fv.get("raw_facility_type", "")
        print(f"  Facility {fv['facility_number']} ({raw} → {fv['facility_type']}): {status}")
        for issue in fv.get("issues", []):
            print(f"    ! {issue}")


if __name__ == "__main__":
    test_lc_facilities()
    test_murabaha_musharaka()
    test_no_collateral()
    print("\n\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)