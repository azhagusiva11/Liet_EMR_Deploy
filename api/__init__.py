"""
API Module - LEAN VERSION
Maps functions for app.py WITHOUT disease detection features
"""

# Patient routes
from api.patient_routes import (
    register_patient,
    get_all_patients,
    get_patient_data,
    update_patient_data,
    search_patients,
    delete_patient,
    export_patient_data,
    get_patient_statistics
)

# Visit routes
from api.visit_routes import (
    save_visit,
    save_consultation,
    get_patient_visits,
    delete_patient_visit,
    generate_clinical_summary
)

# Analytics routes (simplified)
from api.analytics_routes import (
    get_patient_analytics,
    get_feedback_stats,
    save_clinician_feedback,
    extract_text_from_pdf,
    save_visit_feedback,
    get_doctor_performance
)

# Make all functions available at package level
__all__ = [
    # Patient functions
    'register_patient',
    'get_all_patients', 
    'get_patient_data',
    'update_patient_data',
    'search_patients',
    'delete_patient',
    'export_patient_data',
    'get_patient_statistics',
    
    # Visit functions
    'save_visit',
    'save_consultation',
    'get_patient_visits',
    'delete_patient_visit',
    'generate_clinical_summary',
    
    # Analytics functions
    'get_patient_analytics',
    'get_feedback_stats',
    'save_clinician_feedback',
    'extract_text_from_pdf',
    'save_visit_feedback',
    'get_doctor_performance'
]