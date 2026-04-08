"""
Test script to demonstrate structured extraction with separation of:
- Tables (Sanction Advice / Facilities)
- Paragraphs (General Conditions)
"""
from extraction.docx_parser import DocxParser
from pathlib import Path
import json

def test_structured_extraction():
    """Test structured data extraction with separated tables and paragraphs"""
    
    parser = DocxParser()
    
    # Test with a sample document
    sample_path = Path("app/samples")
    
    # Look for DOCX files in samples directory
    docx_files = list(sample_path.glob("*.docx")) + list(sample_path.glob("*.doc"))
    
    if not docx_files:
        print("No DOCX files found in samples directory")
        print("Please place a sample sanction letter in app/samples/")
        return
    
    for doc_file in docx_files:
        print(f"\n{'='*80}")
        print(f"Processing: {doc_file.name}")
        print(f"{'='*80}\n")
        
        try:
            # Extract structured data
            structured_data = parser.extract_structured_data(str(doc_file))
            
            print("\n--- TABLES (Sanction Advice / Facilities) ---")
            print(f"Number of tables found: {len(structured_data['tables'])}")
            for i, table in enumerate(structured_data['tables'], 1):
                print(f"\nTable {i}:")
                for row in table:
                    print(f"  {' | '.join(row)}")
            
            print("\n\n--- PARAGRAPHS (General Conditions) ---")
            print(f"Number of paragraphs found: {len(structured_data['paragraphs'])}")
            for i, para in enumerate(structured_data['paragraphs'], 1):
                print(f"{i}. {para}")
            
            # Save both formats for verification
            print("\n\n--- SAVING TO app/extracted_text ---")
            saved_files = parser.extract_and_save_all(str(doc_file))
            
            print(f"✓ Plain text saved to: {saved_files['text_file']}")
            print(f"✓ Structured JSON saved to: {saved_files['structured_file']}")
            
            # Display JSON structure
            print("\n\n--- JSON STRUCTURE PREVIEW ---")
            with open(saved_files['structured_file'], 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                print(json.dumps({
                    "source_file": json_data["source_file"],
                    "extraction_time": json_data["extraction_time"],
                    "note": json_data["note"],
                    "data": {
                        "paragraphs": f"{len(json_data['data']['paragraphs'])} paragraphs",
                        "tables": f"{len(json_data['data']['tables'])} tables"
                    }
                }, indent=2))
            
        except Exception as e:
            print(f"Error processing {doc_file.name}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_structured_extraction()
