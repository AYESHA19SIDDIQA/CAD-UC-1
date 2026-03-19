"""
Main extraction script: Word Doc → docx_parser → llm_extractor → Gemini API → JSON output
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.extraction.docx_parser import DocxParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine


def extract_from_word_doc(doc_path: str, output_dir: str = None):
    """
    Extract structured data from Word document using Gemini API
    
    Args:
        doc_path: Path to the Word document
        output_dir: Directory to save JSON output (default: extracted_json)
    
    Returns:
        Dictionary containing extracted data
    """
    # Set default output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "extracted_json"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("SANCTION LETTER EXTRACTION")
    print("="*80)
    print(f"\n📄 Input Document: {doc_path}")
    print(f"💾 Output Directory: {output_dir}")
    
    # Step 1: Extract structured data from Word document and save to extracted_text folder
    print("\n[1/5] Extracting structured data from Word document...")
    docx_parser = DocxParser()
    
    try:
        # Use structured extraction to separate tables (facilities) from paragraphs (conditions)
        saved_files = docx_parser.extract_and_save_all(doc_path)
        
        # Get the structured data
        structured_data = docx_parser.extract_structured_data(doc_path)
        
        if not structured_data:
            print("❌ Error: No data extracted from document")
            return None
        
        # Load the saved JSON for verification
        with open(saved_files['structured_file'], 'r', encoding='utf-8') as f:
            saved_json = json.load(f)
            
        print(f"✓ Extracted structured data:")
        print(f"   - Tables (Facilities): {len(structured_data['tables'])} found")
        print(f"   - Paragraphs (Conditions): {len(structured_data['paragraphs'])} found")
        print(f"\n💾 Saved extraction files:")
        print(f"   - Text: {saved_files['text_file']}")
        print(f"   - JSON: {saved_files['structured_file']}")
        print(f"\n📊 Preview:")
        if structured_data['tables']:
            print(f"   First table rows: {len(structured_data['tables'][0])}")
        if structured_data['paragraphs']:
            print(f"   First paragraph: {structured_data['paragraphs'][0][:100]}...")
        
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure the file is a valid Word document")
        print("   2. Try opening it in Word and saving it as .docx")
        print("   3. For .doc files, ensure pywin32 is installed and Microsoft Word is available")
        print("   4. The file might be corrupted or mislabeled - check the file extension")
        import traceback
        traceback.print_exc()
        return None
    
    # Step 2: Read the saved structured data from extracted_text folder
    print("\n[2/5] Loading structured data from saved JSON...")
    try:
        with open(saved_files['structured_file'], 'r', encoding='utf-8') as f:
            saved_structured_data = json.load(f)
        print(f"✓ Loaded saved extraction from: {saved_files['structured_file']}")
    except Exception as e:
        print(f"❌ Error loading saved data: {e}")
        return None
    
    # Step 3: Send structured data to LLM for intelligent extraction
    print("\n[3/5] Sending structured data to Gemini API for extraction...")
    llm_extractor = LLMExtractor()
    
    try:
        # Pass the structured data (with tables and paragraphs separated)
        sanction_data = llm_extractor.extract_sanction_data_from_structured(structured_data)
        print("✓ Successfully extracted sanction data with multiple facilities")
        
        # Convert to dictionary
        extracted_dict = sanction_data.model_dump()
        
        # Pretty print extracted data
        print("\n📊 Extracted Data:")
        print(json.dumps(extracted_dict, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error during LLM extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Step 4: Save JSON output
    print("\n[4/5] Saving final JSON output...")
    
    # Generate output filename with timestamp
    doc_name = Path(doc_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{doc_name}_{timestamp}.json"
    output_path = output_dir / output_filename
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_dict, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✓ JSON saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return None
    
    # Step 5: Determine required documents using rule engine
    print("\n[5/5] Determining required documents using rule engine...")
    print("="*80)
    print("DOCUMENT GENERATION REQUIREMENTS")
    print("="*80)
    
    try:
        rule_engine = RuleEngine()
        
        # Get document requirements
        required_docs = rule_engine.determine_required_documents(sanction_data)
        doc_summary = rule_engine.get_document_summary(sanction_data)
        
        print(f"\n📊 Summary for: {doc_summary['customer_name']}")
        print(f"   Facilities: {doc_summary['facility_count']}")
        for i, fac_type in enumerate(doc_summary['facilities'], 1):
            print(f"     {i}. {fac_type}")
        
        print(f"\n📋 Total Documents to Generate: {doc_summary['total_document_count']}")
        
        # Display by category
        print("\n📄 COMPULSORY DOCUMENTS:")
        for doc in required_docs["compulsory"]:
            print(f"   • {doc}")
        
        print("\n📄 GENERAL DOCUMENTS:")
        for doc in required_docs["general"]:
            print(f"   • {doc}")
        
        print("\n🏦 FACILITY-SPECIFIC DOCUMENTS:")
        for doc in required_docs["facility_specific"]:
            print(f"   • {doc}")
        
        if required_docs["collateral"]:
            print("\n🔒 COLLATERAL DOCUMENTS:")
            for doc in required_docs["collateral"]:
                print(f"   • {doc}")
        else:
            print("\n🔒 COLLATERAL DOCUMENTS: None (no security specified)")
        
        # Save document requirements with the extraction
        doc_requirements_file = output_dir / f"{doc_name}_document_requirements_{timestamp}.json"
        with open(doc_requirements_file, 'w', encoding='utf-8') as f:
            json.dump(doc_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Document requirements saved to: {doc_requirements_file}")
        
    except Exception as e:
        print(f"\n⚠️  Warning: Could not determine document requirements: {e}")
        import traceback
        traceback.print_exc()
        
    
    print("\n" + "="*80)
    print("✅ EXTRACTION COMPLETE")
    print("="*80)
    
    return extracted_dict


def main():
    """Main function to run extraction on sample document"""
    # Get the samples directory
    samples_dir = Path(__file__).parent.parent / "samples"
    
    # Check if samples directory exists
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    # Find first Word document in samples folder
    word_docs = list(samples_dir.glob("*.doc")) + list(samples_dir.glob("*.docx"))
    
    if not word_docs:
        print(f"❌ No Word documents found in: {samples_dir}")
        return
    
    # Use the first Word document found
    doc_path = word_docs[0]
    
    print(f"\n🎯 Found document: {doc_path.name}")
    
    # Run extraction
    result = extract_from_word_doc(str(doc_path))
    
    if result:
        print(f"\n✅ Successfully extracted data from {doc_path.name}")
    else:
        print(f"\n❌ Failed to extract data from {doc_path.name}")


if __name__ == "__main__":
    main()
