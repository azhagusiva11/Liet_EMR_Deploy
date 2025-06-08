"""
Visit API Routes - LEAN VERSION
Handles all visit-related endpoints WITHOUT disease detection
"""

from typing import Dict, List
import logging

from core.visits.visit_manager import VisitManager
from core.ai.gpt_engine import GPTEngine
from data.db.json_adapter import JSONAdapter

logger = logging.getLogger(__name__)

# Initialize services
db = JSONAdapter()
visit_manager = VisitManager(db)
gpt_engine = GPTEngine()


def save_visit(patient_id: str, visit_data: Dict) -> Dict:
    """Save a new visit"""
    try:
        return visit_manager.create_visit(patient_id, visit_data)
    except Exception as e:
        logger.error(f"Error saving visit: {e}")
        return {
            "success": False,
            "message": "Failed to save visit"
        }


def save_consultation(patient_id: str, visit_id: str, consultation_data: Dict) -> Dict:
    """Save consultation results (summary, prescription)"""
    try:
        return visit_manager.update_consultation(patient_id, visit_id, consultation_data)
    except Exception as e:
        logger.error(f"Error saving consultation: {e}")
        return {
            "success": False,
            "message": "Failed to save consultation"
        }


def get_patient_visits(patient_id: str) -> List[Dict]:
    """Get all visits for a patient"""
    try:
        return visit_manager.get_patient_visits(patient_id)
    except Exception as e:
        logger.error(f"Error getting visits: {e}")
        return []


def delete_patient_visit(patient_id: str, visit_id: str) -> Dict:
    """Delete a specific visit"""
    try:
        return visit_manager.delete_visit(patient_id, visit_id)
    except Exception as e:
        logger.error(f"Error deleting visit: {e}")
        return {
            "success": False,
            "message": "Failed to delete visit"
        }


def generate_clinical_summary(symptoms_text: str, patient_data: Dict = None, 
                            include_prescription: bool = True, 
                            format_type: str = "SOAP") -> Dict:
    """Generate AI clinical summary"""
    try:
        return gpt_engine.generate_summary(
            symptoms_text, 
            patient_data, 
            include_prescription, 
            format_type
        )
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "success": False,
            "summary": "",
            "prescription": "",
            "error": str(e)
        }


# Remove these functions as they're no longer needed:
# - check_longitudinal_risks (disease detection)