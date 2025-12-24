"""
File parser for extracting semester and register number data from CSV/Excel files
and image analysis using Groq AI
"""
import re
import csv
import io
import base64
from typing import List, Dict, Optional, Tuple
import httpx


def parse_csv_content(content: str) -> List[Dict]:
    """
    Parse CSV content to extract semester and register number data.
    
    Expected formats:
    1. Simple list: one register number per line
    2. With semester: semester,batch,register_number
    3. With headers: Semester,Batch,Register Number
    
    Returns list of dicts with semester, batch, register_numbers
    """
    lines = content.strip().split('\n')
    if not lines:
        return []
    
    # Try to detect format
    first_line = lines[0].strip()
    
    # Check if it's a header row
    has_header = any(h.lower() in first_line.lower() for h in ['semester', 'batch', 'register', 'roll'])
    
    if has_header:
        lines = lines[1:]
    
    # Parse based on delimiter detection
    delimiter = ',' if ',' in first_line else '\t' if '\t' in first_line else None
    
    result = {}  # {semester: {batch: [register_numbers]}}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if delimiter:
            parts = [p.strip() for p in line.split(delimiter)]
            if len(parts) >= 3:
                # Format: semester, batch, register_number
                sem = parts[0].upper()
                batch = parts[1].upper()
                reg_no = parts[2]
            elif len(parts) == 2:
                # Format: semester, register_number (assume batch A)
                sem = parts[0].upper()
                batch = 'A'
                reg_no = parts[1]
            else:
                # Single column - just register number
                sem = 'S1'
                batch = 'A'
                reg_no = parts[0]
        else:
            # No delimiter - just register numbers
            sem = 'S1'
            batch = 'A'
            reg_no = line
        
        # Normalize semester name
        if not sem.startswith('S'):
            sem = f'S{sem}'
        
        if sem not in result:
            result[sem] = {}
        if batch not in result[sem]:
            result[sem][batch] = []
        
        if reg_no and reg_no not in result[sem][batch]:
            result[sem][batch].append(reg_no)
    
    # Convert to list format
    semesters = []
    for sem_name, batches in sorted(result.items()):
        semester = {
            'name': sem_name,
            'batches': [
                {'name': batch_name, 'register_numbers': reg_nums}
                for batch_name, reg_nums in sorted(batches.items())
            ]
        }
        semesters.append(semester)
    
    return semesters


def extract_register_numbers_from_text(text: str) -> Tuple[List[Dict], List[str]]:
    """
    Extract register numbers and semester info from raw text.
    Uses pattern matching to find register numbers.
    
    Returns (semesters, raw_register_numbers)
    """
    # Common register number patterns
    # KTU format: TVE20CS001, ABC21EC123, etc.
    reg_pattern = r'\b[A-Z]{2,4}\d{2}[A-Z]{2,3}\d{3}\b'
    
    # Find all register numbers
    register_numbers = re.findall(reg_pattern, text.upper())
    
    # Try to detect semester info
    semester_pattern = r'(?:semester|sem)[:\s]*([S]?\d+)'
    batch_pattern = r'(?:batch|division|div)[:\s]*([A-Z])'
    
    sem_match = re.search(semester_pattern, text, re.IGNORECASE)
    batch_match = re.search(batch_pattern, text, re.IGNORECASE)
    
    semester = sem_match.group(1) if sem_match else 'S1'
    if not semester.startswith('S'):
        semester = f'S{semester}'
    
    batch = batch_match.group(1).upper() if batch_match else 'A'
    
    if register_numbers:
        semesters = [{
            'name': semester,
            'batches': [{'name': batch, 'register_numbers': list(set(register_numbers))}]
        }]
        return semesters, register_numbers
    
    return [], []


async def analyze_image_with_groq(
    image_base64: str,
    api_key: str,
    mime_type: str = "image/png"
) -> Optional[str]:
    """
    Use Groq AI to analyze an image and extract register numbers.
    
    Args:
        image_base64: Base64 encoded image
        api_key: Groq API key (from server environment)
        mime_type: Image MIME type
        
    Returns:
        Extracted text from image or None on error
    """
    # Models to try in order of preference
    models_to_try = [
        "meta-llama/llama-4-maverick-17b-128e-instruct",  # Primary: User requested model
        "openai/gpt-oss-120b",              # Fallback: GPT model
        "llama-3.3-70b-versatile",          # Fallback: Versatile model
        "llama-4-scout-17b-16e-instruct",   # Fallback: Vision model
        "llama-3.2-11b-vision-preview",     # Fallback: Smaller vision model
        "llama-3.2-90b-vision-preview",     # Fallback: Larger vision model
    ]
    
    for model in models_to_try:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": """Analyze this image and extract ALL possible information related to an exam schedule. Use your intelligence to identify and organize the data.

Extract the following if present:
1. EXAM_NAME: Name of the exam/test
2. DEPARTMENT: Department or branch name
3. SEMESTER: Semester (e.g., S1, S2, S3, S4, S5, S6, S7, S8)
4. BATCH: Batch/Division (e.g., A, B, C)
5. ACADEMIC_YEAR: Academic year (e.g., 2024-25)
6. DATES: Any exam dates mentioned (format: DD-MM-YY)
7. LABS: Lab names or room numbers
8. INTERNAL_EXAMINERS: Names and IDs of internal examiners
9. EXTERNAL_EXAMINERS: Names and IDs of external examiners
10. REGISTER_NUMBERS: Student register numbers (patterns like TVE20CS001, ABC21EC123)
11. SUBJECTS: Subject names
12. TIME_SLOTS: Time slots mentioned

