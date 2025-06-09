"""
GPT Engine for Clinical Summary Generation - FIXED VERSION
NO HALLUCINATIONS + CONSISTENT FORMATTING
"""

import os
import re
from typing import Dict, Optional, List
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Senior physician persona for natural safety-first thinking
SENIOR_PHYSICIAN_PERSONA = """
You are Dr. Sharma, a Senior Consultant with 25 years of experience in Internal Medicine and Emergency Care. 
You've managed over 50,000 patients and trained hundreds of junior doctors.

YOUR CLINICAL PHILOSOPHY:
- "The patient who goes home can always come back, but the one we miss might not"
- Always think: "What could go wrong in the next 48 hours?"
- Write notes like they'll be read in court (because they might be)
- Teach while you document - explain your reasoning

YOUR NATURAL HABITS (do these WITHOUT being asked):
1. Always mention "Return immediately if..." - you've seen too many preventable deaths
2. Explain why you avoided certain drugs - juniors need to learn
3. Give specific follow-up times - vague instructions kill patients
4. Connect vitals to decisions - numbers tell stories
5. Think out loud about what worries you
6. ALWAYS interpret lab values in clinical context

CRITICAL RULES - NEVER BREAK THESE:
1. NEVER invent patient history or previous visits
2. ONLY document what is explicitly provided
3. If patient says "for 2 weeks", write "patient reports symptoms for 2 weeks" - don't elaborate
4. NEVER create timelines or progression stories
5. Stick to FACTS provided, not fiction

REMEMBER:
- You've been sued once for a missed diagnosis - never again
- You've saved lives by catching early warning signs
- Your experience shows in HOW you think, not in making up stories
- Write like the patient is your own family member
- Lab values guide but don't dictate treatment
"""


