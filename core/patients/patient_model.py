"""
Patient data models using Pydantic v2
Defines schemas for patient creation and updates
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re


class PatientBase(BaseModel):
    """Base patient model with common fields"""
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=150)
    sex: str = Field(..., pattern="^(male|female|other)$")
    mobile: str = Field(..., pattern="^\\+?[1-9]\\d{1,14}$")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Remove extra spaces
        v = ' '.join(v.split())
        # Check for valid name format
        if not re.match(r"^[a-zA-Z\s\.'-]+$", v):
            raise ValueError("Name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v.title()
    
    @field_validator('mobile')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        # Remove spaces and dashes
        v = v.replace(' ', '').replace('-', '')
        # Ensure it starts with +
        if not v.startswith('+'):
            v = '+91' + v  # Default to India
        return v


class PatientCreate(PatientBase):
    """Schema for creating a new patient"""
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    allergies: Optional[List[str]] = Field(default_factory=list)
    chronic_conditions: Optional[List[str]] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "age": 35,
                "sex": "male",
                "mobile": "+919876543210",
                "blood_group": "O+",
                "allergies": ["Penicillin"],
                "chronic_conditions": ["Hypertension"]
            }
        }
    )


class PatientUpdate(BaseModel):
    """Schema for updating patient information"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)
    mobile: Optional[str] = Field(None, pattern="^\\+?[1-9]\\d{1,14}$")
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = ' '.join(v.split())
        if not re.match(r"^[a-zA-Z\s\.'-]+$", v):
            raise ValueError("Name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v.title()
    
    @field_validator('mobile')
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.replace(' ', '').replace('-', '')
        if not v.startswith('+'):
            v = '+91' + v
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 36,
                "allergies": ["Penicillin", "Sulfa drugs"]
            }
        }
    )


class PatientResponse(PatientBase):
    """Schema for patient responses"""
    id: str
    blood_group: Optional[str] = None
    allergies: List[str] = Field(default_factory=list)
    chronic_conditions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    visit_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)