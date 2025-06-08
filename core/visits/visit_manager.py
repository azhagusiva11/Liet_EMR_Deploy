"""
Visit Manager Service - LEAN VERSION
Handles all visit-related operations WITHOUT disease detection or symptom tracking
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

from data.db.json_adapter import JSONAdapter
from core.clinical.vitals_validator import VitalsValidator

logger = logging.getLogger(__name__)


class VisitManager:
    """Manages patient visits and consultations - LEAN VERSION"""
    
    def __init__(self, data_adapter: JSONAdapter):
        self.db = data_adapter
        self.vitals_validator = VitalsValidator()
    
    def create_visit(self, patient_id: str, visit_data: Dict) -> Dict:
        """
        Create a new visit for a patient - SIMPLIFIED
        """
        patient_data = self.db.load_patient(patient_id)
        if not patient_data:
            return {"success": False, "message": "Patient not found"}
        
        # Generate visit ID and timestamp
        visit_data['visit_id'] = self._generate_visit_id()
        visit_data['timestamp'] = datetime.now().isoformat()
        
        # Validate vitals if present
        vitals_validation = None
        if 'vitals' in visit_data and visit_data['vitals']:
            vitals_validation = self.vitals_validator.validate_vitals(
                visit_data['vitals'],
                patient_data.get('age', 30),
                patient_data.get('sex', 'unknown')
            )
            visit_data['vitals_validation'] = vitals_validation
        
        # Add visit to patient record
        if 'visits' not in patient_data:
            patient_data['visits'] = []
        patient_data['visits'].append(visit_data)
        
        # Save updated patient data
        success = self.db.save_patient(patient_data)
        
        if success:
            logger.info(f"Created visit {visit_data['visit_id']} for patient {patient_id}")
            return {
                "success": True,
                "visit_id": visit_data['visit_id'],
                "vitals_validation": vitals_validation
            }
        else:
            return {
                "success": False,
                "message": "Failed to save visit"
            }
    
    def update_consultation(self, patient_id: str, visit_id: str, 
                          consultation_data: Dict) -> Dict:
        """
        Update visit with consultation data - SIMPLIFIED
        """
        patient_data = self.db.load_patient(patient_id)
        if not patient_data:
            return {"success": False, "message": "Patient not found"}
        
        # Find the visit
        visit_index = None
        for i, visit in enumerate(patient_data.get('visits', [])):
            if visit.get('visit_id') == visit_id:
                visit_index = i
                break
        
        if visit_index is None:
            return {"success": False, "message": "Visit not found"}
        
        # Update visit with consultation data
        visit = patient_data['visits'][visit_index]
        visit.update({
            'summary': consultation_data.get('summary', ''),
            'prescription': consultation_data.get('prescription', ''),
            'consultation_timestamp': datetime.now().isoformat(),
            'format_type': consultation_data.get('format_type', 'SOAP')
        })
        
        # Save updated data
        success = self.db.save_patient(patient_data)
        
        if success:
            return {"success": True}
        else:
            return {"success": False, "message": "Failed to update consultation"}
    
    def get_patient_visits(self, patient_id: str) -> List[Dict]:
        """Get all visits for a patient"""
        patient_data = self.db.load_patient(patient_id)
        if not patient_data:
            return []
        
        return patient_data.get('visits', [])
    
    def delete_visit(self, patient_id: str, visit_id: str) -> Dict:
        """Delete a specific visit"""
        patient_data = self.db.load_patient(patient_id)
        if not patient_data:
            return {"success": False, "message": "Patient not found"}
        
        # Find and remove the visit
        visits = patient_data.get('visits', [])
        original_count = len(visits)
        patient_data['visits'] = [v for v in visits if v.get('visit_id') != visit_id]
        
        if len(patient_data['visits']) < original_count:
            # Save updated data
            success = self.db.save_patient(patient_data)
            if success:
                return {"success": True}
            else:
                return {"success": False, "message": "Failed to save changes"}
        else:
            return {"success": False, "message": "Visit not found"}
    
    def _generate_visit_id(self) -> str:
        """Generate unique visit ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"V{timestamp}"
    
    def get_visit_statistics(self, patient_id: str) -> Dict:
        """Get statistics about patient visits - SIMPLIFIED"""
        patient_data = self.db.load_patient(patient_id)
        if not patient_data:
            return {"total_visits": 0}
        
        visits = patient_data.get('visits', [])
        
        # Calculate statistics
        total_visits = len(visits)
        
        # Get date range
        if visits:
            timestamps = [v.get('timestamp', '') for v in visits]
            timestamps.sort()
            first_visit = timestamps[0].split('T')[0] if timestamps[0] else None
            last_visit = timestamps[-1].split('T')[0] if timestamps[-1] else None
        else:
            first_visit = last_visit = None
        
        return {
            'total_visits': total_visits,
            'first_visit': first_visit,
            'last_visit': last_visit
        }