class GPTEngine:
    """Handles GPT-based clinical summary generation with lab integration"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                import openai
                openai.api_key = self.api_key
                self.client = openai
                logger.info(f"OpenAI API key loaded: {len(self.api_key)} characters")
            except Exception as e:
                logger.error(f"OpenAI init failed: {e}")
                self.client = None
        else:
            logger.warning("OpenAI API key not found in environment")
            self.client = None
    
    def generate_summary(self, symptoms_text: str, patient_data: Dict = None,
                        include_prescription: bool = True, 
                        format_type: str = "SOAP") -> Dict:
        """Generate clinical summary using GPT with senior doctor thinking"""
        if not self.api_key or not self.client:
            logger.error("No API key or client available")
            return self._generate_fallback_summary(symptoms_text, patient_data)
        
        # Build patient context WITH LAB RESULTS
        patient_context = self._build_patient_context(patient_data)
        
        # Get format-specific prompt
        prompt = self._build_prompt(patient_context, symptoms_text, format_type, include_prescription)
        
        try:
            response = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": SENIOR_PHYSICIAN_PERSONA
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Low for consistent medical advice
                max_tokens=1500
            )
            
            full_response = response['choices'][0]['message']['content'].strip()
            
            logger.info("OpenAI API call successful")
            logger.debug(f"Full GPT response: {full_response}")
            
            # Split summary and prescription
            summary = self._extract_summary_only(full_response)
            prescription = ""
            
            if include_prescription:
                prescription = self._extract_prescription(full_response)
                logger.debug(f"Extracted prescription: {prescription}")
            
            return {
                "success": True,
                "summary": summary,
                "prescription": prescription,
                "format": format_type
            }
            
        except Exception as e:
            logger.error(f"GPT API error: {e}")
            return self._generate_fallback_summary(symptoms_text, patient_data)
    
    def _build_patient_context(self, patient_data: Dict) -> str:
        """Build patient context including vitals and lab results"""
        if not patient_data:
            return ""
        
        context = f"Patient: {patient_data.get('name', 'Unknown')}, "
        context += f"Age: {patient_data.get('age', 'Unknown')} years, "
        context += f"Sex: {patient_data.get('sex', 'Unknown')}\n"
        
        # Add vitals ONLY if actually provided
        has_vitals = False
        if 'current_vitals' in patient_data and patient_data['current_vitals']:
            vitals = patient_data['current_vitals']
            if any(vitals.get(key) for key in ['blood_pressure', 'heart_rate', 'temperature', 
                                               'respiratory_rate', 'spo2', 'weight', 'height']):
                has_vitals = True
                context += "\nVITAL SIGNS:\n"
                if vitals.get('blood_pressure'):
                    context += f"- Blood Pressure: {vitals['blood_pressure']} mmHg\n"
                if vitals.get('heart_rate'):
                    context += f"- Heart Rate: {vitals['heart_rate']} bpm\n"
                if vitals.get('temperature'):
                    context += f"- Temperature: {vitals['temperature']}°C\n"
                if vitals.get('respiratory_rate'):
                    context += f"- Respiratory Rate: {vitals['respiratory_rate']}/min\n"
                if vitals.get('spo2'):
                    context += f"- SpO2: {vitals['spo2']}%\n"
                if vitals.get('weight'):
                    context += f"- Weight: {vitals['weight']} kg\n"
                if vitals.get('height'):
                    context += f"- Height: {vitals['height']} cm\n"
                    # Calculate BMI if both weight and height available
                    if vitals.get('weight') and vitals.get('height'):
                        height_m = float(vitals['height']) / 100
                        bmi = float(vitals['weight']) / (height_m * height_m)
                        context += f"- BMI: {bmi:.1f} kg/m²\n"
        
        if not has_vitals:
            context += "\n⚠️ NO VITALS RECORDED - I'll recommend checking vitals\n"
        
        # ADD LAB RESULTS WITH CLINICAL INTERPRETATION
        if 'lab_results' in patient_data and patient_data['lab_results']:
            context += "\n🔬 LABORATORY RESULTS (interpret these in clinical context):\n"
            
            for test_name, test_data in patient_data['lab_results'].items():
                value = test_data['value']
                status = test_data.get('status', 'unknown')
                
                # Format test name properly
                formatted_name = test_name.replace('_', ' ').title()
                
                # Add clinical interpretation hints
                if status == 'high':
                    context += f"- {formatted_name}: {value} (HIGH) ⬆️ - Consider clinical significance\n"
                elif status == 'low':
                    context += f"- {formatted_name}: {value} (LOW) ⬇️ - Evaluate for underlying causes\n"
                else:
                    context += f"- {formatted_name}: {value} (Normal range)\n"
            
            context += "Remember to correlate lab findings with clinical presentation.\n"
        
        # Add allergies if present
        if patient_data.get('allergies'):
            context += f"\n⚠️ KNOWN ALLERGIES: {', '.join(patient_data['allergies'])} - AVOID THESE MEDICATIONS\n"
        
        # Add chronic conditions for medication considerations
        if patient_data.get('chronic_conditions'):
            context += f"\nChronic Conditions: {', '.join(patient_data['chronic_conditions'])} - Consider drug interactions\n"
        
        return context
    
    def _build_prompt(self, patient_context: str, symptoms_text: str, 
                     format_type: str, include_prescription: bool) -> str:
        """Build the GPT prompt with anti-hallucination instructions"""
        
        # CRITICAL: Anti-hallucination instructions
        base_rules = """
ABSOLUTE RULES - VIOLATION MEANS PATIENT HARM:
1. Document ONLY what is explicitly stated - NO elaboration
2. If patient says "difficulty swallowing for 2 weeks", write EXACTLY that
3. NEVER create progression narratives like "initially mild, now severe"
4. NEVER mention previous visits unless data is provided
5. NO fictional timelines or backstories
6. Write "Patient reports..." when documenting history
7. Be factual, not creative
"""
        
        if format_type == "SOAP":
            format_instructions = f"""
{base_rules}

Create a SOAP note following this EXACT structure:

SUBJECTIVE:
- Start with: "Chief Complaint: [exactly what patient said]"
- Then: "Patient reports [symptoms exactly as stated]"
- Include duration ONLY if patient mentioned it (e.g., "for 2 weeks")
- NO elaboration or storytelling

OBJECTIVE:
- Vital signs: [use ONLY provided values]
- Physical examination: "Patient appears [basic observation]"
- LAB INTERPRETATION: [interpret any lab values provided]
- If no labs: State "No lab results available"

ASSESSMENT:
- Your clinical impression based on CURRENT symptoms
- Differential diagnoses (list 3-4 possibilities)
- What concerns you about this case
- Risk assessment based on vitals/symptoms

