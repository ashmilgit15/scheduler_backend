from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Groq API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from .models import (
    ScheduleRequest,
    ScheduleResponse,
    ApiResponse,
    ValidationError,
    Examiner,
)
from .validators import validate_schedule_request
from .parsers import parse_dates, remove_duplicates
from .scheduler import allocate_students, select_optimal_dates, auto_schedule_dates, DAILY_CAPACITY
from .formatter import format_schedule_response
from .file_parser import (
    parse_csv_content,
    extract_register_numbers_from_text,
    analyze_image_with_groq,
    parse_groq_response
)

app = FastAPI(
    title="Exam Scheduler API",
    description="AI-Driven Practical Exam Scheduler for Engineering Colleges",
    version="1.0.0"
)

# CORS configuration for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for deployment flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "exam-scheduler"}


@app.post("/api/schedule/generate", response_model=ApiResponse)
def generate_schedule(request: ScheduleRequest):
    """
    Generate exam schedule from inputs.
    
    Validates inputs, removes duplicates, sorts dates, and generates
    the complete schedule allocation.
    """
    warnings = []
    
    # Get all register numbers (from semesters or legacy field)
    all_register_numbers = request.get_all_register_numbers()
    
    # Remove duplicates from register numbers
    unique_numbers, duplicates = remove_duplicates(all_register_numbers)
    if duplicates:
        warnings.append(f"Duplicate register numbers removed: {', '.join(duplicates[:10])}" + 
                       (f" and {len(duplicates) - 10} more" if len(duplicates) > 10 else ""))
    
    # Update request with unique numbers
    request.register_numbers = unique_numbers
    
    # Get dates (from exam_dates or legacy dates field)
    dates = request.get_dates()
    
    # Sort dates chronologically
    dates = parse_dates(dates)
    request.dates = dates
    
    # Build date to subject mapping and date to register numbers mapping
    date_subjects = {}
    date_register_numbers = {}
    for ed in request.exam_dates:
        if ed.subject:
            date_subjects[ed.date] = ed.subject
        if ed.register_numbers:
            date_register_numbers[ed.date] = ed.register_numbers
    
    # Validate inputs
    errors, validation_warnings = validate_schedule_request(request)
    warnings.extend(validation_warnings)
    
    if errors:
        return ApiResponse(
            success=False,
            errors=errors,
            warnings=warnings
        )
    
    # Generate schedule with examiner assignments
    schedules = allocate_students(
        request.register_numbers,
        dates,
        request.labs,
        internal_examiners=[e.model_dump() for e in request.internal_examiners],
        external_examiners=[e.model_dump() for e in request.external_examiners],
        semesters=[s.model_dump() for s in request.semesters] if request.semesters else None,
        date_subjects=date_subjects,
        date_register_numbers=date_register_numbers if date_register_numbers else None
    )
    
    # Format response
    response = format_schedule_response(
        request.exam_metadata,
        request.internal_examiners,
        request.external_examiners,
        schedules
    )
    
    return ApiResponse(
        success=True,
        data=response,
        warnings=warnings
    )


@app.post("/api/schedule/validate")
def validate_schedule(request: ScheduleRequest):
    """
    Validate schedule inputs without generating.
    
    Returns validation errors and warnings.
    """
    warnings = []
    
    # Get all register numbers
    all_register_numbers = request.get_all_register_numbers()
    
    # Check for duplicates
    unique_numbers, duplicates = remove_duplicates(all_register_numbers)
    if duplicates:
        warnings.append(f"Duplicate register numbers found: {', '.join(duplicates[:10])}" + 
                       (f" and {len(duplicates) - 10} more" if len(duplicates) > 10 else ""))
    
    # Update for validation
    request.register_numbers = unique_numbers
    
    # Validate
    errors, validation_warnings = validate_schedule_request(request)
    warnings.extend(validation_warnings)
    
    return {
        "success": len(errors) == 0,
        "errors": [{"field": e.field, "message": e.message} for e in errors],
        "warnings": warnings,
        "summary": {
            "total_students": len(unique_numbers),
            "duplicates_found": len(duplicates),
            "dates_provided": len(request.dates),
            "labs_provided": len(request.labs),
            "internal_examiners": len(request.internal_examiners),
            "external_examiners": len(request.external_examiners),
            "semesters": len(request.semesters) if request.semesters else 0
        }
    }



@app.post("/api/upload/parse-file")
async def parse_uploaded_file(file: UploadFile = File(...)):
    """
    Parse uploaded CSV/TXT file to extract semester and register number data.
    
    Supports:
    - CSV with columns: semester, batch, register_number
    - Plain text with register numbers (one per line)
    - Auto-detection of semester/batch from content
    """
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Try CSV parsing first
        if file.filename and (file.filename.endswith('.csv') or ',' in text_content):
            semesters = parse_csv_content(text_content)
        else:
            # Try text extraction
            semesters, _ = extract_register_numbers_from_text(text_content)
        
        if not semesters:
            # Fallback: treat as simple list
            lines = text_content.strip().split('\n')
            register_numbers = [line.strip() for line in lines if line.strip()]
            if register_numbers:
                semesters = [{
                    'name': 'S1',
                    'batches': [{'name': 'A', 'register_numbers': register_numbers}]
                }]
        
        total_students = sum(
            len(batch['register_numbers'])
            for sem in semesters
            for batch in sem['batches']
        )
        
        return {
            "success": True,
            "semesters": semesters,
            "total_students": total_students,
            "message": f"Extracted {total_students} register numbers from {len(semesters)} semester(s)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "semesters": [],
            "total_students": 0
        }


