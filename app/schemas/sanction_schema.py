"""
Data schemas for sanction letters and documents
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import date

class FacilityData(BaseModel):
    """Schema for individual facility data including detailed limit information."""
    
    s_no: Optional[Union[str, int]] = Field(None, description="Serial number of the facility in the table")
    nature_of_limit: Optional[str] = Field(None, description="Description/nature of the facility (e.g., 'LC Sight (Foreign) under MSFA')")
    facility_type: str = Field(..., description="Type of facility (e.g., Murabaha, Musharaka) – normalized")
    existing_limit: Optional[str] = Field(None, description="Existing limit amount as text (e.g., '50.00')")
    approved_limit: str = Field(..., description="New approved/sanctioned amount (as text with currency)")
    increase_decrease: Optional[str] = Field(None, description="Increase or decrease amount (e.g., '-', '+5.00')")
    currency: str = Field(default="PKR", description="Currency code")
    profit_rate: str = Field(..., description="Profit/commission rate details (as text, may include percentages and notes)")
    tenor: str = Field(..., description="Facility tenor (e.g., '36 months', 'At Sight', 'Max 120 Days')")
    expiry_review: Optional[str] = Field(None, description="Expiry or review indicator (e.g., 'Review', 'Fresh', or a date)")
    purpose: Optional[str] = Field(None, description="Purpose of the facility")
    security: Union[str, List[str]] = Field(..., description="Security/collateral details")
    is_sub_limit: bool = Field(default=False, description="Indicates if this facility is a sub-limit of another")
    parent_facility_s_no: Optional[Union[str, int]] = Field(None, description="If sub-limit, the serial number of the main facility")
    
    @field_validator('security', mode='before')
    @classmethod
    def convert_security_to_string(cls, v):
        """Convert security list to string if needed"""
        if isinstance(v, list):
            return " | ".join(v)
        return v
    
    # For backward compatibility: facility_amount is alias of approved_limit
    @property
    def facility_amount(self) -> str:
        return self.approved_limit
    
    class Config:
        json_schema_extra = {
            "example": {
                "s_no": 1,
                "nature_of_limit": "LC Sight (Foreign) under MSFA",
                "facility_type": "LC",
                "existing_limit": "50.00",
                "approved_limit": "50.00",
                "increase_decrease": "-",
                "currency": "PKR",
                "profit_rate": "85% Commission on opening, 75% Commission on retirement, PAD: K+3%",
                "tenor": "At Sight",
                "expiry_review": "Review",
                "purpose": "Import financing",
                "security": "Cash margin 25%",
                "is_sub_limit": False,
                "parent_facility_s_no": None
            }
        }

class SanctionData(BaseModel):
    """Schema for extracted sanction letter data including header information and multiple facilities."""
    
    approval_no: Optional[str] = Field(None, description="Approval number (e.g., 'CBD/level#03/2018/0090/18/12/2018')")
    proposal_type: Optional[str] = Field(None, description="Type of proposal (e.g., 'Renewal', 'Fresh')")
    approval_level: Optional[str] = Field(None, description="Approval level (e.g., 'Level3')")
    sanction_date: Optional[Union[date, str]] = Field(None, description="Date of sanction/approval")
    customer_name: str = Field(..., description="Name of the customer")
    customer_location: Optional[str] = Field(None, description="Customer's address/location")
    business_segment: Optional[str] = Field(None, description="Business segment (e.g., 'ME')")
    icrr: Optional[str] = Field(None, description="ICRR rating (e.g., '3 - Good')")
    originating_unit_region: Optional[str] = Field(None, description="Originating unit or region")
    facilities: List[FacilityData] = Field(..., description="List of sanctioned facilities")
    terms_conditions: Optional[List[str]] = Field(default=[], description="Key terms and conditions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "approval_no": "CBD/level#03/2018/0090/18/12/2018",
                "proposal_type": "Renewal",
                "approval_level": "Level3",
                "sanction_date": "2018-12-18",
                "customer_name": "M/s Global Technologies & Services",
                "customer_location": "6-L Block-6, P.E.C.H.S Sharh-e-Faisal Karachi",
                "business_segment": "ME",
                "icrr": "3 - Good",
                "originating_unit_region": "Shahrah e Faisal Karachi",
                "facilities": [
                    {
                        "s_no": 1,
                        "nature_of_limit": "LC Sight (Foreign) under MSFA",
                        "facility_type": "LC",
                        "existing_limit": "50.00",
                        "approved_limit": "50.00",
                        "increase_decrease": "-",
                        "currency": "PKR",
                        "profit_rate": "85% Commission on opening, 75% Commission on retirement, PAD: K+3%",
                        "tenor": "At Sight",
                        "expiry_review": "Review",
                        "purpose": "Import financing",
                        "security": "Cash margin 25%",
                        "is_sub_limit": False,
                        "parent_facility_s_no": None
                    },
                    {
                        "s_no": 2,
                        "nature_of_limit": "LC Usance (Foreign) without MSFA – Sub Limit of Facility 1",
                        "facility_type": "LC",
                        "existing_limit": "",
                        "approved_limit": "50.00",
                        "increase_decrease": "",
                        "currency": "PKR",
                        "profit_rate": "85% Commission on opening, 75% Commission on retirement, APSOC",
                        "tenor": "Max 120 Days",
                        "expiry_review": "Fresh",
                        "purpose": "",
                        "security": "",
                        "is_sub_limit": True,
                        "parent_facility_s_no": 1
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