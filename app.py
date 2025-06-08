import streamlit as st
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import hashlib

# Load environment variables properly
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Verify API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✅ OpenAI API key loaded: {len(api_key)} characters")
else:
    print("❌ OpenAI API key not found in environment")

# CORE IMPORTS - Phase 1 MVP (LEAN VERSION - NO RARE DISEASE DETECTION)
from api import (
    register_patient, get_all_patients, get_patient_data,
    save_visit, save_consultation, update_patient_data, 
    extract_text_from_pdf, delete_patient_visit,
    save_clinician_feedback, get_feedback_stats,
    generate_clinical_summary, get_patient_analytics,
    search_patients, delete_patient, export_patient_data
)

# Essential utils only (REMOVED voice_input)
from utils.export_tools import generate_visit_pdf, generate_visit_docx
from utils.drug_checker import DrugInteractionChecker
from utils.medical_validator_v2 import MedicalValidator
from utils.pdf_processor import PDFProcessor
from utils.senior_doctor_feedback import feedback_system
from utils.silent_tracker import tracker
from utils.analytics_helper import (
    load_tracking_data, get_doctor_personal_stats, 
    get_daily_visit_chart_data, get_doctor_leaderboard,
    get_recent_actions, get_feature_usage_stats
)

# Initialize services
os.makedirs("logs", exist_ok=True)
drug_checker = DrugInteractionChecker()
validator = MedicalValidator()
pdf_processor = PDFProcessor()

# Helper functions
def safe_save_visit(patient_id: str, visit_data: dict) -> dict:
    """Wrapper to ensure data is in correct format before calling save_visit"""
    try:
        # Ensure all required fields exist and are correct type
        cleaned_data = {
            'chief_complaint': str(visit_data.get('chief_complaint', '')),
            'visit_type': str(visit_data.get('visit_type', 'opd')).lower(),
            'timestamp': visit_data.get('timestamp', datetime.now().isoformat()),
            'doctor': visit_data.get('doctor', 'Dr. Smith'),
            'format_type': visit_data.get('format_type', 'SOAP')
        }
        
        # Ensure vitals is a dict, not a list or None
        vitals = visit_data.get('vitals', {})
        if not isinstance(vitals, dict):
            vitals = {}
        
        # Remove any empty string values from vitals
        cleaned_vitals = {}
        for key, value in vitals.items():
            if value and str(value).strip():
                cleaned_vitals[key] = value
        
        cleaned_data['vitals'] = cleaned_vitals
        
        # Add optional fields if they exist
        if 'summary' in visit_data:
            cleaned_data['summary'] = str(visit_data['summary'])
        if 'prescription' in visit_data:
            cleaned_data['prescription'] = str(visit_data['prescription'])
        if 'is_backdated' in visit_data:
            cleaned_data['is_backdated'] = visit_data['is_backdated']
        if 'lab_results' in visit_data:
            cleaned_data['lab_results'] = visit_data['lab_results']
            
        # Call the actual save_visit
        return save_visit(patient_id, cleaned_data)
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error in safe_save_visit: {str(e)}"
        }

