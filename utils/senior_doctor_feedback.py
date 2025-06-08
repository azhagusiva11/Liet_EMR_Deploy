"""
Fixed Senior Doctor Feedback System - Handles Streamlit State Properly
Captures feedback at the right psychological moments without state loss
"""
import json
import os
from datetime import datetime
import streamlit as st

class SeniorDoctorFeedback:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self.feedback_log = "logs/doctor_reactions.jsonl"
        
        # Don't initialize session state in __init__ as it may be called before Streamlit is ready
        
    def _ensure_session_state(self):
        """Ensure session state is initialized when needed"""
        if 'feedback_given' not in st.session_state:
            st.session_state.feedback_given = {}
        if 'show_missed_input' not in st.session_state:
            st.session_state.show_missed_input = False
    
    def capture_moment(self, doctor_id: str, moment: str, data: dict):
        """Log feedback moments with debug info"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "doctor": doctor_id,
            "moment": moment,
            "data": data
        }
        
        try:
            # Debug print
            print(f"🔍 Capturing: {moment} for {doctor_id}")
            print(f"📝 Data: {data}")
            
            with open(self.feedback_log, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()  # Ensure immediate write
            
            print(f"✅ Saved successfully to {self.feedback_log}")
            
            # Also show success in UI
            if moment in ["ai_summary_excellent", "ai_summary_good"]:
                st.success("Thanks for the feedback! 🚀", icon="✅")
            
        except Exception as e:
            print(f"❌ Error logging feedback: {e}")
            st.error(f"Feedback save failed: {e}")
    
    def ai_summary_reaction(self, doctor_id: str, case_complexity: str):
        """The magic moment - right after AI generates summary"""
        
        # Ensure session state is initialized
        self._ensure_session_state()
        
        # Check if feedback already given for this summary
        feedback_key = f"summary_feedback_{st.session_state.get('current_summary_id', 'default')}"
        
        if feedback_key not in st.session_state.feedback_given:
            st.markdown("##### 🎯 Quick reaction to this AI summary?")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("😍 Nailed it", key=f"feedback_excellent_{feedback_key}"):
                    self.capture_moment(doctor_id, "ai_summary_excellent", {
                        "complexity": case_complexity,
                        "emotion": "excellent"
                    })
                    st.session_state.feedback_given[feedback_key] = "excellent"
                    st.rerun()
            
            with col2:
                if st.button("👍 Helpful", key=f"feedback_good_{feedback_key}"):
                    self.capture_moment(doctor_id, "ai_summary_good", {
                        "complexity": case_complexity,
                        "emotion": "helpful"
                    })
                    st.session_state.feedback_given[feedback_key] = "helpful"
                    st.rerun()
            
            with col3:
                if st.button("🤔 Missed something", key=f"feedback_missed_{feedback_key}"):
                    st.session_state.show_missed_input = True
                    self.capture_moment(doctor_id, "ai_summary_missed_clicked", {
                        "complexity": case_complexity,
                        "emotion": "missed"
                    })
            
            # Show input field if "Missed something" was clicked
            if st.session_state.show_missed_input:
                st.markdown("**What did we miss? (helps us improve)**")
                missed_detail = st.text_input(
                    "",
                    placeholder="e.g., Drug interaction, patient history...",
                    key=f"missed_input_{feedback_key}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Submit", key=f"submit_missed_{feedback_key}"):
                        if missed_detail:
                            self.capture_moment(doctor_id, "ai_summary_missed", {
                                "complexity": case_complexity,
                                "emotion": "missed",
                                "details": missed_detail
                            })
                            st.session_state.feedback_given[feedback_key] = "missed"
                            st.session_state.show_missed_input = False
                            st.info("💡 Thanks! We'll improve this.")
                            st.rerun()
                        else:
                            st.warning("Please describe what was missed")
                
                with col2:
                    if st.button("Cancel", key=f"cancel_missed_{feedback_key}"):
                        st.session_state.show_missed_input = False
                        st.rerun()
        else:
            # Show that feedback was already given
            feedback_type = st.session_state.feedback_given[feedback_key]
            emoji_map = {"excellent": "😍", "helpful": "👍", "missed": "🤔"}
            st.info(f"Feedback recorded: {emoji_map.get(feedback_type, '✅')} {feedback_type}")
    
    def prescription_check(self, doctor_id: str, ai_prescription: str, final_prescription: str):
        """Silent tracking of prescription edits"""
        try:
            # Clean up prescriptions for comparison
            ai_clean = ai_prescription.strip() if ai_prescription else ""
            final_clean = final_prescription.strip() if final_prescription else ""
            
            if ai_clean != final_clean:
                self.capture_moment(doctor_id, "prescription_edited", {
                    "ai_version_length": len(ai_clean),
                    "final_version_length": len(final_clean),
                    "was_edited": True,
                    "edit_percentage": round((1 - len(set(final_clean) & set(ai_clean)) / max(len(ai_clean), 1)) * 100, 1)
                })
                print(f"📝 Prescription was edited by {doctor_id}")
            else:
                self.capture_moment(doctor_id, "prescription_accepted", {
                    "prescription_length": len(ai_clean),
                    "was_edited": False
                })
                print(f"✅ Prescription accepted as-is by {doctor_id}")
        except Exception as e:
            print(f"❌ Error in prescription tracking: {e}")
    
    def complex_case_followup(self, doctor_id: str):
        """Direct line to founder for engaged doctors"""
        # Ensure session state is initialized
        self._ensure_session_state()
        
        with st.expander("💬 Chat with founder", expanded=False):
            st.markdown("##### 💭 Got suggestions or concerns?")
            
            message_key = f"founder_message_{doctor_id}_{datetime.now().strftime('%Y%m%d')}"
            
            message = st.text_area(
                "What's working? What's missing?",
                placeholder="The AI is great for simple cases, but for complex autoimmune conditions...",
                height=80,
                key=message_key
            )
            
            if st.button("Send to Founder", key=f"send_{message_key}"):
                if message:
                    self.capture_moment(doctor_id, "founder_direct", {
                        "message": message,
                        "priority": "high",
                        "timestamp": datetime.now().isoformat()
                    })
                    st.success("✅ Message sent! Founder will respond within 24 hours.")
                    st.balloons()
                    # Clear the message
                    st.session_state[message_key] = ""
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Please enter a message")
    
    def visit_saved_feedback(self, doctor_id: str, visit_id: str):
        """Capture feedback after visit is saved"""
        # Ensure session state is initialized
        self._ensure_session_state()
        
        feedback_key = f"visit_saved_{visit_id}"
        
        if feedback_key not in st.session_state.feedback_given:
            st.markdown("### Quick feedback?")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("😍 Great", key=f"save_great_{visit_id}"):
                    self.capture_moment(doctor_id, "visit_saved_feedback", {
                        "rating": "great", 
                        "visit_id": visit_id
                    })
                    st.session_state.feedback_given[feedback_key] = "great"
                    st.success("Thanks! 🚀")
                    st.rerun()
            
            with col2:
                if st.button("👍 Good", key=f"save_good_{visit_id}"):
                    self.capture_moment(doctor_id, "visit_saved_feedback", {
                        "rating": "good", 
                        "visit_id": visit_id
                    })
                    st.session_state.feedback_given[feedback_key] = "good"
                    st.success("Thanks! 👍")
                    st.rerun()
            
            with col3:
                if st.button("🤔 Issues", key=f"save_issues_{visit_id}"):
                    self.capture_moment(doctor_id, "visit_saved_feedback", {
                        "rating": "issues", 
                        "visit_id": visit_id
                    })
                    st.session_state.feedback_given[feedback_key] = "issues"
                    st.info("Please use the founder chat to share details")
                    st.rerun()
    
    def get_doctor_insights(self, doctor_id: str):
        """Generate insights for investors with better error handling"""
        insights = {
            "total_reactions": 0,
            "positive_ratio": 0,
            "improvement_suggestions": [],
            "engagement_level": "new",
            "feedback_types": {
                "ai_summary": 0,
                "prescription": 0,
                "visit_saved": 0,
                "founder_chat": 0
            }
        }
        
        try:
            if os.path.exists(self.feedback_log):
                reactions = []
                with open(self.feedback_log, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if data["doctor"] == doctor_id:
                                    reactions.append(data)
                                    
                                    # Count by type
                                    moment = data["moment"]
                                    if "ai_summary" in moment:
                                        insights["feedback_types"]["ai_summary"] += 1
                                    elif "prescription" in moment:
                                        insights["feedback_types"]["prescription"] += 1
                                    elif "visit_saved" in moment:
                                        insights["feedback_types"]["visit_saved"] += 1
                                    elif "founder" in moment:
                                        insights["feedback_types"]["founder_chat"] += 1
                            except json.JSONDecodeError:
                                print(f"Skipping invalid JSON line: {line}")
                                continue
                
                insights["total_reactions"] = len(reactions)
                
                if reactions:
                    # Calculate positive ratio
                    positive_moments = [
                        "ai_summary_excellent", 
                        "ai_summary_good", 
                        "prescription_accepted",
                        "visit_saved_feedback"
                    ]
                    positive = len([r for r in reactions if r["moment"] in positive_moments 
                                   and r.get("data", {}).get("rating") != "issues"])
                    insights["positive_ratio"] = round(positive / len(reactions) * 100, 1)
                    
                    # Get improvement suggestions
                    missed_feedback = [r for r in reactions if r["moment"] == "ai_summary_missed"]
                    insights["improvement_suggestions"] = [
                        r["data"].get("details", "") for r in missed_feedback[-3:] if r["data"].get("details")
                    ]
                    
                    # Get founder messages
                    founder_messages = [r for r in reactions if r["moment"] == "founder_direct"]
                    for msg in founder_messages[-2:]:  # Last 2 messages
                        if msg["data"].get("message"):
                            insights["improvement_suggestions"].append(f"Founder chat: {msg['data']['message']}")
                    
                    # Determine engagement level
                    if len(reactions) > 10:
                        insights["engagement_level"] = "champion"
                    elif len(reactions) > 5:
                        insights["engagement_level"] = "engaged"
                    else:
                        insights["engagement_level"] = "exploring"
        
        except Exception as e:
            print(f"❌ Error getting insights: {e}")
            st.error(f"Error loading feedback data: {e}")
        
        return insights
    
    def debug_feedback_status(self):
        """Debug function to check feedback system status"""
        # Ensure session state is initialized
        self._ensure_session_state()
        
        st.markdown("### 🔍 Feedback System Debug")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**File Status:**")
            if os.path.exists(self.feedback_log):
                file_size = os.path.getsize(self.feedback_log)
                st.success(f"✅ Log file exists ({file_size} bytes)")
                
                # Count entries
                try:
                    with open(self.feedback_log, 'r') as f:
                        lines = f.readlines()
                    st.info(f"📊 Total entries: {len(lines)}")
                except Exception as e:
                    st.error(f"❌ Can't read file: {e}")
            else:
                st.error("❌ Log file not found")
        
        with col2:
            st.markdown("**Session State:**")
            st.write(f"Feedback given: {len(st.session_state.feedback_given)} items")
            st.write(f"Show missed input: {st.session_state.show_missed_input}")
        
        # Show recent entries
        if st.checkbox("Show recent log entries"):
            try:
                with open(self.feedback_log, 'r') as f:
                    lines = f.readlines()[-10:]  # Last 10 entries
                st.code('\n'.join(lines))
            except Exception as e:
                st.error(f"Can't read log: {e}")

# Global instance
feedback_system = SeniorDoctorFeedback()