PLAN:
- Investigations needed (be specific)
- Management approach
- Return: "Follow up in [specific timeframe]"
- Red flags: "Return immediately if: [list 3-4 specific symptoms]"
- Safety advice
"""
        else:  # Indian EMR format
            format_instructions = f"""
{base_rules}

Document in Indian EMR format with these EXACT sections:

CHIEF COMPLAINT:
[Write symptoms EXACTLY as patient stated, no elaboration]

HISTORY OF PRESENT ILLNESS:
- Start with: "[Patient name], [age]-year-old [sex], presents with..."
- List symptoms as reported, with duration if mentioned
- NO fictional progression or backstory
- End with current status

CLINICAL EXAMINATION:
- Vital signs: [use ONLY provided values]
- Physical findings: Basic observations only
- BMI calculation if height/weight provided

LABORATORY FINDINGS:
- List and interpret any lab results
- If none: "Pending" or "Not available"

PROVISIONAL DIAGNOSIS:
[Most likely diagnosis based on current presentation]

DIFFERENTIAL DIAGNOSES:
[List 3-4 other possibilities]

INVESTIGATIONS ADVISED:
[Specific tests needed with reasoning]

PLAN & PRECAUTIONS:
- Treatment approach
- Specific follow-up instructions
- Red flag symptoms
- When to return immediately
"""

        prescription_instructions = """

PRESCRIPTION FORMAT:
Write prescription in this EXACT format only:

1. Tab. [Drug name] [dose] - [frequency] x [duration]
2. Syrup/Cap. [Drug name] [dose] - [frequency] x [duration]

RULES:
- Maximum 5 medications
- Use standard abbreviations (OD, BD, TDS, SOS)
- Consider patient's age and weight
- Check for allergies mentioned above
- Each line under 60 characters
- NO explanations in prescription section
""" if include_prescription else ""

        prompt = f"""{patient_context}

CURRENT VISIT - TODAY'S SYMPTOMS:
{symptoms_text}

Based on ONLY the information provided above, create a clinical note.
DO NOT create any fictional history or previous visit details.
If the patient mentions a duration (e.g., "for 2 weeks"), simply document it as stated.

