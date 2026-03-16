"""
Data schemas for sanction letters and documents
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import date

class FacilityData(BaseModel):
    """Schema for individual facility data"""
    
    facility_type: str = Field(..., description="Type of facility (e.g., Murabaha, Musharaka)")
    facility_amount: str = Field(..., description="Sanctioned amount (as text with currency)")
    currency: str = Field(default="PKR", description="Currency code")
    tenor: str = Field(..., description="Facility tenor (e.g., '36 months', 'At Sight')")
    profit_rate: str = Field(..., description="Profit rate (as text, may include percentages and details)")
    purpose: Optional[str] = Field(None, description="Purpose of the facility")
    security: Union[str, List[str]] = Field(..., description="Security/collateral details")
    
    @field_validator('security', mode='before')
    @classmethod
    def convert_security_to_string(cls, v):
        """Convert security list to string if needed"""
        if isinstance(v, list):
            return " | ".join(v)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "facility_type": "Murabaha",
                "facility_amount": "PKR 50.00 millions",
                "currency": "PKR",
                "tenor": "36 months",
                "profit_rate": "KIBOR + 3%",
                "purpose": "Working Capital",
                "security": "Hypothecation of stock"
            }
        }

class SanctionData(BaseModel):
    """Schema for extracted sanction letter data with multiple facilities"""
    
    customer_name: str = Field(..., description="Name of the customer")
    sanction_date: Optional[Union[date, str]] = Field(None, description="Date of sanction")
    facilities: List[FacilityData] = Field(..., description="List of sanctioned facilities")
    terms_conditions: Optional[List[str]] = Field(default=[], description="Key terms and conditions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "ABC Corporation",
                "sanction_date": "2026-03-01",
                "facilities": [
                    {
                        "facility_type": "Murabaha",
                        "facility_amount": "PKR 50.00 millions",
                        "currency": "PKR",
                        "tenor": "36 months",
                        "profit_rate": "KIBOR + 3%",
                        "purpose": "Working Capital",
                        "security": "Hypothecation of stock"
                    },
                    {
                        "facility_type": "Musharaka",
                        "facility_amount": "PKR 30.00 millions",
                        "currency": "PKR",
                        "tenor": "24 months",
                        "profit_rate": "KIBOR + 2.5%",
                        "purpose": "Trade Finance",
                        "security": "Pledge of goods"
                    }
                ],
                "terms_conditions": ["Quarterly reviews", "Insurance required"]
            }
        }

class DocumentGenerationRequest(BaseModel):
    """Request schema for document generation"""
    sanction_data: SanctionData
    document_types: List[str] = Field(..., description="Types of documents to generate")

class DocumentGenerationResponse(BaseModel):
    """Response schema for document generation"""
    success: bool
    message: str
    generated_files: List[str]
