"""
Step 6: Document Generation Test
=================================
Loads the already-extracted JSON from main_extraction.py and runs the full
document generation pipeline (create_templates → generate all .docx files).

Run from the project root:
    python -m app.test_document_generation

No re-extraction needed — it reads the latest JSON from extracted_json/.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── helpers ────────────────────────────────────────────────────────────────

def load_latest_extraction(extracted_json_dir: Path) -> dict:
    """Pick the most-recently-written *_requirements_*.json file."""
    # Prefer the document_requirements file (has the categorised doc list)
    reqs = sorted(
        extracted_json_dir.glob("*_document_requirements_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if reqs:
        print(f"📂 Using requirements file: {reqs[0].name}")
        with open(reqs[0], encoding="utf-8") as f:
            return json.load(f)

    # Fallback: main extraction JSON
    mains = sorted(
        [p for p in extracted_json_dir.glob("*.json")
         if "document_requirements" not in p.name],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if mains:
        print(f"📂 Using extraction file: {mains[0].name}")
        with open(mains[0], encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(f"No JSON files found in {extracted_json_dir}")


def ensure_templates(template_dir: Path):
    """Run create_templates if the templates folder is empty."""
    docx_files = list(template_dir.glob("*.docx"))
    if docx_files:
        print(f"✓ Templates found ({len(docx_files)} files) — skipping creation")
        return

    print("⚙️  No templates found — creating starter templates...")
    from app.utils.create_templates import main as create_templates_main
    create_templates_main()
    docx_files = list(template_dir.glob("*.docx"))
    print(f"✓ Created {len(docx_files)} templates")


# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("DOCUMENT GENERATION TEST")
    print("=" * 80)

    # Paths
    project_root = Path(__file__).parent.parent
    extracted_json_dir = project_root / "extracted_json"
    template_dir = project_root / "app" / "templates"
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    # ── Step 1: Load extraction results ──────────────────────────────────
    print("\n[1/4] Loading extraction results...")
    try:
        extraction = load_latest_extraction(extracted_json_dir)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Run main_extraction.py first to generate the JSON.")
        return

    # The requirements file has a 'documents' key; the main file has 'facilities'
    if "documents" in extraction:
        # Requirements file format
        required_docs = extraction["documents"]
        customer_name = extraction.get("customer_name", "Unknown")
        # We still need the full SanctionData — load from the matching main file
        mains = sorted(
            [p for p in extracted_json_dir.glob("*.json")
             if "document_requirements" not in p.name],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not mains:
            print("❌ Could not find main extraction JSON. Run main_extraction.py first.")
            return
        with open(mains[0], encoding="utf-8") as f:
            sanction_dict = json.load(f)
    else:
        # Main extraction file — derive required_docs via rule engine
        sanction_dict = extraction
        customer_name = extraction.get("customer_name", "Unknown")
        print("   (No requirements file found — re-running rule engine)")
        from app.schemas.sanction_schema import SanctionData
        from app.services.rule_engine import RuleEngine
        sanction_data = SanctionData(**sanction_dict)
        required_docs = RuleEngine().determine_required_documents(sanction_data)

    print(f"   Customer: {customer_name}")
    total = sum(len(v) for v in required_docs.values())
    print(f"   Documents to generate: {total}")

    # ── Step 2: Ensure templates exist ───────────────────────────────────
    print("\n[2/4] Checking templates...")
    ensure_templates(template_dir)

    # ── Step 3: Build SanctionData object ────────────────────────────────
    print("\n[3/4] Building SanctionData...")
    from app.schemas.sanction_schema import SanctionData
    try:
        sanction_data = SanctionData(**sanction_dict)
        print(f"   ✓ {len(sanction_data.facilities)} facilities loaded")
        for f in sanction_data.facilities:
            sub = " [sub-limit]" if f.is_sub_limit else ""
            print(f"      • {f.facility_type} — {f.nature_of_limit}{sub}")
    except Exception as e:
        print(f"   ❌ Failed to build SanctionData: {e}")
        return

    # ── Step 4: Generate documents ────────────────────────────────────────
    print("\n[4/4] Generating documents...")
    print("-" * 60)
    from app.utils.docx_generator import DocxGenerator
    generator = DocxGenerator()

    results = {"success": [], "failed": []}

    for category, doc_names in required_docs.items():
        if not doc_names:
            continue
        print(f"\n  📁 {category.upper()}")
        for doc_name in doc_names:
            doc_key = doc_name.lower().replace(" ", "_").replace("-", "_")

            # Facility-specific: one file per facility
            if category == "facility_specific":
                for facility in sanction_data.facilities:
                    label = f"{doc_name} ({facility.facility_type} #{facility.s_no})"
                    try:
                        path = generator.generate_document(doc_key, sanction_data, facility)
                        fname = Path(path).name
                        print(f"    ✓ {label}")
                        print(f"      → {fname}")
                        results["success"].append(path)
                    except Exception as e:
                        print(f"    ✗ {label}")
                        print(f"      Error: {e}")
                        results["failed"].append((label, str(e)))
            else:
                try:
                    path = generator.generate_document(doc_key, sanction_data)
                    fname = Path(path).name
                    print(f"    ✓ {doc_name}")
                    print(f"      → {fname}")
                    results["success"].append(path)
                except Exception as e:
                    print(f"    ✗ {doc_name}")
                    print(f"      Error: {e}")
                    results["failed"].append((doc_name, str(e)))

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("GENERATION SUMMARY")
    print("=" * 80)
    print(f"\n  ✓ Generated: {len(results['success'])} files")
    print(f"  ✗ Failed:    {len(results['failed'])} files")

    if results["failed"]:
        print("\n  Failed documents:")
        for name, err in results["failed"]:
            print(f"    • {name}: {err}")

    if results["success"]:
        print(f"\n  Output directory: {output_dir.resolve()}")
        print("\n  Generated files:")
        for p in results["success"]:
            size_kb = Path(p).stat().st_size // 1024
            print(f"    • {Path(p).name}  ({size_kb} KB)")

    if not results["failed"]:
        print("\n✅ ALL DOCUMENTS GENERATED SUCCESSFULLY")
    else:
        print(f"\n⚠️  {len(results['failed'])} document(s) failed — check errors above")

    print("=" * 80)


if __name__ == "__main__":
    main()