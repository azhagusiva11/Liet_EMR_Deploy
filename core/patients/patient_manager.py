"""
Patient Manager Service
Handles all patient-related operations
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime
import logging

from data.db.json_adapter import JSONAdapter
from core.patients.patient_model import PatientCreate, PatientUpdate

logger = logging.getLogger(__name__)


class PatientManager:
    """Manages patient CRUD operations"""
    
    def __init__(self, data_adapter: JSONAdapter):
        self.db = data_adapter
    
    def create_patient(self, patient_data: PatientCreate) -> Dict:
        """
        Create a new patient record
        """
        # Generate unique patient ID
        patient_id = self._generate_patient_id()
        
        # Check if patient already exists (by mobile)
        existing = self._find_patient_by_mobile(patient_data.mobile)
        if existing:
            return {
                "success": False,
                "message": "Patient with this mobile number already exists",
                "existing_patient_id": existing['id']
            }
        
        # Create patient record
        patient_record = {
            "id": patient_id,
            "name": patient_data.name,
            "age": patient_data.age,
            "sex": patient_data.sex,
            "mobile": patient_data.mobile,
            "blood_group": patient_data.blood_group,
            "allergies": patient_data.allergies,
            "chronic_conditions": patient_data.chronic_conditions,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "visits": []
        }
        
        # Save to database
        success = self.db.save_patient(patient_record)
        
        if success:
            logger.info(f"Created patient {patient_id}: {patient_data.name}")
            return {
                "success": True,
                "patient_id": patient_id,
                "message": "Patient registered successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save patient data"
            }
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """Get patient by ID"""
        return self.db.load_patient(patient_id)
    
    def get_all_patients(self) -> List[Dict]:
        """Get all patients with summary info"""
        patients = self.db.get_all_patients()
        
        # Add summary info
        for patient in patients:
            patient['visit_count'] = len(patient.get('visits', []))
            patient['last_visit'] = self._get_last_visit_date(patient)
        
        return patients
    
    def update_patient(self, patient_id: str, updates: PatientUpdate) -> Dict:
        """Update patient information"""
        patient = self.db.load_patient(patient_id)
        if not patient:
            return {
                "success": False,
                "message": "Patient not found"
            }
        
        # Update only provided fields
        update_dict = updates.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if value is not None:
                patient[field] = value
        
        patient['updated_at'] = datetime.now().isoformat()
        
        # Save updated patient
        success = self.db.save_patient(patient)
        
        if success:
            return {
                "success": True,
                "message": "Patient updated successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to update patient"
            }
    
    def search_patients(self, search_term: str) -> List[Dict]:
        """Search patients by name or mobile"""
        all_patients = self.get_all_patients()
        search_lower = search_term.lower()
        
        results = []
        for patient in all_patients:
            if (search_lower in patient['name'].lower() or 
                search_term in patient['mobile']):
                results.append(patient)
        
        return results
    
    def delete_patient(self, patient_id: str) -> Dict:
        """Delete patient record"""
        success = self.db.delete_patient(patient_id)
        
        if success:
            return {
                "success": True,
                "message": "Patient deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to delete patient"
            }
    
    def _generate_patient_id(self) -> str:
        """Generate unique patient ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"P{timestamp}"
    
    def _find_patient_by_mobile(self, mobile: str) -> Optional[Dict]:
        """Find patient by mobile number"""
        all_patients = self.db.get_all_patients()
        for patient in all_patients:
            if patient.get('mobile') == mobile:
                return patient
        return None
    
    def _get_last_visit_date(self, patient: Dict) -> Optional[str]:
        """Get the date of last visit"""
        visits = patient.get('visits', [])
        if not visits:
            return None
        
        # Sort by timestamp and get the latest
        sorted_visits = sorted(visits, 
                             key=lambda x: x.get('timestamp', ''), 
                             reverse=True)
        
        if sorted_visits:
            timestamp = sorted_visits[0].get('timestamp', '')
            if timestamp:
                return timestamp.split('T')[0]  # Return date part only
        
        return None