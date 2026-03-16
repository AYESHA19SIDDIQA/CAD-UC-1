"""
Test script for extracting text from sample sanction documents
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extraction.docx_parser import DocxParser

def test_single_file(parser, file_path):
    """Test extraction on a single file"""
    print("="*80)
    print(f"FILE: {os.path.basename(file_path)}")
    print("="*80)
    
    # Extract structured data
    structured_data = parser.extract_structured_data(file_path)
    
    print(f"\nNumber of paragraphs: {len(structured_data['paragraphs'])}")
    print(f"Number of tables: {len(structured_data['tables'])}")
    print(f"Total text length: {len(structured_data['full_text'])} characters")
    
    print("\n--- RAW TEXT (First 1500 characters) ---")
    print(structured_data['full_text'][:1500])
    if len(structured_data['full_text']) > 1500:
        print("...")
    
    if structured_data['tables']:
        print("\n--- TABLE DATA ---")
        for table_idx, table in enumerate(structured_data['tables'], 1):
            print(f"\nTable {table_idx} ({len(table)} rows):")
            for row_idx, row in enumerate(table[:10], 1):  # Show first 10 rows
                print(f"  Row {row_idx}: {row}")
            if len(table) > 10:
                print(f"  ... ({len(table) - 10} more rows)")
    
    print("\n")

def main():
    """Test the DOCX parser on sample sanction advice documents"""
    
    # Path to samples directory
    samples_dir = r"c:\Users\hp\Desktop\BM_stuff\CAD_01\document_generator\app\samples"
    
    if not os.path.exists(samples_dir):
        print(f"Error: Samples directory not found at {samples_dir}")
        return
    
    print("="*80)
    print("TESTING DOCX EXTRACTOR ON SANCTION ADVICE SAMPLES")
    print("="*80)
    print(f"\nSamples directory: {samples_dir}\n")
    
    # Initialize parser
    parser = DocxParser()
    
    # Find all .doc and .docx files
    sample_files = []
    for file in os.listdir(samples_dir):
        if file.endswith(('.doc', '.docx')):
            sample_files.append(os.path.join(samples_dir, file))
    
    if not sample_files:
        print("No .doc or .docx files found in samples directory")
        return
    
    print(f"Found {len(sample_files)} sample file(s)\n")
    
    # Process each file
    for sample_file in sample_files:
        try:
            test_single_file(parser, sample_file)
        except Exception as e:
            print(f"Error processing {os.path.basename(sample_file)}: {str(e)}")
            print()

if __name__ == "__main__":
    main()
