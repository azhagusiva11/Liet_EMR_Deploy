"""
Silent Activity Tracker - Logs all actions without UI disruption
"""
import json
import os
from datetime import datetime
from typing import Dict, Any
import streamlit as st

class SilentTracker:
    def __init__(self):
        os.makedirs("logs/activity", exist_ok=True)
        self.log_file = f"logs/activity/actions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
    def track(self, action: str, metadata: Dict[str, Any] = None):
        """Track any action silently"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "doctor_id": st.session_state.get('current_doctor', 'unknown'),
                "patient_id": st.session_state.get('selected_patient', 'none'),
                "session_id": st.session_state.get('session_id', 'unknown'),
                "action": action,
                "metadata": metadata or {}
            }
            
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            # Silent fail - don't disrupt user flow
            pass
    
    def track_timing(self, action: str, start_time: datetime, metadata: Dict = None):
        """Track action with duration"""
        duration_seconds = (datetime.now() - start_time).total_seconds()
        meta = metadata or {}
        meta['duration_seconds'] = duration_seconds
        self.track(action, meta)

# Global instance
tracker = SilentTracker()