# Set page config
st.set_page_config(
    page_title="Smart EMR - Phase 1",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .feedback-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .alert-box {
        background-color: #ffe6e6;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #ff4444;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_patient' not in st.session_state:
    st.session_state.selected_patient = None
if 'current_doctor' not in st.session_state:
    st.session_state.current_doctor = "Dr. Smith"
if 'workflow_state' not in st.session_state:
    st.session_state.workflow_state = {
        'summary_generated': False,
        'current_summary': None,
        'current_prescription': None,
        'current_visit_data': None,
        'lab_results': None,
        'visit_saved': False,
        'visit_id': None,
        'original_prescription': None,
        'current_summary_id': None
    }
# Add session ID if not exists
if 'session_id' not in st.session_state:
    st.session_state.session_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(hashlib.md5(str(os.urandom(16)).encode()).hexdigest()[:8])

# Track page load
tracker.track("app_loaded")

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🏥 Smart EMR - Phase 1")
with col2:
    # Quick metrics
    patients = get_all_patients()
    st.metric("Total Patients", len(patients))
with col3:
    # API Status
    st.metric("API", "🟢 Online")

# Sidebar for patient management
with st.sidebar:
    st.header("Patient Management")
    
    # Search box
    search_term = st.text_input("🔍 Search patient", placeholder="Name or mobile...")
    
    if search_term:
        tracker.track("patient_search", {"search_term_length": len(search_term)})
        search_results = search_patients(search_term)
        if search_results:
            st.write(f"Found {len(search_results)} patient(s)")
            for patient in search_results:
                if st.button(f"{patient['name']} ({patient['mobile']})", key=f"search_{patient['id']}"):
                    st.session_state.selected_patient = patient['id']
                    tracker.track("patient_selected", {"patient_id": patient['id'], "from": "search"})
                    st.rerun()
    
    st.markdown("---")
    
    # New Registration
    with st.expander("➕ Register New Patient", expanded=not st.session_state.selected_patient):
        with st.form("registration_form"):
            name = st.text_input("Patient Name *")
            age = st.number_input("Age *", min_value=0, max_value=120, value=30)
            sex = st.selectbox("Sex *", ["Male", "Female", "Other"])
            mobile = st.text_input("Mobile Number *", placeholder="+919876543210")
            
            # Optional fields
            blood_group = st.selectbox("Blood Group", ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            allergies = st.text_input("Known Allergies", placeholder="Penicillin, Sulfa drugs...")
            chronic_conditions = st.text_input("Chronic Conditions", placeholder="Diabetes, Hypertension...")
            
            if st.form_submit_button("Register Patient", type="primary"):
                if name and mobile:
                    # Validate inputs
                    name_valid, name_msg = validator.validate_patient_name(name)
                    if not name_valid:
                        st.error(name_msg)
                        st.stop()
                    
                    mobile_valid, mobile_msg = validator.validate_mobile_number(mobile)
                    if not mobile_valid:
                        st.error(mobile_msg)
                        st.stop()
                    
                    # Create patient data dictionary
                    patient_dict = {
                        "name": name,
                        "age": age,
                        "sex": sex.lower(),  # Convert to lowercase for validation
                        "mobile": mobile if mobile.startswith('+') else f"+91{mobile}",
                        "blood_group": blood_group if blood_group else None,
                        "allergies": [a.strip() for a in allergies.split(',')] if allergies else [],
                        "chronic_conditions": [c.strip() for c in chronic_conditions.split(',')] if chronic_conditions else []
                    }
                    
                    tracker.track("registration_attempt", {
                        "has_blood_group": bool(blood_group),
                        "has_allergies": bool(allergies),
                        "has_chronic": bool(chronic_conditions)
                    })
                    
                    result = register_patient(patient_dict)
                    
                    if result['success']:
                        tracker.track("patient_registered", {"patient_id": result['patient_id']})
                        st.success("Patient registered successfully!")
                        st.session_state.selected_patient = result['patient_id']
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {result['message']}")

    # Existing patients list
    st.subheader("Existing Patients")
    patients = get_all_patients()
    
    for patient in patients[:10]:  # Show first 10
        if st.button(f"👤 {patient['name']} ({patient['age']}y)", key=patient['id']):
            st.session_state.selected_patient = patient['id']
            tracker.track("patient_selected", {"patient_id": patient['id'], "from": "list"})
            st.rerun()

# Main content area
if st.session_state.selected_patient:
    patient_data = get_patient_data(st.session_state.selected_patient)
    
    if not patient_data:
        st.error("Patient data not found!")
        st.session_state.selected_patient = None
        st.stop()
    
    # Patient Header
    st.markdown(f"## 👤 {patient_data['name']} - {patient_data['age']}y {patient_data['sex']}")
    
    # Quick info bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mobile", patient_data.get('mobile', 'N/A'))
    with col2:
        st.metric("Blood Group", patient_data.get('blood_group', 'Unknown'))
    with col3:
        total_visits = len(patient_data.get('visits', []))
        st.metric("Total Visits", total_visits)
    with col4:
        if patient_data.get('allergies'):
            st.warning(f"⚠️ Allergies: {', '.join(patient_data['allergies'])}")
    
    # TABS - ONLY 2
    tab1, tab2 = st.tabs(["📋 Clinical Workflow", "📊 Analytics"])
    
    # TAB 1: CLINICAL WORKFLOW
    with tab1:
        # Visit type selector
        visit_type = st.radio("Visit Type", ["OPD", "Admitted", "Backdated Entry"], horizontal=True)
        
        if visit_type == "OPD":
            st.header("New OPD Consultation")
            
            # STEP 1: DATA ENTRY
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Chief complaints
                st.subheader("Chief Complaints")
                
                # Track if symptoms change
                symptoms_text = st.text_area(
                    "Enter symptoms, history, examination findings...",
                    value=st.session_state.get('symptoms_text', ''),
                    height=150,
                    key="symptoms_input"
                )
                
                # Track symptom input
                if symptoms_text != st.session_state.get('last_symptoms', ''):
                    if symptoms_text:  # Only track if not empty
                        tracker.track("symptoms_entered", {
                            "length": len(symptoms_text),
                            "word_count": len(symptoms_text.split())
                        })
                    st.session_state.last_symptoms = symptoms_text
            
            with col2:
                # Summary format selection
                st.subheader("Options")
                summary_format = st.radio(
                    "Summary Format",
                    ["SOAP", "INDIAN_EMR"],
                    format_func=lambda x: "SOAP Note" if x == "SOAP" else "Indian EMR Format"
                )
                
                # Track format changes
                if summary_format != st.session_state.get('last_format'):
                    tracker.track("format_changed", {"format": summary_format})
                    st.session_state.last_format = summary_format
                
                include_prescription = st.checkbox("Include Prescription", value=True)
            
            # Vitals Section
            st.subheader("Vital Signs")
            vitals_start = datetime.now()
            
            vcol1, vcol2, vcol3, vcol4 = st.columns(4)
            with vcol1:
                bp = st.text_input("BP (mmHg)", placeholder="120/80", key="bp_input")
                temp = st.number_input("Temp (°C)", min_value=0.0, max_value=45.0, value=0.0, step=0.1, format="%.1f", key="temp_input")
            with vcol2:
                hr = st.number_input("HR (bpm)", min_value=0, max_value=200, value=0, key="hr_input")
                spo2 = st.number_input("SpO2 (%)", min_value=0, max_value=100, value=0, key="spo2_input")
            with vcol3:
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=300.0, value=0.0, step=0.1, key="weight_input")
                height = st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=0.0, step=0.1, key="height_input")
                
                # Calculate BMI if both available
                if weight > 0 and height > 0:
                    bmi = weight / ((height/100) ** 2)
                    bmi_status = ""
                    if bmi < 18.5:
                        bmi_status = "Underweight"
                    elif bmi < 25:
                        bmi_status = "Normal"
                    elif bmi < 30:
                        bmi_status = "Overweight"
                    else:
                        bmi_status = "Obese"
                    st.metric("BMI", f"{bmi:.1f} {bmi_status}")
                else:
                    st.metric("BMI", "---")
            with vcol4:
                rr = st.number_input("RR (/min)", min_value=0, max_value=60, value=0, key="rr_input")
            
            # Track if vitals entered
            vitals_entered = any([bp, hr > 0, temp > 0, spo2 > 0, weight > 0, height > 0, rr > 0])
            if vitals_entered and not st.session_state.get('vitals_tracked'):
                tracker.track_timing("vitals_entered", vitals_start, {
                    "has_bp": bool(bp),
                    "has_hr": hr > 0,
                    "has_temp": temp > 0,
                    "has_spo2": spo2 > 0,
                    "has_weight": weight > 0,
                    "has_height": height > 0,
                    "has_rr": rr > 0
                })
                st.session_state.vitals_tracked = True
            
            # Lab Report Upload - FIXED FOR MULTIPLE FILES
            st.subheader("Lab Reports (Optional)")
            uploaded_labs = st.file_uploader(
                "Upload Lab PDFs (can select multiple)", 
                type=['pdf'], 
                key="lab_upload",
                accept_multiple_files=True
            )
            
            lab_results = {}
            if uploaded_labs:
                for idx, uploaded_lab in enumerate(uploaded_labs):
                    tracker.track("lab_upload_started", {"file_index": idx})
                    with st.spinner(f"Processing lab report {idx+1}/{len(uploaded_labs)}..."):
                        result = pdf_processor.process_pdf(uploaded_lab, patient_data['name'])
                        if result['success']:
                            tracker.track("lab_upload_processed", {
                                "file_index": idx,
                                "name_match": result.get('name_match', False),
                                "lab_values_found": len(result.get('lab_results', {}))
                            })
                            
                            # Name validation
                            if not result['name_match'] and result['extracted_name']:
                                st.warning(f"""
                                ⚠️ **Name Mismatch in Report {idx+1}!**
                                - Expected: {patient_data['name']}
                                - Found in PDF: {result['extracted_name']}
                                - Match confidence: {result['match_confidence']*100:.0f}%
                                """)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button(f"✅ Proceed Anyway", key=f"proceed_mismatch_{idx}"):
                                        tracker.track("lab_mismatch_override", {"confidence": result['match_confidence'], "file_index": idx})
                                        st.session_state[f'lab_override_{idx}'] = True
                                with col2:
                                    if st.button(f"❌ Skip This Report", key=f"cancel_mismatch_{idx}"):
                                        tracker.track("lab_mismatch_cancelled", {"file_index": idx})
                                        continue
                            
                            # Show lab results
                            if result['lab_results']:
                                st.success(f"✅ Lab values detected in report {idx+1}:")
                                lab_report = pdf_processor.format_lab_report(result['lab_results'])
                                st.markdown(lab_report)
                                # Merge results
                                lab_results.update(result['lab_results'])
                            else:
                                st.info(f"No standard lab values detected in report {idx+1}")
                        else:
                            tracker.track("lab_upload_failed", {"error": result.get('error', 'Unknown'), "file_index": idx})
                            st.error(f"Failed to process report {idx+1}: {result.get('error', 'Unknown error')}")
                
                # Store combined results
                if lab_results:
                    st.session_state.workflow_state['lab_results'] = lab_results
            
            # STEP 2: GENERATE SUMMARY
            st.markdown("---")
            if st.button("🤖 Generate Summary", type="primary", use_container_width=True):
                if symptoms_text:
                    tracker.track("generate_clicked", {
                        "has_vitals": vitals_entered,
                        "has_lab": bool(lab_results),
                        "format": summary_format
                    })
                    
                    with st.spinner("Generating clinical summary..."):
                        start_time = datetime.now()
                        
                        # Prepare vitals
                        vitals = {}
                        vitals_valid = True
                        
                        if bp and bp.strip():
                            # Validate BP format
                            if '/' in bp:
                                try:
                                    sys, dia = map(int, bp.split('/'))
                                    if sys < 50 or sys > 250 or dia < 30 or dia > 150:
                                        st.error(f"❌ Invalid BP: {sys}/{dia} (unrealistic values)")
                                        vitals_valid = False
                                    else:
                                        vitals['blood_pressure'] = bp
                                except:
                                    st.error("❌ Invalid BP format. Use format: 120/80")
                                    vitals_valid = False
                            else:
                                st.error("❌ Invalid BP format. Use format: 120/80")
                                vitals_valid = False
                        
                        if hr > 0:
                            if hr < 30 or hr > 250:
                                st.error(f"❌ Invalid HR: {hr} bpm (must be between 30-250)")
                                vitals_valid = False
                            else:
                                vitals['heart_rate'] = hr
                        
                        if temp > 0:
                            if temp < 35.0 or temp > 42.0:
                                st.error(f"❌ Invalid temperature: {temp}°C (must be between 35-42°C)")
                                vitals_valid = False
                            else:
                                vitals['temperature'] = temp
                        
                        if spo2 > 0:
                            vitals['spo2'] = spo2
                        if weight > 0:
                            vitals['weight'] = weight
                        if height > 0:
                            vitals['height'] = height
                        if rr > 0:
                            vitals['respiratory_rate'] = rr
                        
                        if not vitals_valid:
                            tracker.track("generate_failed", {"reason": "invalid_vitals"})
                            st.stop()
                        
                        # Prepare patient context with vitals and lab results
                        patient_context = patient_data.copy()
                        patient_context['current_vitals'] = vitals
                        patient_context['lab_results'] = lab_results
                        
                        # Generate summary
                        summary_result = generate_clinical_summary(
                            symptoms_text,
                            patient_context,
                            include_prescription=include_prescription,
                            format_type=summary_format
                        )
                        
                        if summary_result['success']:
                            tracker.track_timing("summary_generated", start_time, {
                                "format": summary_format,
                                "has_prescription": bool(summary_result.get('prescription')),
                                "summary_length": len(summary_result['summary']),
                                "prescription_length": len(summary_result.get('prescription', ''))
                            })
                            
                            # Generate unique summary ID
                            st.session_state.workflow_state['current_summary_id'] = f"{datetime.now().timestamp()}"
                            
                            # Store in session state
                            st.session_state.workflow_state['summary_generated'] = True
                            st.session_state.workflow_state['current_summary'] = summary_result['summary']
                            st.session_state.workflow_state['current_prescription'] = summary_result.get('prescription', '')
                            st.session_state.workflow_state['original_prescription'] = summary_result.get('prescription', '')
                            st.session_state.workflow_state['current_visit_data'] = {
                                'chief_complaint': symptoms_text,
                                'vitals': vitals,
                                'lab_results': lab_results,
                                'timestamp': datetime.now().isoformat(),
                                'doctor': st.session_state.current_doctor,
                                'format_type': summary_format
                            }
                            st.success("✅ Summary generated successfully!")
                        else:
                            tracker.track("generate_failed", {
                                "reason": "api_error",
                                "error": summary_result.get('error', 'Unknown')
                            })
                            st.error(f"Failed to generate summary: {summary_result.get('error', 'Unknown error')}")
                else:
                    st.error("Please enter chief complaints first")
            
            # DISPLAY GENERATED SUMMARY
            if st.session_state.workflow_state['summary_generated']:
                st.markdown("---")
                st.subheader("Generated Clinical Summary")
                
                # Display summary
                st.text_area(
                    "Clinical Summary",
                    value=st.session_state.workflow_state['current_summary'],
                    height=300,
                    disabled=True
                )
                
                # ADD: Peak moment feedback capture (keep existing)
                # Determine case complexity
                complexity = "complex" if len(symptoms_text) > 200 else "simple"
                
                # Capture feedback at peak emotional moment
                feedback_system.ai_summary_reaction(
                    doctor_id=st.session_state.current_doctor,
                    case_complexity=complexity
                )
                
                # Display prescription (editable)
                if st.session_state.workflow_state['current_prescription']:
                    original_prescription = st.session_state.workflow_state['original_prescription']
                    prescription = st.text_area(
                        "Prescription (Edit as needed)",
                        value=st.session_state.workflow_state['current_prescription'],
                        height=150,
                        key="prescription_edit"
                    )
                    
                    # Track prescription edits
                    if prescription != original_prescription and prescription != st.session_state.get('last_tracked_rx'):
                        edit_percentage = 100 * (1 - len(set(prescription) & set(original_prescription)) / max(len(original_prescription), 1))
                        tracker.track("prescription_edited", {
                            "edit_percentage": round(edit_percentage, 1),
                            "length_change": len(prescription) - len(original_prescription),
                            "added_content": len(prescription) > len(original_prescription)
                        })
                        st.session_state.last_tracked_rx = prescription
                    
                    # Check drug interactions
                    if prescription:
                        drug_check = drug_checker.check_prescription(prescription)
                        if drug_check['has_interactions']:
                            tracker.track("drug_interaction_detected", {
                                "interaction_count": len(drug_check['interactions'])
                            })
                            st.warning("⚠️ Drug Interactions Detected:")
                            for interaction in drug_check['interactions']:
                                st.write(f"- {interaction['description']}")
                        if drug_check['has_warnings']:
                            tracker.track("drug_warning_detected", {
                                "warning_count": len(drug_check['warnings'])
                            })
                            st.warning("⚠️ Warnings:")
                            for warning in drug_check['warnings']:
                                st.write(f"- {warning}")
                    
                    # Store final prescription for tracking
                    st.session_state.workflow_state['final_prescription'] = prescription
                else:
                    prescription = ""
                
                # ACTION BUTTONS - COMBINED SAVE & EXPORT
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                # COMBINED SAVE & EXPORT PDF
                with col1:
                    if st.button("💾 Save & Export PDF", type="primary", use_container_width=True):
                        if not st.session_state.workflow_state['visit_saved']:
                            save_start = datetime.now()
                            
                            # Track prescription edits before saving
                            if 'final_prescription' in st.session_state.workflow_state:
                                feedback_system.prescription_check(
                                    doctor_id=st.session_state.current_doctor,
                                    ai_prescription=st.session_state.workflow_state['original_prescription'],
                                    final_prescription=st.session_state.workflow_state['final_prescription']
                                )
                            
                            # Prepare complete visit data
                            visit_data = st.session_state.workflow_state['current_visit_data'].copy()
                            visit_data['visit_type'] = 'opd'
                            
                            # Save visit
                            visit_result = safe_save_visit(st.session_state.selected_patient, visit_data)
                            
                            if visit_result['success']:
                                visit_id = visit_result['visit_id']
                                st.session_state.workflow_state['visit_id'] = visit_id
                                
                                # Save consultation data
                                consultation_data = {
                                    'summary': st.session_state.workflow_state['current_summary'],
                                    'prescription': prescription,
                                    'format_type': summary_format
                                }
                                
                                save_result = save_consultation(
                                    st.session_state.selected_patient,
                                    visit_id,
                                    consultation_data
                                )
                                
                                if save_result['success']:
                                    tracker.track_timing("visit_saved", save_start, {
                                        "visit_id": visit_id,
                                        "had_vitals": bool(visit_data.get('vitals')),
                                        "had_lab": bool(lab_results),
                                        "had_disease_alerts": bool(visit_result.get('disease_alerts')),
                                        "prescription_edited": prescription != st.session_state.workflow_state['original_prescription'],
                                        "format": summary_format
                                    })
                                    
                                    st.success("✅ Visit saved successfully!")
                                    
                                    # Generate PDF immediately
                                    try:
                                        visit_data_for_pdf = visit_data.copy()
                                        visit_data_for_pdf['summary'] = st.session_state.workflow_state['current_summary']
                                        visit_data_for_pdf['prescription'] = prescription
                                        visit_data_for_pdf['visit_id'] = visit_id
                                        
                                        pdf_path = generate_visit_pdf(patient_data, visit_data_for_pdf)
                                        with open(pdf_path, "rb") as f:
                                            st.download_button(
                                                "⬇️ Download PDF",
                                                data=f.read(),
                                                file_name=f"visit_{patient_data['name']}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                                mime="application/pdf"
                                            )
                                        tracker.track("pdf_exported", {"success": True})
                                        
                                        # Simple feedback after save
                                        feedback_system.visit_saved_feedback(
                                            st.session_state.current_doctor,
                                            visit_id
                                        )
                                        
                                        # Mark as saved
                                        st.session_state.workflow_state['visit_saved'] = True
                                        
                                        # Show vitals validation if any issues
                                        if visit_result.get('vitals_validation'):
                                            val = visit_result['vitals_validation']
                                            if val.get('alerts'):
                                                st.warning("⚠️ **Vitals Alert:**")
                                                for alert in val['alerts']:
                                                    st.write(f"- {alert}")
                                        
                                        # Check for disease alerts
                                        if visit_result.get('disease_alerts'):
                                            tracker.track("disease_alert_generated", {
                                                "count": len(visit_result['disease_alerts']),
                                                "top_disease": visit_result['disease_alerts'][0]['disease'],
                                                "top_confidence": visit_result['disease_alerts'][0]['confidence']
                                            })
                                            st.error(f"🚨 {len(visit_result['disease_alerts'])} Rare Disease Alert(s) Detected!")
                                            for alert in visit_result['disease_alerts']:
                                                st.write(f"- **{alert['disease']}** ({alert['confidence']*100:.0f}% confidence)")
                                                st.write(f"  {alert['message']}")
                                    except Exception as e:
                                        tracker.track("pdf_export_failed", {"error": str(e)})
                                        st.error(f"PDF export failed: {str(e)}")
                                else:
                                    tracker.track("save_failed", {"stage": "consultation", "message": save_result.get('message')})
                                    st.error("Failed to save consultation")
                            else:
                                tracker.track("save_failed", {"stage": "visit", "message": visit_result.get('message')})
                                st.error(f"Failed to save visit: {visit_result.get('message')}")
                        else:
                            st.info("Visit already saved")
                
                # COMBINED SAVE & EXPORT WORD
                with col2:
                    if st.button("💾 Save & Export Word", type="primary", use_container_width=True):
                        if not st.session_state.workflow_state['visit_saved']:
                            save_start = datetime.now()
                            
                            # Same save logic as PDF
                            visit_data = st.session_state.workflow_state['current_visit_data'].copy()
                            visit_data['visit_type'] = 'opd'
                            
                            visit_result = safe_save_visit(st.session_state.selected_patient, visit_data)
                            
                            if visit_result['success']:
                                visit_id = visit_result['visit_id']
                                
                                consultation_data = {
                                    'summary': st.session_state.workflow_state['current_summary'],
                                    'prescription': prescription,
                                    'format_type': summary_format
                                }
                                
                                save_result = save_consultation(
                                    st.session_state.selected_patient,
                                    visit_id,
                                    consultation_data
                                )
                                
                                if save_result['success']:
                                    st.success("✅ Visit saved successfully!")
                                    
                                    # Generate Word document
                                    try:
                                        visit_data_for_docx = visit_data.copy()
                                        visit_data_for_docx['summary'] = st.session_state.workflow_state['current_summary']
                                        visit_data_for_docx['prescription'] = prescription
                                        visit_data_for_docx['visit_id'] = visit_id
                                        visit_data_for_docx['format_type'] = summary_format  # Add format type
                                        
                                        docx_path = generate_visit_docx(patient_data, visit_data_for_docx)
                                        with open(docx_path, "rb") as f:
                                            st.download_button(
                                                "⬇️ Download Word",
                                                data=f.read(),
                                                file_name=f"visit_{patient_data['name']}_{datetime.now().strftime('%Y%m%d')}.docx",
                                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                            )
                                        tracker.track("docx_exported", {"success": True})
                                        
                                        st.session_state.workflow_state['visit_saved'] = True
                                    except Exception as e:
                                        tracker.track("docx_export_failed", {"error": str(e)})
                                        st.error(f"Word export failed: {str(e)}")
                        else:
                            st.info("Visit already saved")
                
                # New Visit
                with col3:
                    if st.session_state.workflow_state['visit_saved']:
                        if st.button("🔄 New Visit", use_container_width=True):
                            tracker.track("new_visit_clicked")
                            # Clear workflow state
                            st.session_state.workflow_state = {
                                'summary_generated': False,
                                'current_summary': None,
                                'current_prescription': None,
                                'current_visit_data': None,
                                'lab_results': None,
                                'visit_saved': False,
                                'visit_id': None,
                                'original_prescription': None,
                                'current_summary_id': None
                            }
                            # Clear symptoms text
                            st.session_state.symptoms_text = ""
                            # Clear tracking flags
                            st.session_state.vitals_tracked = False
                            st.session_state.last_tracked_rx = None
                            st.rerun()
            
            # Visit History Section
            st.markdown("---")
            st.subheader("Recent Visits")
            
            visits = patient_data.get('visits', [])
            if visits:
                # Show last 5 visits
                recent_visits = sorted(visits, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
                
                for visit in recent_visits:
                    visit_date = visit.get('timestamp', 'Unknown date')[:10]
                    visit_type = visit.get('visit_type', 'OPD')
                    
                    # Check if visit has disease alerts
                    alert_emoji = "🚨" if visit.get('disease_alerts') else ""
                    
                    with st.expander(f"{alert_emoji} 📅 {visit_date} - {visit_type} Visit"):
                        tracker.track("visit_history_viewed", {"visit_id": visit.get('visit_id')})
                        
                        # Chief complaint
                        if visit.get('chief_complaint'):
                            st.markdown("**Chief Complaint:**")
                            st.write(visit['chief_complaint'])
                        
                        # Summary
                        if visit.get('summary'):
                            st.markdown("**Clinical Summary:**")
                            st.text(visit['summary'])
                        
                        # Prescription
                        if visit.get('prescription'):
                            st.markdown("**Prescription:**")
                            st.text(visit['prescription'])
                        
                        # Export buttons
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            if st.button(f"📄 Export PDF", key=f"export_hist_pdf_{visit.get('visit_id', visit_date)}"):
                                tracker.track("history_pdf_export", {"visit_id": visit.get('visit_id')})
                                try:
                                    pdf_path = generate_visit_pdf(patient_data, visit)
                                    with open(pdf_path, "rb") as pdf_file:
                                        st.download_button(
                                            label="⬇️ Download PDF",
                                            data=pdf_file.read(),
                                            file_name=f"visit_{patient_data['name']}_{visit_date}.pdf",
                                            mime="application/pdf",
                                            key=f"download_hist_pdf_{visit.get('visit_id')}"
                                        )
                                except Exception as e:
                                    st.error(f"Export failed: {str(e)}")
                        
                        with ecol2:
                            if st.button(f"📝 Export Word", key=f"export_hist_docx_{visit.get('visit_id', visit_date)}"):
                                tracker.track("history_docx_export", {"visit_id": visit.get('visit_id')})
                                try:
                                    docx_path = generate_visit_docx(patient_data, visit)
                                    with open(docx_path, "rb") as docx_file:
                                        st.download_button(
                                            label="⬇️ Download Word",
                                            data=docx_file.read(),
                                            file_name=f"visit_{patient_data['name']}_{visit_date}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key=f"download_hist_docx_{visit.get('visit_id')}"
                                        )
                                except Exception as e:
                                    st.error(f"Export failed: {str(e)}")
                        
                        # Delete button
                        if st.button(f"🗑️ Delete Visit", key=f"delete_{visit.get('visit_id', visit_date)}"):
                            tracker.track("visit_delete_attempted", {"visit_id": visit.get('visit_id')})
                            if st.checkbox("Are you sure?", key=f"confirm_delete_{visit.get('visit_id')}"):
                                result = delete_patient_visit(
                                    st.session_state.selected_patient,
                                    visit.get('visit_id')
                                )
                                if result['success']:
                                    tracker.track("visit_deleted", {"visit_id": visit.get('visit_id')})
                                    st.success("Visit deleted")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete visit")
            else:
                st.info("No previous visits recorded")
        
        elif visit_type == "Admitted":
            st.header("Admitted Patient Entry")
            
            # Daily notes
            with st.form("admitted_notes"):
                st.subheader("Daily Progress Note")
                
                # Date selector
                note_date = st.date_input("Date", datetime.now())
                
                # Vitals
                col1, col2, col3 = st.columns(3)
                with col1:
                    adm_bp = st.text_input("BP", placeholder="120/80")
                    adm_hr = st.number_input("HR", min_value=0, max_value=200, value=0)
                with col2:
                    adm_temp = st.number_input("Temp (°C)", min_value=0.0, max_value=45.0, value=0.0, step=0.1)
                    adm_spo2 = st.number_input("SpO2 (%)", min_value=0, max_value=100, value=0)
                with col3:
                    adm_rr = st.number_input("RR", min_value=0, max_value=60, value=0)
                    adm_urine = st.text_input("Urine Output", placeholder="500ml/24hr")
                
                # Clinical notes
                progress_notes = st.text_area("Progress Notes", height=200)
                treatment_given = st.text_area("Treatment Given Today", height=100)
                plan_tomorrow = st.text_area("Plan for Tomorrow", height=100)
                
                if st.form_submit_button("Save Daily Note", type="primary"):
                    if progress_notes:
                        # Create visit data
                        admitted_vitals = {}
                        if adm_bp:
                            admitted_vitals['blood_pressure'] = adm_bp
                        if adm_hr > 0:
                            admitted_vitals['heart_rate'] = adm_hr
                        if adm_temp > 0:
                            admitted_vitals['temperature'] = adm_temp
                        if adm_spo2 > 0:
                            admitted_vitals['spo2'] = adm_spo2
                        if adm_rr > 0:
                            admitted_vitals['respiratory_rate'] = adm_rr
                        if adm_urine:
                            admitted_vitals['urine_output'] = adm_urine
                        
                        admitted_summary = f"Date: {note_date}\n\n"
                        admitted_summary += f"PROGRESS NOTES:\n{progress_notes}\n\n"
                        admitted_summary += f"TREATMENT GIVEN:\n{treatment_given}\n\n"
                        admitted_summary += f"PLAN:\n{plan_tomorrow}"
                        
                        admitted_visit = {
                            'chief_complaint': f"Admitted patient - Day {note_date}",
                            'visit_type': 'admitted',
                            'vitals': admitted_vitals,
                            'summary': admitted_summary,
                            'timestamp': datetime.combine(note_date, datetime.now().time()).isoformat(),
                            'doctor': st.session_state.current_doctor
                        }
                        
                        result = safe_save_visit(st.session_state.selected_patient, admitted_visit)
                        
                        if result.get('success'):
                            st.success("✅ Daily note saved successfully!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to save: {result.get('message')}")
                    else:
                        st.error("Please enter progress notes")
        
        elif visit_type == "Backdated Entry":
            st.header("Add Historical Visit")
            
            with st.form("backdated_form"):
                # Date and time
                col1, col2 = st.columns(2)
                with col1:
                    back_date = st.date_input("Visit Date", max_value=datetime.now().date())
                with col2:
                    back_time = st.time_input("Visit Time", datetime.now().time())
                
                # Symptoms
                back_symptoms = st.text_area("Chief Complaints", height=100)
                
                # Vitals
                st.subheader("Vitals (if recorded)")
                vcol1, vcol2, vcol3 = st.columns(3)
                with vcol1:
                    back_bp = st.text_input("BP", placeholder="120/80")
                with vcol2:
                    back_hr = st.number_input("HR", min_value=0, max_value=200, value=0)
                with vcol3:
                    back_temp = st.number_input("Temp", min_value=0.0, max_value=45.0, value=0.0, step=0.1)
                
                # Summary and prescription
                back_notes = st.text_area("Clinical Notes (optional)", height=150)
                back_prescription = st.text_area("Prescription (if given)", height=100)
                
                if st.form_submit_button("Add Historical Visit", type="primary"):
                    if back_symptoms:
                        tracker.track("backdated_entry_submitted", {
                            "date": str(back_date),
                            "has_vitals": bool(back_bp or back_hr > 0 or back_temp > 0),
                            "has_notes": bool(back_notes),
                            "has_rx": bool(back_prescription)
                        })
                        
                        # Create historical visit
                        visit_datetime = datetime.combine(back_date, back_time)
                        
                        # Prepare vitals
                        historical_vitals = {}
                        if back_bp and back_bp.strip():
                            historical_vitals['blood_pressure'] = back_bp
                        if back_hr > 0:
                            historical_vitals['heart_rate'] = back_hr
                        if back_temp > 0:
                            historical_vitals['temperature'] = back_temp
                        
                        # Create visit
                        historical_visit = {
                            'chief_complaint': back_symptoms,
                            'visit_type': 'opd',
                            'vitals': historical_vitals,
                            'summary': back_notes if back_notes else f"Historical visit on {back_date}",
                            'prescription': back_prescription if back_prescription else "",
                            'is_backdated': True,
                            'timestamp': visit_datetime.isoformat(),
                            'doctor': st.session_state.current_doctor
                        }
                        
                        # Save
                        result = safe_save_visit(st.session_state.selected_patient, historical_visit)
                        
                        if result.get('success'):
                            tracker.track("backdated_entry_saved", {"visit_id": result.get('visit_id')})
                            st.success(f"✅ Historical visit added for {back_date}")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to save: {result.get('message')}")
                    else:
                        st.error("Please enter chief complaints")
    
    # TAB 2: ANALYTICS
    with tab2:
        tracker.track("analytics_viewed")
        st.header("📊 Analytics Dashboard")
        
        # Load tracking data
        tracker_data = load_tracking_data()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Doctors Today", tracker_data['active_doctors_today'])
            st.metric("Total Visits", tracker_data['total_visits'])
        
        with col2:
            st.metric("Avg Visit Duration", f"{tracker_data['avg_visit_duration']:.1f}s")
            st.metric("AI Usage Rate", f"{tracker_data['ai_usage_rate']:.1f}%")
        
        with col3:
            st.metric("Rx Edit Rate", f"{tracker_data['rx_edit_rate']:.1f}%")
            st.metric("Alert Acceptance", f"{tracker_data['alert_acceptance']:.1f}%")
        
        with col4:
            st.metric("WhatsApp Sent", f"{tracker_data['whatsapp_rate']:.1f}%")
            st.metric("Format Preference", tracker_data['preferred_format'])
        
        # Time series chart
        st.subheader("📊 Daily Activity")
        daily_visits = get_daily_visit_chart_data()
        if not daily_visits.empty:
            st.line_chart(daily_visits)
        else:
            st.info("No visit data available yet")
        
        # Doctor leaderboard
        st.subheader("🏆 Doctor Engagement")
        doctor_stats = get_doctor_leaderboard()
        if not doctor_stats.empty:
            st.dataframe(doctor_stats, use_container_width=True)
        else:
            st.info("No doctor activity data yet")
        
        # Feature usage
        st.subheader("🔧 Feature Adoption")
        feature_stats = get_feature_usage_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PDF Exports", feature_stats['pdf_export'])
            st.metric("Word Exports", feature_stats.get('docx_export', 0))
        
        with col2:
            st.metric("Lab Uploads", feature_stats['lab_upload'])
            st.metric("Backdated Entries", feature_stats['backdated_entry'])
            st.metric("Vitals Entered", feature_stats['vitals_entered'])
        
        with col3:
            st.metric("SOAP Format", feature_stats['format_soap'])
            st.metric("Indian EMR Format", feature_stats['format_indian'])
            st.metric("Rx Included", feature_stats['prescription_included'])
        
        # Personal stats for current doctor
        st.markdown("---")
        st.subheader(f"📈 Your Performance ({st.session_state.current_doctor})")
        
        doctor_stats = get_doctor_personal_stats(st.session_state.current_doctor)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Today's Visits", doctor_stats['today_count'])
        with col2:
            st.metric("This Week", doctor_stats['week_count'])
        with col3:
            st.metric("Total Visits", doctor_stats['total_count'])
        with col4:
            st.metric("AI Usage", f"{doctor_stats['ai_usage_rate']}%")
        
        # Personalized message
        if doctor_stats['total_count'] > 50:
            st.success("🌟 Power User! You're maximizing efficiency. Keep up the great work!")
        elif doctor_stats['total_count'] > 20:
            st.info("🌟 You're getting the hang of it! Your efficiency is improving.")
        else:
            st.info("👋 Welcome to Smart EMR! Try the AI summary to save time.")
        
        # Simplified feedback section
        st.markdown("---")
        feedback_system.complex_case_followup(st.session_state.current_doctor)
        
        # Action log
        if st.checkbox("Show Raw Activity Log"):
            recent_actions = get_recent_actions(limit=100)
            if recent_actions:
                st.json(recent_actions)
            else:
                st.info("No actions logged yet")
        
        # Export data button
        if st.button("📥 Export Analytics Data"):
            tracker.track("analytics_data_exported")
            analytics_data = {
                "summary": tracker_data,
                "feature_usage": feature_stats,
                "doctor_stats": doctor_stats['total_count'],
                "recent_actions": get_recent_actions(limit=50)
            }
            st.download_button(
                "⬇️ Download Analytics JSON",
                data=json.dumps(analytics_data, indent=2),
                file_name=f"analytics_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

else:
    # Simple welcome screen
    tracker.track("no_patient_selected")
    st.header("🏥 Welcome to Smart EMR")
    st.info("👈 Register a new patient or search for an existing patient to get started")

# Footer
st.markdown("---")
st.caption(f"Smart EMR v2.0 - Phase 1 MVP | Doctor: {st.session_state.current_doctor} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")