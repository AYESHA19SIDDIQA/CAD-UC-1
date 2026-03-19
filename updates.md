# Document Generator — Fix Notes & Template Guide

## Files changed in this patch

| File | Status | What changed |
|------|--------|--------------|
| `app/services/rule_engine.py` | **Fixed** | Facility-type normalisation now handles full nature-of-limit strings like "LC Sight (Foreign) under MSFA" |
| `app/extraction/llm_extractor.py` | **Fixed** | Single file (delete `llm_extractor_prompt.py`). Default model profile changed to `"existing"` (Gemini) |
| `app/utils/docx_generator.py` | **Fixed** | Handles multi-facility `SanctionData`. Correct token replacement. `generate_all_documents()` added |
| `app/services/document_service.py` | **Fixed** | Wires the full pipeline correctly. Supports both DOCX and PDF input |
| `app/test_rule_engine.py` | **Fixed** | Uses correct `FacilityData` fields (`approved_limit` not `facility_amount`) |
| `app/utils/create_templates.py` | **New** | Script to generate starter `.docx` templates in `app/templates/` |

---

## Bug summary

### Bug 1 — Rule engine never matched real facility types
**Problem:** The LLM extracts `facility_type` as `"LC Sight (Foreign) under MSFA"` (the full
nature-of-limit text). The old `_normalize_facility_type` only matched `"lc"` or
`"letter of credit"` exactly, so everything fell through to `.title()` → `"Lc Sight..."` → no match → default docs only.

**Fix:** Added substring matching. The engine now checks whether the lowercase facility string
*contains* a known pattern (`"lc sight"`, `"lc usance"`, `"lc "`, etc.) and returns the
canonical key.

> **Best practice going forward:** In the LLM extraction prompt, instruct the model to put the
> *short canonical name* (`"LC"`, `"Murabaha"`) in `facility_type` and the full description in
> `nature_of_limit`. The prompt in the fixed `llm_extractor.py` now does this.

---

### Bug 2 — `test_rule_engine.py` used old schema fields
**Problem:** The test created `FacilityData(facility_amount="PKR 50.00 millions", ...)` but the
schema replaced `facility_amount` with `approved_limit`. The test crashed before hitting
anything useful.

**Fix:** Rewritten test uses correct fields (`approved_limit`, `nature_of_limit`, `s_no`, etc.).

---

### Bug 3 — Two `llm_extractor` files drifted apart
**Problem:** `llm_extractor.py` and `llm_extractor_prompt.py` had diverging prompts. The
pipeline uses `llm_extractor.py` but its default model was `"qwen_small_local"` — a local CPU
model that isn't running on most machines, causing silent failures.

**Fix:** Delete `llm_extractor_prompt.py`. The fixed `llm_extractor.py` is the single source
of truth, defaults to `"existing"` (whatever provider is in `.env`, typically Gemini).

---

### Bug 4 — `DocxGenerator` used old single-facility schema
**Problem:** `docx_generator.py` referenced `data.facility_type`, `data.facility_amount`,
`data.profit_rate` — none of which exist on the new `SanctionData` model.

**Fix:** Generator now takes `(sanction_data, facility)` where `facility` is the specific
`FacilityData` object for facility-specific documents. A new `generate_all_documents()` method
accepts the full `required_docs` dict from the rule engine.

---

### Bug 5 — `DocumentService` passed wrong type to generator
**Problem:** `determine_required_documents()` returns a `Dict[str, List[str]]` but the old
service iterated it as a flat list of strings.

**Fix:** Service now calls `docx_generator.generate_all_documents(required_docs, sanction_data)`.

---

## Template system — how it works

### Step 1 — Create starter templates (once)
```bash
python -m app.utils.create_templates
```
This writes `.docx` files to `app/templates/` with placeholder tokens already in place.

### Step 2 — Brand the templates
Open each file in Microsoft Word and apply your bank's:
- Logo (header)
- Font (e.g. Calibri, Times New Roman)
- Colour scheme
- Page margins / footer

**Do not remove or rename the `{{TOKEN}}` placeholders.** They will be replaced at
generation time. Formatting around them (bold, font size, colour) is preserved.

### Step 3 — Tokens reference
| Token | Replaced with |
|-------|---------------|
| `{{CUSTOMER_NAME}}` | Customer full name |
| `{{APPROVAL_NO}}` | Sanction approval number |
| `{{SANCTION_DATE}}` | Date of sanction |
| `{{ICRR}}` | Credit rating |
| `{{BUSINESS_SEGMENT}}` | Business segment |
| `{{CUSTOMER_LOCATION}}` | Customer address |
| `{{DATE}}` | Document generation date (today) |
| `{{FACILITY_TYPE}}` | Canonical facility type, e.g. `LC` |
| `{{NATURE_OF_LIMIT}}` | Full nature-of-limit description |
| `{{APPROVED_LIMIT}}` | Approved limit (number only) |
| `{{EXISTING_LIMIT}}` | Existing limit (number only) |
| `{{CURRENCY}}` | Currency code, e.g. `PKR` |
| `{{PROFIT_RATE}}` | Profit / commission rate string |
| `{{TENOR}}` | Tenor string |
| `{{SECURITY}}` | Security / collateral details |
| `{{PURPOSE}}` | Purpose of the facility |

### Step 4 — Add a new template
1. Create `app/templates/my_new_document.docx` with `{{TOKEN}}` placeholders.
2. Add the document name to the relevant list in `rule_engine.py`, e.g.:
   ```python
   "LC": {
       "facility_specific_documents": [
           ...
           "My New Document",   # ← add here
       ],
   }
   ```
   The generator converts `"My New Document"` → `"my_new_document"` → looks for
   `app/templates/my_new_document.docx`.
3. That's it — no other code changes needed.

---

## Running the full pipeline manually

```python
from app.extraction.docx_parser import DocxParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine
from app.utils.docx_generator import DocxGenerator

# 1. Parse
parser = DocxParser()
structured = parser.extract_structured_data("app/samples/my_sanction.docx")

# 2. Extract
extractor = LLMExtractor()   # uses Gemini by default
sanction_data = extractor.extract_sanction_data_from_structured(structured)

# 3. Determine docs
engine = RuleEngine()
required_docs = engine.determine_required_documents(sanction_data)
print(required_docs)

# 4. Generate
generator = DocxGenerator()
generated = generator.generate_all_documents(required_docs, sanction_data)
print(generated)
```