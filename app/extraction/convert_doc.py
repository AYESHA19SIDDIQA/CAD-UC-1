"""
Helper script to convert .doc files to .docx using Microsoft Word
"""
import os
import sys
from pathlib import Path

def convert_doc_to_docx(doc_path):
    """Convert .doc file to .docx using Microsoft Word"""
    try:
        import win32com.client
    except ImportError:
        print("❌ pywin32 is not installed. Install with: pip install pywin32")
        return None
    
    doc_path = os.path.abspath(doc_path)
    
    if not os.path.exists(doc_path):
        print(f"❌ File not found: {doc_path}")
        return None
    
    # Create output path
    docx_path = doc_path.rsplit('.', 1)[0] + '_converted.docx'
    
    print(f"📄 Converting: {os.path.basename(doc_path)}")
    print(f"➡️ Output: {os.path.basename(docx_path)}")
    
    # Create Word application
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    
    try:
        # Open document
        doc = word.Documents.Open(doc_path)
        
        # Save as .docx (format 16 is docx)
        doc.SaveAs2(docx_path, FileFormat=16)
        
        # Close document
        doc.Close(False)
        
        print(f"✅ Successfully converted to: {docx_path}")
        return docx_path
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return None
        
    finally:
        # Quit Word
        word.Quit()


def main():
    """Convert all .doc files in samples folder"""
    samples_dir = Path(__file__).parent.parent / "samples"
    
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    # Find all .doc files
    doc_files = list(samples_dir.glob("*.doc"))
    
    if not doc_files:
        print(f"❌ No .doc files found in: {samples_dir}")
        return
    
    print("="*80)
    print("DOCUMENT CONVERTER")
    print("="*80)
    print(f"\nFound {len(doc_files)} .doc file(s)\n")
    
    converted = []
    for doc_file in doc_files:
        result = convert_doc_to_docx(str(doc_file))
        if result:
            converted.append(result)
        print()
    
    if converted:
        print("="*80)
        print(f"✅ Successfully converted {len(converted)} file(s)")
        print("="*80)
        print("\nYou can now run: python app/extraction/main_extraction.py")
    else:
        print("="*80)
        print("❌ No files were converted")
        print("="*80)


if __name__ == "__main__":
    main()
