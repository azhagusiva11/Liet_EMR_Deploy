# utils/pdf_processor.py
"""
PDF Lab Report Processor with OCR support - Enhanced Lab Detection
Handles text PDFs, image PDFs, and patient name validation
"""

import re
import PyPDF2
import pytesseract
from PIL import Image
import io
from difflib import SequenceMatcher
import logging
from pdf2image import convert_from_bytes
import tempfile
import os

logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self):
        # Enhanced patterns to detect more lab values
        self.common_lab_patterns = {
            # Blood counts
            'hemoglobin': r'(?:hemoglobin|hb|haemoglobin|hgb)[\s:]*(\d+\.?\d*)\s*(?:g/dl|gm/dl|g%)?',
            'wbc': r'(?:wbc|white blood cells?|total wbc|leucocyte|tlc)[\s:]*(\d+\.?\d*)\s*(?:/cumm|x10\^?3|/mm3)?',
            'rbc': r'(?:rbc|red blood cells?|erythrocyte)[\s:]*(\d+\.?\d*)\s*(?:million|x10\^?6|/cumm)?',
            'platelets': r'(?:platelets?|platelet count|plt)[\s:]*(\d+\.?\d*)\s*(?:lakhs?|lac|x10\^?3|/cumm)?',
            'neutrophils': r'(?:neutrophils?|neut|segmented)[\s:]*(\d+\.?\d*)\s*%?',
            'lymphocytes': r'(?:lymphocytes?|lymph|lymp)[\s:]*(\d+\.?\d*)\s*%?',
            'eosinophils': r'(?:eosinophils?|eosin|eos)[\s:]*(\d+\.?\d*)\s*%?',
            
            # Blood sugar
            'glucose': r'(?:glucose|blood sugar|sugar|fbs|rbs|ppbs|fasting blood|random blood)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'hba1c': r'(?:hba1c|glycated hemoglobin|a1c)[\s:]*(\d+\.?\d*)\s*%?',
            
            # Kidney function
            'creatinine': r'(?:creatinine|creat|s\.creatinine|serum creatinine)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'urea': r'(?:urea|blood urea|bun)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'uric_acid': r'(?:uric acid|s\.uric acid)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            
            # Liver function
            'sgpt': r'(?:sgpt|alt|alanine)[\s:]*(\d+\.?\d*)\s*(?:u/l|iu/l|units)?',
            'sgot': r'(?:sgot|ast|aspartate)[\s:]*(\d+\.?\d*)\s*(?:u/l|iu/l|units)?',
            'bilirubin': r'(?:bilirubin|total bilirubin|t\.bili)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'alkaline_phosphatase': r'(?:alkaline phosphatase|alk phos|alp)[\s:]*(\d+\.?\d*)\s*(?:u/l|iu/l)?',
            
            # Lipids
            'cholesterol': r'(?:cholesterol|total cholesterol|t\.cholesterol)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'triglycerides': r'(?:triglycerides?|tg|trigs?)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'hdl': r'(?:hdl|hdl cholesterol|hdl-c)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            'ldl': r'(?:ldl|ldl cholesterol|ldl-c)[\s:]*(\d+\.?\d*)\s*(?:mg/dl|mg%)?',
            
            # Electrolytes
            'sodium': r'(?:sodium|na\+?|s\.sodium)[\s:]*(\d+\.?\d*)\s*(?:meq/l|mmol/l)?',
            'potassium': r'(?:potassium|k\+?|s\.potassium)[\s:]*(\d+\.?\d*)\s*(?:meq/l|mmol/l)?',
            'chloride': r'(?:chloride|cl-?|s\.chloride)[\s:]*(\d+\.?\d*)\s*(?:meq/l|mmol/l)?',
            
            # Thyroid
            'tsh': r'(?:tsh|thyroid stimulating)[\s:]*(\d+\.?\d*)\s*(?:miu/l|uiu/ml)?',
            't3': r'(?:t3|triiodothyronine|total t3)[\s:]*(\d+\.?\d*)\s*(?:ng/dl|ng/ml)?',
            't4': r'(?:t4|thyroxine|total t4)[\s:]*(\d+\.?\d*)\s*(?:ug/dl|mcg/dl)?',
            
            # Others
            'esr': r'(?:esr|erythrocyte sedimentation)[\s:]*(\d+\.?\d*)\s*(?:mm/hr|mm/1st hr)?',
            'crp': r'(?:crp|c-reactive protein)[\s:]*(\d+\.?\d*)\s*(?:mg/l|mg/dl)?',
            'vitamin_d': r'(?:vitamin d|vit d|25-oh)[\s:]*(\d+\.?\d*)\s*(?:ng/ml)?',
            'vitamin_b12': r'(?:vitamin b12|vit b12|b12)[\s:]*(\d+\.?\d*)\s*(?:pg/ml)?',
        }
        
        # Enhanced name patterns
        self.name_patterns = [
            r'patient\s*name\s*:?\s*([a-zA-Z\s\.]+)',
            r'name\s*:?\s*([a-zA-Z\s\.]+)',
            r'pt\.\s*name\s*:?\s*([a-zA-Z\s\.]+)',
            r'patient\s*:?\s*([a-zA-Z\s\.]+)',
            r'name of patient\s*:?\s*([a-zA-Z\s\.]+)',
            r'patient\'s name\s*:?\s*([a-zA-Z\s\.]+)'
        ]
        
        # Check if Tesseract is available on Windows
        self.ocr_available = False
        if os.name == 'nt':  # Windows
            tesseract_path = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.ocr_available = True
                logger.info(f"Tesseract found at: {tesseract_path}")
            else:
                logger.warning("Tesseract not found. OCR will be disabled.")
                logger.warning("To enable OCR, install Tesseract-OCR and set TESSERACT_CMD in .env")
        else:
            # On Linux/Mac, assume tesseract is in PATH
            try:
                pytesseract.get_tesseract_version()
                self.ocr_available = True
            except:
                self.ocr_available = False
    
    def process_pdf(self, pdf_file, expected_patient_name=None):
        """Main entry point for PDF processing"""
        try:
            # Read PDF bytes
            pdf_file.seek(0)  # Reset file pointer
            pdf_bytes = pdf_file.read()
            
            # Try text extraction first
            text_content = self._extract_text_pypdf(pdf_bytes)
            
            # If no text found and OCR is available, try OCR
            if not text_content.strip() and self.ocr_available:
                logger.info("No text found, attempting OCR")
                text_content = self._ocr_pdf(pdf_bytes)
            elif not text_content.strip():
                logger.warning("No text found and OCR not available")
                text_content = ""
            
            # Clean text for better matching
            text_content = self._clean_text(text_content)
            
            # Parse lab values
            lab_results = self._parse_lab_values(text_content)
            
            # Extract and validate patient name
            extracted_name = self._extract_patient_name(text_content)
            name_match = True
            match_confidence = 1.0
            
            if expected_patient_name and extracted_name:
                name_match, match_confidence = self._validate_name(
                    extracted_name, expected_patient_name
                )
            
            return {
                'success': True,
                'text_content': text_content,
                'lab_results': lab_results,
                'extracted_name': extracted_name,
                'name_match': name_match,
                'match_confidence': match_confidence,
                'ocr_available': self.ocr_available
            }
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'lab_results': {},
                'text_content': '',
                'ocr_available': self.ocr_available
            }
    
    def _clean_text(self, text):
        """Clean text for better pattern matching"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Add space after colons if missing
        text = re.sub(r':(\S)', r': \1', text)
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text
    
    def _extract_text_pypdf(self, pdf_bytes):
        """Extract text using PyPDF2"""
        text_content = ""
        try:
            # Create BytesIO object from bytes
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                    
            logger.info(f"Extracted {len(text_content)} characters from PDF")
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            import traceback
            traceback.print_exc()
        
        return text_content
    
    def _ocr_pdf(self, pdf_bytes):
        """OCR PDF pages - only if OCR is available"""
        if not self.ocr_available:
            logger.warning("OCR not available")
            return ""
        
        ocr_text = ""
        try:
            # Check if pdf2image and poppler are available
            try:
                # Convert PDF to images
                images = convert_from_bytes(pdf_bytes, dpi=200)
                logger.info(f"Converted PDF to {len(images)} images")
                
                # OCR each page
                for i, image in enumerate(images[:5]):  # Limit to first 5 pages
                    try:
                        text = pytesseract.image_to_string(image)
                        if text.strip():
                            ocr_text += f"\n--- Page {i + 1} ---\n{text}\n"
                    except Exception as e:
                        logger.error(f"OCR error on page {i}: {e}")
                        
            except Exception as e:
                logger.error(f"PDF to image conversion error: {e}")
                logger.info("Note: You need to install poppler-utils for Windows")
                logger.info("Download from: https://github.com/oschwartz10612/poppler-windows/releases/")
                
        except Exception as e:
            logger.error(f"OCR process error: {e}")
        
        return ocr_text
    
    def _parse_lab_values(self, text):
        """Extract lab values from text with enhanced detection"""
        if not text:
            return {}
            
        text_lower = text.lower()
        results = {}
        
        # Try each pattern
        for test_name, pattern in self.common_lab_patterns.items():
            # Try multiple variations of the pattern
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                try:
                    # Get the value
                    value_str = match.group(1)
                    value = float(value_str)
                    
                    # Skip unrealistic values
                    if value <= 0 or value > 10000:
                        continue
                    
                    # Store the result
                    results[test_name] = {
                        'value': value,
                        'raw_match': match.group(0).strip()
                    }
                    
                    # Add interpretation
                    results[test_name]['status'] = self._interpret_value(
                        test_name, value
                    )
                    
                    # Only take the first valid match for each test
                    break
                    
                except ValueError:
                    continue
        
        # Also look for values in table format
        self._parse_table_format(text, results)
        
        logger.info(f"Found {len(results)} lab values in PDF")
        return results
    
    def _parse_table_format(self, text, results):
        """Parse lab values that might be in table format"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Look for lines that have test name and value separated by spaces/tabs
            # Example: "Hemoglobin    14.5    g/dl"
            parts = re.split(r'\s{2,}|\t+', line.strip())
            
            if len(parts) >= 2:
                test_part = parts[0].lower()
                value_part = parts[1]
                
                # Check if we can match a test name
                for test_name, _ in self.common_lab_patterns.items():
                    test_keywords = test_name.replace('_', ' ').split()
                    
                    if any(keyword in test_part for keyword in test_keywords):
                        try:
                            # Extract numeric value
                            value_match = re.search(r'(\d+\.?\d*)', value_part)
                            if value_match:
                                value = float(value_match.group(1))
                                if test_name not in results and 0 < value < 10000:
                                    results[test_name] = {
                                        'value': value,
                                        'raw_match': line.strip(),
                                        'status': self._interpret_value(test_name, value)
                                    }
                        except:
                            continue
    
    def _interpret_value(self, test_name, value):
        """Enhanced interpretation of lab values"""
        normal_ranges = {
            'hemoglobin': {'male': (13, 17), 'female': (12, 15)},
            'wbc': {'all': (4000, 11000)},
            'rbc': {'male': (4.5, 5.5), 'female': (4.0, 5.0)},
            'platelets': {'all': (1.5, 4.5)},  # in lakhs
            'neutrophils': {'all': (40, 70)},  # percentage
            'lymphocytes': {'all': (20, 40)},  # percentage
            'eosinophils': {'all': (1, 4)},  # percentage
            
            'glucose': {'fasting': (70, 100), 'random': (70, 140)},
            'hba1c': {'all': (4, 5.6)},
            
            'creatinine': {'male': (0.7, 1.3), 'female': (0.6, 1.1)},
            'urea': {'all': (15, 40)},
            'uric_acid': {'male': (3.5, 7.2), 'female': (2.6, 6.0)},
            
            'sgpt': {'all': (0, 40)},
            'sgot': {'all': (0, 40)},
            'bilirubin': {'all': (0.3, 1.2)},
            'alkaline_phosphatase': {'all': (40, 150)},
            
            'cholesterol': {'all': (0, 200)},
            'triglycerides': {'all': (0, 150)},
            'hdl': {'male': (40, 100), 'female': (50, 100)},
            'ldl': {'all': (0, 100)},
            
            'sodium': {'all': (135, 145)},
            'potassium': {'all': (3.5, 5.0)},
            'chloride': {'all': (95, 105)},
            
            'tsh': {'all': (0.4, 4.0)},
            't3': {'all': (80, 200)},
            't4': {'all': (4.5, 12.0)},
            
            'esr': {'all': (0, 20)},
            'crp': {'all': (0, 6)},
            'vitamin_d': {'all': (30, 100)},
            'vitamin_b12': {'all': (200, 900)}
        }
        
        if test_name in normal_ranges:
            ranges = normal_ranges[test_name]
            # Simple check (can be enhanced with age/sex specific ranges)
            range_key = 'all' if 'all' in ranges else list(ranges.keys())[0]
            low, high = ranges[range_key]
            
            if value < low:
                return 'low'
            elif value > high:
                return 'high'
            else:
                return 'normal'
        
        return 'unknown'
    
    def _extract_patient_name(self, text):
        """Extract patient name from text"""
        if not text:
            return None
            
        for pattern in self.name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up name
                name = re.sub(r'\s+', ' ', name)
                name = name.title()
                
                # Basic validation - should have at least 2 characters
                if len(name) > 2 and not name.lower().startswith('test'):
                    return name
        
        return None
    
    def _validate_name(self, extracted_name, expected_name):
        """Validate if names match using fuzzy matching"""
        # Normalize names
        name1 = extracted_name.lower().strip()
        name2 = expected_name.lower().strip()
        
        # Direct match
        if name1 == name2:
            return True, 1.0
        
        # Fuzzy match
        similarity = SequenceMatcher(None, name1, name2).ratio()
        
        # Check if one name contains the other (common with initials)
        if name1 in name2 or name2 in name1:
            return True, max(similarity, 0.8)
        
        # Threshold for acceptance
        if similarity > 0.85:
            return True, similarity
        
        return False, similarity
    
    def format_lab_report(self, lab_results):
        """Format lab results for display"""
        if not lab_results:
            return "No lab values detected"
        
        report = "**Detected Lab Values:**\n\n"
        
        # Group by category
        categories = {
            'Blood Counts': ['hemoglobin', 'wbc', 'rbc', 'platelets', 'neutrophils', 'lymphocytes', 'eosinophils', 'esr'],
            'Blood Sugar': ['glucose', 'hba1c'],
            'Kidney Function': ['creatinine', 'urea', 'uric_acid'],
            'Liver Function': ['sgpt', 'sgot', 'bilirubin', 'alkaline_phosphatase'],
            'Lipid Profile': ['cholesterol', 'triglycerides', 'hdl', 'ldl'],
            'Electrolytes': ['sodium', 'potassium', 'chloride'],
            'Thyroid': ['tsh', 't3', 't4'],
            'Others': ['crp', 'vitamin_d', 'vitamin_b12']
        }
        
        for category, tests in categories.items():
            category_results = {test: lab_results[test] for test in tests if test in lab_results}
            
            if category_results:
                report += f"\n**{category}:**\n"
                
                for test, data in category_results.items():
                    status_emoji = {
                        'normal': '✅',
                        'low': '⬇️',
                        'high': '⬆️',
                        'unknown': '❓'
                    }
                    
                    emoji = status_emoji.get(data['status'], '❓')
                    test_name = test.replace('_', ' ').title()
                    
                    report += f"{emoji} **{test_name}**: {data['value']} "
                    if data['status'] != 'normal' and data['status'] != 'unknown':
                        report += f"({data['status'].upper()})"
                    report += "\n"
        
        return report