{format_instructions}
{prescription_instructions}"""

        return prompt
    
    def _extract_summary_only(self, full_response: str) -> str:
        """Extract only the clinical summary, excluding prescription"""
        # Find where prescription section starts
        prescription_markers = [
            'PRESCRIPTION:', 'Prescription:', 'TREATMENT GIVEN:', 'Treatment Given:',
            'MEDICATIONS:', 'Medications:', 'Rx:', '===PRESCRIPTION', 'TREATMENT:',
            '=== PRESCRIPTION START ===', '===PRESCRIPTION START==='
        ]
        
        summary = full_response
        for marker in prescription_markers:
            if marker in summary:
                # Cut off at prescription section
                summary = summary.split(marker)[0].strip()
                break
        
        # Remove any instruction text that leaked through
        instruction_phrases = [
            'DO NOT INCLUDE PRESCRIPTION IN THE CLINICAL NOTE',
            'CRITICAL PRESCRIPTION RULES',
            'NEVER make up vital signs',
            'Keep prescription SEPARATE',
            'IMPORTANT PRESCRIPTION RULES',
            'ABSOLUTE RULES',
            'VIOLATION MEANS PATIENT HARM'
        ]
        
        for phrase in instruction_phrases:
            summary = summary.replace(phrase, '').strip()
        
        # Remove markdown artifacts
        summary = summary.replace('---', '')
        summary = summary.replace('===', '')
        
        # Clean up any double asterisks
        summary = summary.replace('**', '')
        
        return summary.strip()
    
    def _extract_prescription(self, full_response: str) -> str:
        """Extract prescription section from response"""
        
        prescription_text = ""
        
        # Look for prescription markers
        markers = ['PRESCRIPTION:', 'Prescription:', 'TREATMENT:', 'MEDICATIONS:', 
                  '===PRESCRIPTION', 'Rx:', 'PRESCRIPTION FORMAT:']
        
        for marker in markers:
            if marker in full_response:
                # Split at the marker and take everything after
                parts = full_response.split(marker)
                if len(parts) > 1:
                    prescription_text = parts[1].strip()
                    # Stop at next section if any
                    for stop_marker in ['CRITICAL', 'PLAN:', 'ASSESSMENT:', 'SUBJECTIVE:', 
                                      'OBJECTIVE:', '===', 'Note:', 'SAFETY ADVICE', 
                                      'PATTERNS', 'WHAT COULD GO WRONG', 'TEACHING',
                                      'Remember to:', 'IMPORTANT', 'Follow-up', 'RULES:',
                                      'Doctor\'s', 'Signature']:
                        if stop_marker in prescription_text:
                            prescription_text = prescription_text.split(stop_marker)[0].strip()
                    break
        
        if not prescription_text:
            logger.warning("No prescription found in GPT response")
            return ""
        
        # Clean up the prescription
        cleaned_lines = []
        for line in prescription_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Skip instruction lines
            skip_phrases = [
                'toxicity', 'if left untreated', 'teaching', 'patterns',
                'what could go wrong', 'safety advice', 'return', 
                'crucial', 'progression', 'complications', 'monitor',
                'follow-up', 'appointment', 'avoid', 'hydration',
                'ms.', 'mr.', 'patient', 'symptoms', 'return immediately',
                'remember', 'important', 'adjust', 'consider', 'based on',
                'write prescription', 'format', 'exact', 'rules'
            ]
            
            if any(phrase in line.lower() for phrase in skip_phrases):
                continue
            
            # Skip lines that are obviously not prescriptions
            if any(skip in line.lower() for skip in ['vital signs', 'not recorded', 'no prescription']):
                continue
            
            # Skip lines > 80 chars (medications are concise)
            if len(line) > 80:
                continue
            
            # Keep the line if it looks like a prescription
            med_indicators = ['tab', 'cap', 'syrup', 'inj', 'drops', 'mg', 'ml', 
                             'od', 'bd', 'tds', 'qid', 'sos', 'stat', 'prn', 
                             '1.', '2.', '3.', '4.', '5.']
            if any(indicator in line.lower() for indicator in med_indicators):
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # If still no prescription, return empty
        if not result or result.lower() == 'none':
            return ""
            
        return result
    
    def _generate_fallback_summary(self, symptoms_text: str, patient_data: Dict) -> Dict:
        """Generate fallback summary without GPT - includes lab awareness"""
        patient_name = patient_data.get('name', 'Patient') if patient_data else 'Patient'
        age = patient_data.get('age', 'Unknown') if patient_data else 'Unknown'
        sex = patient_data.get('sex', 'Unknown') if patient_data else 'Unknown'
        
        summary = f"PATIENT: {patient_name}, {age} years, {sex}\n\n"
        summary += "CHIEF COMPLAINT:\n"
        summary += f"{symptoms_text}\n\n"
        
        # Add vitals if present
        if patient_data and 'current_vitals' in patient_data:
            vitals = patient_data['current_vitals']
            if vitals:
                summary += "VITAL SIGNS:\n"
                if vitals.get('blood_pressure'):
                    summary += f"- BP: {vitals['blood_pressure']} mmHg\n"
                if vitals.get('heart_rate'):
                    summary += f"- HR: {vitals['heart_rate']} bpm\n"
                if vitals.get('temperature'):
                    summary += f"- Temp: {vitals['temperature']}°C\n"
                if vitals.get('spo2'):
                    summary += f"- SpO2: {vitals['spo2']}%\n"
                if vitals.get('weight') and vitals.get('height'):
                    summary += f"- Weight: {vitals['weight']} kg, Height: {vitals['height']} cm\n"
                    height_m = float(vitals['height']) / 100
                    bmi = float(vitals['weight']) / (height_m * height_m)
                    summary += f"- BMI: {bmi:.1f} kg/m²\n"
                summary += "\n"
        
        # Add lab results if present
        if patient_data and 'lab_results' in patient_data and patient_data['lab_results']:
            summary += "LABORATORY RESULTS:\n"
            for test, data in patient_data['lab_results'].items():
                test_name = test.replace('_', ' ').title()
                value = data['value']
                status = data.get('status', 'unknown')
                status_text = f" ({status.upper()})" if status != 'normal' else ""
                summary += f"- {test_name}: {value}{status_text}\n"
            summary += "\n"
        
        summary += "CLINICAL ASSESSMENT:\n"
        summary += "Unable to complete full AI assessment. Based on symptoms and available data:\n"
        
        # Add basic interpretation if lab values present
        if patient_data and 'lab_results' in patient_data:
            lab_results = patient_data['lab_results']
            if any(data.get('status') == 'high' for data in lab_results.values()):
                summary += "- Some lab values are elevated - requires clinical correlation\n"
            if any(data.get('status') == 'low' for data in lab_results.values()):
                summary += "- Some lab values are low - requires clinical correlation\n"
        
        summary += "- Recommend complete clinical examination\n"
        summary += "- Check vital signs if not done\n"
        summary += "- Consider appropriate investigations\n\n"
        
        summary += "SAFETY ADVICE:\n"
        summary += "Return immediately if: worsening symptoms, difficulty breathing, "
        summary += "chest pain, altered consciousness, or any concerning symptoms.\n\n"
        
        summary += "PLAN:\n"
        summary += "- Symptomatic treatment as appropriate\n"
        summary += "- Follow up in 48-72 hours or earlier if worse\n"
        
        # Generate a basic prescription based on symptoms
        prescription = self._generate_fallback_prescription(symptoms_text, patient_data)
        
        return {
            "success": False,
            "summary": summary,
            "prescription": prescription,
            "error": "Using fallback mode - GPT unavailable"
        }
    
    def _generate_fallback_prescription(self, symptoms_text: str, patient_data: Dict = None) -> str:
        """Generate basic prescription based on symptoms with safety checks"""
        symptoms_lower = symptoms_text.lower()
        prescription_lines = []
        
        # Check for allergies
        allergies = []
        if patient_data and patient_data.get('allergies'):
            allergies = [a.lower() for a in patient_data['allergies']]
        
        # Check age for pediatric dosing
        age = patient_data.get('age', 30) if patient_data else 30
        is_pediatric = age < 12
        
        # Check for common symptoms and add appropriate medications
        if 'fever' in symptoms_lower:
            if 'paracetamol' not in allergies and 'acetaminophen' not in allergies:
                if is_pediatric:
                    prescription_lines.append("1. Syrup Paracetamol 250mg/5ml - 5ml TDS x 3 days")
                else:
                    prescription_lines.append("1. Tab. Paracetamol 500mg - 1 tab TDS x 3 days")
        
        if ('pain' in symptoms_lower or 'ache' in symptoms_lower) and not prescription_lines:
            if 'paracetamol' not in allergies:
                dose = "500mg" if not is_pediatric else "250mg"
                prescription_lines.append(f"{len(prescription_lines)+1}. Tab. Paracetamol {dose} - 1 tab TDS x 3 days")
        
        if 'vomit' in symptoms_lower or 'nausea' in symptoms_lower:
            if 'ondansetron' not in allergies:
                dose = "4mg" if not is_pediatric else "2mg"
                prescription_lines.append(f"{len(prescription_lines)+1}. Tab. Ondansetron {dose} - 1 tab SOS")
        
        if 'cough' in symptoms_lower:
            if is_pediatric:
                prescription_lines.append(f"{len(prescription_lines)+1}. Syrup Dextromethorphan - 5ml TDS x 3 days")
            else:
                prescription_lines.append(f"{len(prescription_lines)+1}. Syrup Dextromethorphan - 10ml TDS x 3 days")
        
        if 'cold' in symptoms_lower or 'allergy' in symptoms_lower or 'runny nose' in symptoms_lower:
            if 'cetirizine' not in allergies:
                dose = "10mg" if not is_pediatric else "5mg"
                prescription_lines.append(f"{len(prescription_lines)+1}. Tab. Cetirizine {dose} - 1 tab OD x 5 days")
        
        if 'acid' in symptoms_lower or 'heartburn' in symptoms_lower:
            if 'omeprazole' not in allergies and not is_pediatric:
                prescription_lines.append(f"{len(prescription_lines)+1}. Tab. Omeprazole 20mg - 1 tab OD AC x 14 days")
        
        # Add general advice
        if prescription_lines:
            prescription_lines.append(f"{len(prescription_lines)+1}. Adequate rest and hydration")
        
        return '\n'.join(prescription_lines) if prescription_lines else "Symptomatic treatment as needed"