@app.post("/api/upload/analyze-image")
async def analyze_image(
    file: UploadFile = File(...)
):
    """
    Analyze an image using Groq AI to extract all exam-related data.
    
    The API key is read from GROQ_API_KEY environment variable.
    No API key input required from frontend.
    
    Returns comprehensive extracted data including:
    - Register numbers
    - Exam metadata (name, department, semester, etc.)
    - Dates, labs, examiners, subjects
    """
    # Check if API key is configured
    if not GROQ_API_KEY:
        return {
            "success": False,
            "error": "Groq API key not configured on server. Please contact administrator.",
            "semesters": [],
            "extracted_data": None,
            "raw_response": None
        }
    
    try:
        content = await file.read()
        image_base64 = base64.b64encode(content).decode('utf-8')
        
        # Determine MIME type
        mime_type = file.content_type or "image/png"
        
        # Validate image format
        valid_types = ["image/png", "image/jpeg", "image/jpg"]
        if mime_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid image format. Supported formats: PNG, JPG, JPEG. Got: {mime_type}",
                "semesters": [],
                "extracted_data": None,
                "raw_response": None
            }
        
        # Call Groq AI with server-side API key
        response_text = await analyze_image_with_groq(image_base64, GROQ_API_KEY, mime_type)
        
        if not response_text:
            return {
                "success": False,
                "error": "Failed to analyze image with Groq AI. Please try again or use a different image.",
                "semesters": [],
                "extracted_data": None,
                "raw_response": None
            }
        
        # Parse the response - now returns extracted_data too
        semesters, register_numbers, extracted_data = parse_groq_response(response_text)
        
        total_students = len(register_numbers)
        
        return {
            "success": True,
            "semesters": semesters,
            "total_students": total_students,
            "extracted_data": extracted_data,
            "raw_response": response_text,
            "message": f"Extracted {total_students} register numbers and additional exam data using AI"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error processing image: {str(e)}",
            "semesters": [],
            "extracted_data": None,
            "raw_response": None
        }



@app.post("/api/schedule/auto-select-dates")
def auto_select_dates(
    available_dates: List[str],
    student_count: int,
    min_gap_days: int = 1,
    subjects: Optional[List[str]] = None
):
    """
    Automatically select optimal dates from available dates.
    
    The algorithm:
    1. Calculates how many days are needed (125 students per day)
    2. Selects dates with the specified minimum gap
    3. Returns selected dates with optional subject assignments
    
    Args:
        available_dates: List of available dates in DD-MM-YY format
        student_count: Total number of students
        min_gap_days: Minimum gap between exam days (default 1)
        subjects: Optional list of subjects to assign to dates
    """
    try:
        # Parse and sort dates
        sorted_dates = parse_dates(available_dates)
        
        # Calculate requirements
        import math
        required_days = math.ceil(student_count / DAILY_CAPACITY)
        
        # Select optimal dates
        selected_dates, message = select_optimal_dates(
            sorted_dates, 
            student_count, 
            min_gap_days
        )
        
        # Build exam dates with subjects
        exam_dates = []
        for i, date in enumerate(selected_dates):
            exam_dates.append({
                'date': date,
                'subject': subjects[i] if subjects and i < len(subjects) else None,
                'register_numbers': []
            })
        
        return {
            "success": True,
            "selected_dates": selected_dates,
            "exam_dates": exam_dates,
            "required_days": required_days,
            "available_days": len(available_dates),
            "students_per_day": DAILY_CAPACITY,
            "message": message,
            "schedule_info": {
                "total_students": student_count,
                "days_needed": required_days,
                "days_selected": len(selected_dates),
                "min_gap_requested": min_gap_days
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "selected_dates": [],
            "exam_dates": []
        }


@app.post("/api/schedule/calculate-requirements")
def calculate_requirements(student_count: int, available_dates: int = 0):
    """
    Calculate scheduling requirements based on student count.
    
    Returns:
        - Required number of days
        - Students per day capacity
        - Whether available dates are sufficient
    """
    import math
    required_days = math.ceil(student_count / DAILY_CAPACITY)
    
    return {
        "student_count": student_count,
        "daily_capacity": DAILY_CAPACITY,
        "required_days": required_days,
        "available_dates": available_dates,
        "dates_sufficient": available_dates >= required_days if available_dates > 0 else None,
        "additional_dates_needed": max(0, required_days - available_dates) if available_dates > 0 else None
    }
