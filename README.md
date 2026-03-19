# Document Generator

An intelligent document generation system that processes sanction letters and automatically generates required banking documents.

## Features

- **PDF Parsing**: Extract text and data from sanction letter PDFs
- **LLM-based Extraction**: Use AI to extract structured data from unstructured text
- **Rule Engine**: Apply business rules to determine document requirements
- **Document Generation**: Automatically generate DOCX documents from templates
- **REST API**: FastAPI-based API for easy integration

## Project Structure

```
document_generator/
│
├── app/
│   ├── main.py                    # FastAPI application entry point
│   │
│   ├── api/
│   │   └── routes.py              # API endpoints
│   │
│   ├── extraction/
│   │   ├── pdf_parser.py          # PDF text extraction
│   │   └── llm_extractor.py       # LLM-based data extraction
│   │
│   ├── schemas/
│   │   └── sanction_schema.py     # Pydantic data models
│   │
│   ├── services/
│   │   ├── rule_engine.py         # Business rules engine
│   │   ├── document_service.py    # Main orchestration service
│   │   └── llm_service.py         # LLM API integration
│   │
│   ├── templates/                 # Document templates (DOCX)
│   │   ├── offer_letter.docx
│   │   ├── murabaha_master.docx
│   │   └── ...
│   │
│   └── utils/
│       ├── docx_generator.py      # DOCX generation utilities
│       └── validators.py          # Data validation utilities
│
├── output/                        # Generated documents output directory
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Installation

1. Clone the repository or navigate to the project directory

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Set up environment variables:
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
```

## Usage

### Running the API Server

```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### API Endpoints

#### Generate Documents
```
POST /api/v1/generate-document
```

Upload a sanction letter PDF to generate required documents.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (PDF)

**Response:**
```json
{
  "success": true,
  "sanction_data": {
    "customer_name": "ABC Corporation",
    "facility_type": "Murabaha",
    "facility_amount": 50000000.0,
    ...
  },
  "generated_files": [
    "output/offer_letter_ABC_Corporation_20260303_120000.docx",
    "output/murabaha_master_ABC_Corporation_20260303_120000.docx"
  ]
}
```

#### Health Check
```
GET /api/v1/health
```

## Supported Facility Types

- **Murabaha**: Cost-plus financing
- **Musharaka**: Partnership financing
- **Ijarah**: Leasing

## Document Templates

Place your DOCX templates in the `app/templates/` directory. Use the following placeholders:

- `{{CUSTOMER_NAME}}`: Customer name
- `{{FACILITY_TYPE}}`: Type of facility
- `{{FACILITY_AMOUNT}}`: Sanctioned amount with currency
- `{{TENOR}}`: Duration in months
- `{{PROFIT_RATE}}`: Profit rate percentage
- `{{PURPOSE}}`: Purpose of the facility
- `{{SECURITY}}`: Security/collateral details
- `{{DATE}}`: Current date

## Development

### Adding New Document Types

1. Create a template in `app/templates/`
2. Update `rule_engine.py` to include the document type
3. The system will automatically handle generation

### Customizing Business Rules

Edit `app/services/rule_engine.py` to modify validation rules and document requirements.

## License

Proprietary - All rights reserved

## Contact

For questions or support, contact the development team.