Output in this exact format (leave blank if not found):
EXAM_NAME: [exam name]
DEPARTMENT: [department]
SEMESTER: [semester]
BATCH: [batch]
ACADEMIC_YEAR: [year]
DATES:
[list each date on new line in DD-MM-YY format]
LABS:
[list each lab on new line]
INTERNAL_EXAMINERS:
[ID: Name format, one per line]
EXTERNAL_EXAMINERS:
[ID: Name format, one per line]
SUBJECTS:
[list each subject on new line]
REGISTER_NUMBERS:
[list each register number on new line]
RAW_TEXT:
[any other text you can see that might be useful]

Be thorough and extract everything you can see. If you're unsure about something, include it anyway with a note."""
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{mime_type};base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 8192
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status_code == 400 and "model" in response.text.lower():
                    # Model not available, try next one
                    print(f"Model {model} not available, trying next...")
                    continue
                else:
                    print(f"Groq API error with {model}: {response.status_code} - {response.text}")
                    # Try next model on error
                    continue
                    
        except Exception as e:
            print(f"Error calling Groq API with {model}: {e}")
            continue
    
    # All models failed
    return None


def parse_groq_response(response: str) -> Tuple[List[Dict], List[str], Dict]:
    """
    Parse Groq AI response to extract all exam-related data.
    Returns (semesters, register_numbers, extracted_data).
    """
    lines = response.strip().split('\n')
    
    # Initialize extracted data
    extracted_data = {
        'exam_name': '',
        'department': '',
        'semester': 'S1',
        'batch': 'A',
        'academic_year': '',
        'dates': [],
        'labs': [],
        'internal_examiners': [],
        'external_examiners': [],
        'subjects': [],
        'register_numbers': [],
        'raw_text': ''
    }
    
    current_section = None
    seen_numbers = set()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for section headers
        if line.upper().startswith('EXAM_NAME:'):
            extracted_data['exam_name'] = line.split(':', 1)[1].strip()
            current_section = None
        elif line.upper().startswith('DEPARTMENT:'):
            extracted_data['department'] = line.split(':', 1)[1].strip()
            current_section = None
        elif line.upper().startswith('SEMESTER:'):
            sem_val = line.split(':', 1)[1].strip()
            if sem_val:
                extracted_data['semester'] = sem_val.upper() if sem_val.upper().startswith('S') else f'S{sem_val}'
            current_section = None
        elif line.upper().startswith('BATCH:'):
            batch_val = line.split(':', 1)[1].strip()
            if batch_val:
                extracted_data['batch'] = batch_val[0].upper()
            current_section = None
        elif line.upper().startswith('ACADEMIC_YEAR:'):
            extracted_data['academic_year'] = line.split(':', 1)[1].strip()
            current_section = None
        elif line.upper().startswith('DATES:'):
            current_section = 'dates'
        elif line.upper().startswith('LABS:'):
            current_section = 'labs'
        elif line.upper().startswith('INTERNAL_EXAMINERS:'):
            current_section = 'internal_examiners'
        elif line.upper().startswith('EXTERNAL_EXAMINERS:'):
            current_section = 'external_examiners'
        elif line.upper().startswith('SUBJECTS:'):
            current_section = 'subjects'
        elif line.upper().startswith('REGISTER_NUMBERS:'):
            current_section = 'register_numbers'
        elif line.upper().startswith('RAW_TEXT:'):
            current_section = 'raw_text'
        elif current_section:
            # Process line based on current section
            cleaned = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
            if not cleaned:
                continue
                
            if current_section == 'dates':
                # Try to extract date in DD-MM-YY format
                date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', cleaned)
                if date_match:
                    extracted_data['dates'].append(date_match.group().replace('/', '-'))
                elif cleaned:
                    extracted_data['dates'].append(cleaned)
            elif current_section == 'labs':
                if cleaned:
                    extracted_data['labs'].append(cleaned)
            elif current_section == 'internal_examiners':
                # Parse ID: Name format
                if ':' in cleaned:
                    parts = cleaned.split(':', 1)
                    extracted_data['internal_examiners'].append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip()
                    })
                elif cleaned:
                    extracted_data['internal_examiners'].append({
                        'id': f'INT{len(extracted_data["internal_examiners"])+1}',
                        'name': cleaned
                    })
            elif current_section == 'external_examiners':
                if ':' in cleaned:
                    parts = cleaned.split(':', 1)
                    extracted_data['external_examiners'].append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip()
                    })
                elif cleaned:
                    extracted_data['external_examiners'].append({
                        'id': f'EXT{len(extracted_data["external_examiners"])+1}',
                        'name': cleaned
                    })
            elif current_section == 'subjects':
                if cleaned:
                    extracted_data['subjects'].append(cleaned)
            elif current_section == 'register_numbers':
                # Match register number pattern
                match = re.search(r'[A-Z]{2,4}\d{2}[A-Z]{2,3}\d{3}', cleaned.upper())
                if match:
                    num = match.group()
                    if num not in seen_numbers:
                        extracted_data['register_numbers'].append(num)
                        seen_numbers.add(num)
            elif current_section == 'raw_text':
                extracted_data['raw_text'] += cleaned + '\n'
    
    # Also try to find any register numbers in the entire response
    all_matches = re.findall(r'\b[A-Z]{2,4}\d{2}[A-Z]{2,3}\d{3}\b', response.upper())
    for match in all_matches:
        if match not in seen_numbers:
            extracted_data['register_numbers'].append(match)
            seen_numbers.add(match)
    
    # Build semesters structure
    semesters = []
    if extracted_data['register_numbers']:
        semesters = [{
            'name': extracted_data['semester'],
            'batches': [{'name': extracted_data['batch'], 'register_numbers': extracted_data['register_numbers']}]
        }]
    
    return semesters, extracted_data['register_numbers'], extracted_data
