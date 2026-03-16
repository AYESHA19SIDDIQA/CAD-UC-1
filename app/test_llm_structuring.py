"""
Use LLM to structure the raw extracted text from sanction advice
"""
import os
import sys
import json
from pprint import pprint

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def show_raw_extraction(extracted_file):
    """Show the raw messy extraction"""
    print("="*80)
    print("RAW EXTRACTED TEXT (First 1000 chars)")
    print("="*80)
    with open(extracted_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    print(raw_text[:1000])
    print("\n... [text truncated] ...\n")
    return raw_text

def structure_with_llm(raw_text):
    """
    Use LLM to parse and structure the sanction advice data
    """
    try:
        # Use the professional config system
        from config import get_settings
        from services.llm_service import LLMService
        
        settings = get_settings()
        
        # Check if API key is configured
        if not settings.validate_openai_key():
            print("\n⚠️  API KEY not configured properly")
            print("\n📝 Setup Instructions:")
            print("   1. Make sure .env file exists")
            print("   2. Edit .env and add your OpenRouter API key")
            print("   3. Run this script again")
            return None
        
        # Initialize LLM service
        llm_service = LLMService()
        
        prompt = f"""
You are a banking document parser. Extract structured information from this sanction advice document.

Extract the following fields:
1. Customer name
2. Customer location/address
3. Approval number
4. Approval date
5. Business segment
6. ICRR rating
7. All facility details including:
   - Facility type/name
   - Approved limit (amount in PKR millions)
   - Profit rate/commission
   - Tenor/duration
   - Expiry/Review status
8. Security arrangements for each facility
9. Special conditions
10. Key general conditions (list top 5)

Return the data as a JSON object with these fields.

Sanction Advice Text:
{raw_text}

Return ONLY valid JSON, no explanation.
"""
        
        print("="*80)
        print("CALLING LLM TO STRUCTURE DATA...")
        print("="*80)
        print(f"Provider: {'OpenRouter' if settings.is_using_openrouter() else 'Direct OpenAI'}")
        print(f"Model: {settings.openai_model}")
        print(f"Temperature: {settings.openai_temperature}")
        print("(This may take 10-30 seconds)")
        
        # Use the LLM service to extract structured data
        structured_data = llm_service.extract_structured_data(prompt)
        
        return structured_data
        
    except ValueError as e:
        # Configuration error
        print(f"\n❌ Configuration Error: {e}")
        return None
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're in the correct directory and all packages are installed")
        return None
    except Exception as e:
        print(f"\n❌ Error during LLM processing: {e}")
        import traceback
        traceback.print_exc()
        return None

def structure_with_regex(raw_text):
    """
    Fallback: Use regex/pattern matching to structure data (basic)
    This is a simple fallback if LLM is not available
    """
    import re
    
    print("="*80)
    print("USING REGEX-BASED EXTRACTION (Fallback)")
    print("="*80)
    
    structured = {}
    
    # Extract customer name
    customer_match = re.search(r'Customer name and location:\s*(.+?)(?:\n|,)', raw_text)
    if customer_match:
        structured['customer_name'] = customer_match.group(1).strip()
    
    # Extract approval number
    approval_match = re.search(r'Approval No[.:]?\s*([^\n]+)', raw_text)
    if approval_match:
        structured['approval_number'] = approval_match.group(1).strip()
    
    # Extract date
    date_match = re.search(r'Date:\s*([^\n]+)', raw_text)
    if date_match:
        structured['approval_date'] = date_match.group(1).strip()
    
    # Extract ICRR
    icrr_match = re.search(r'ICRR:\s*([^\n]+)', raw_text)
    if icrr_match:
        structured['icrr'] = icrr_match.group(1).strip()
    
    # Extract business segment
    segment_match = re.search(r'Business Segment:\s*([^\n]+)', raw_text)
    if segment_match:
        structured['business_segment'] = segment_match.group(1).strip()
    
    # Extract facilities (basic - just look for amounts)
    amounts = re.findall(r'(\d+\.\d+)\s*million', raw_text, re.IGNORECASE)
    if amounts:
        structured['facility_amounts_pkr_millions'] = amounts
    
    return structured

def main():
    """Main function to demonstrate structuring raw extraction"""
    
    # Path to extracted file
    extracted_file = r"c:\Users\hp\Desktop\BM_stuff\CAD_01\document_generator\app\samples\Sanction Advice Word Global Technologies Services-2.doc_extracted.txt"
    
    if not os.path.exists(extracted_file):
        print(f"Error: Extracted file not found: {extracted_file}")
        return
    
    # 1. Show raw extraction
    raw_text = show_raw_extraction(extracted_file)
    
    print(f"\nRaw text length: {len(raw_text)} characters")
    print("As you can see, it's very messy with tables, line breaks, etc.\n")
    
    input("Press Enter to structure this data with LLM...")
    
    # 2. Structure with LLM
    structured_data = structure_with_llm(raw_text)
    
    if structured_data:
        print("\n" + "="*80)
        print("✅ STRUCTURED DATA (from LLM)")
        print("="*80)
        print(json.dumps(structured_data, indent=2))
        
        # Save structured data
        output_file = extracted_file.replace("_extracted.txt", "_structured.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2)
        print(f"\n✅ Structured data saved to: {output_file}")
    else:
        print("\n⚠️  LLM structuring failed, using regex fallback...")
        structured_data = structure_with_regex(raw_text)
        print("\n" + "="*80)
        print("STRUCTURED DATA (from Regex - Basic)")
        print("="*80)
        pprint(structured_data)
    
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    print("Before: Raw messy text with \\n, tables, random spacing")
    print("After: Clean JSON with named fields and structured data")
    print("\nThis is the power of LLM for document parsing!")

if __name__ == "__main__":
    main()
