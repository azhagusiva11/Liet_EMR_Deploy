"""
Analytics and Utility API Routes - LEAN VERSION
Handles dashboard and statistics WITHOUT disease detection
"""

import os
import json
from typing import Dict, List
import logging
from datetime import datetime

from data.db.json_adapter import JSONAdapter

logger = logging.getLogger(__name__)

# Initialize services
db = JSONAdapter()


def get_patient_analytics() -> Dict:
    """Get overall system analytics - SIMPLIFIED"""
    try:
        total_patients = 0
        total_visits = 0
        recent_visits = []
        
        # Process all patients
        for patient_data in db.get_all_patients():
            total_patients += 1
            visits = patient_data.get('visits', [])
            total_visits += len(visits)
            
            # Get recent visits
            for visit in visits[-5:]:
                recent_visits.append({
                    'patient_name': patient_data['name'],
                    'visit_date': visit.get('timestamp', 'Unknown'),
                    'visit_type': visit.get('visit_type', 'OPD')
                })
        
        # Sort recent visits
        recent_visits.sort(key=lambda x: x['visit_date'], reverse=True)
        
        return {
            'total_patients': total_patients,
            'total_visits': total_visits,
            'recent_visits': recent_visits[:10],
            'avg_visits_per_patient': round(total_visits / total_patients, 1) if total_patients > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {
            'total_patients': 0,
            'total_visits': 0,
            'recent_visits': [],
            'avg_visits_per_patient': 0
        }


def get_feedback_stats() -> Dict:
    """Get feedback statistics"""
    try:
        total_feedback = 0
        total_rating = 0
        ai_helpful_count = 0
        
        for patient_data in db.get_all_patients():
            for visit in patient_data.get('visits', []):
                if 'clinician_feedback' in visit:
                    feedback_entries = visit['clinician_feedback']
                    if isinstance(feedback_entries, list):
                        for feedback in feedback_entries:
                            total_feedback += 1
                            total_rating += feedback.get('overall_rating', 0)
                            if feedback.get('summary_accuracy', 0) >= 4:
                                ai_helpful_count += 1
        
        return {
            'total_feedback': total_feedback,
            'average_rating': round(total_rating / total_feedback, 2) if total_feedback > 0 else 0,
            'ai_helpful_percentage': round((ai_helpful_count / total_feedback) * 100, 1) if total_feedback > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return {
            'total_feedback': 0,
            'average_rating': 0,
            'ai_helpful_percentage': 0
        }


def save_clinician_feedback(patient_id: str, visit_id: str, feedback_data: Dict) -> Dict:
    """Save clinician feedback for a visit"""
    try:
        patient_data = db.load_patient(patient_id)
        if not patient_data:
            return {"success": False, "message": "Patient not found"}
        
        # Find the visit
        for visit in patient_data.get('visits', []):
            if visit.get('visit_id') == visit_id:
                # Initialize feedback list if not exists
                if 'clinician_feedback' not in visit:
                    visit['clinician_feedback'] = []
                
                # Add feedback entry
                feedback_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'summary_accuracy': feedback_data.get('summary_accuracy', 0),
                    'prescription_appropriate': feedback_data.get('prescription_appropriate', False),
                    'overall_rating': feedback_data.get('overall_rating', 0),
                    'comments': feedback_data.get('comments', '')
                }
                
                visit['clinician_feedback'].append(feedback_entry)
                
                # Update edited content if provided
                if 'edited_summary' in feedback_data:
                    visit['original_summary'] = visit.get('summary', '')
                    visit['summary'] = feedback_data['edited_summary']
                    visit['summary_edited'] = True
                
                if 'edited_prescription' in feedback_data:
                    visit['original_prescription'] = visit.get('prescription', '')
                    visit['prescription'] = feedback_data['edited_prescription']
                    visit['prescription_edited'] = True
                
                # Save updated data
                db.save_patient(patient_data)
                
                return {
                    "success": True,
                    "message": "Feedback saved successfully"
                }
        
        return {"success": False, "message": "Visit not found"}
        
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return {
            "success": False,
            "message": "Failed to save feedback"
        }


def extract_text_from_pdf(pdf_file) -> Dict:
    """Extract text from uploaded PDF"""
    try:
        # Try PyPDF2 first
        try:
            import PyPDF2
            text = ""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return {"success": True, "text": text}
            
        except ImportError:
            # Try pypdf as fallback
            try:
                import pypdf
                text = ""
                pdf_reader = pypdf.PdfReader(pdf_file)
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return {"success": True, "text": text}
                
            except ImportError:
                return {
                    "success": False,
                    "text": "",
                    "error": "No PDF library installed. Install PyPDF2 or pypdf."
                }
        
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return {
            "success": False,
            "text": "",
            "error": str(e)
        }


def save_visit_feedback(patient_id: str, visit_id: str, feedback_type: str) -> Dict:
    """Save quick visit feedback"""
    try:
        patient_data = db.load_patient(patient_id)
        if not patient_data:
            return {"success": False, "message": "Patient not found"}
        
        # Find the visit
        for visit in patient_data.get('visits', []):
            if visit.get('visit_id') == visit_id:
                visit['quick_feedback'] = {
                    'type': feedback_type,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Save updated data
                db.save_patient(patient_data)
                return {"success": True}
        
        return {"success": False, "message": "Visit not found"}
        
    except Exception as e:
        logger.error(f"Error saving visit feedback: {e}")
        return {"success": False, "message": "Failed to save feedback"}


def get_doctor_performance(doctor_id: str) -> Dict:
    """Get doctor performance metrics"""
    try:
        visits_count = 0
        summaries_generated = 0
        prescriptions_edited = 0
        
        for patient_data in db.get_all_patients():
            for visit in patient_data.get('visits', []):
                if visit.get('doctor') == doctor_id:
                    visits_count += 1
                    if visit.get('summary'):
                        summaries_generated += 1
                    if visit.get('prescription_edited'):
                        prescriptions_edited += 1
        
        return {
            'total_visits': visits_count,
            'summaries_generated': summaries_generated,
            'prescriptions_edited': prescriptions_edited,
            'ai_usage_rate': round(summaries_generated / visits_count * 100, 1) if visits_count > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting doctor performance: {e}")
        return {
            'total_visits': 0,
            'summaries_generated': 0,
            'prescriptions_edited': 0,
            'ai_usage_rate': 0
        }