"""
Validation service for exam scheduler inputs
All validations are optional - the system will use defaults when values are not provided
"""
import math
from typing import List, Tuple, Optional
from datetime import datetime

from .models import ValidationError, ScheduleRequest


# Constants
MIN_REGISTER_NUMBERS = 1  # Minimum 1 student (was 25, now flexible)
DEFAULT_LABS = ["Lab 1", "Lab 2", "Lab 3", "Lab 4", "Lab 5"]
STUDENTS_PER_LAB = 25
LABS_PER_DAY = 5
DAILY_CAPACITY = STUDENTS_PER_LAB * LABS_PER_DAY  # 125


def calculate_required_dates(student_count: int) -> int:
    """
    Calculate minimum number of dates required for given student count.
    
    Args:
        student_count: Number of students to schedule
        
    Returns:
        Minimum number of dates required
    """
    if student_count <= 0:
        return 0
    return math.ceil(student_count / DAILY_CAPACITY)


def calculate_additional_dates_needed(student_count: int, provided_dates: int) -> int:
    """
    Calculate how many additional dates are needed.
    
    Args:
        student_count: Number of students to schedule
        provided_dates: Number of dates provided by user
        
    Returns:
        Number of additional dates needed (0 if sufficient)
    """
    required = calculate_required_dates(student_count)
    return max(0, required - provided_dates)


def validate_register_numbers(register_numbers: List[str]) -> Optional[ValidationError]:
    """
    Validate register numbers list - now optional, just needs at least 1 if provided.
    
    Args:
        register_numbers: List of register numbers
        
    Returns:
        ValidationError if invalid, None if valid
    """
    if not register_numbers:
        return ValidationError(
            field="register_numbers",
            message="At least one register number is required to generate a schedule"
        )
    
    return None


def validate_labs(labs: List[str]) -> Tuple[Optional[ValidationError], List[str]]:
    """
    Validate labs list - optional, returns defaults if not provided.
    
    Args:
        labs: List of lab names
        
    Returns:
        Tuple of (ValidationError if invalid, list of labs to use)
    """
    if not labs:
        # Return default labs
        return None, DEFAULT_LABS
    
    # Any number of labs is now acceptable
    return None, labs


def validate_internal_examiners(examiners: List) -> Optional[ValidationError]:
    """
    Validate internal examiners list - now optional.
    
    Args:
        examiners: List of internal examiners
        
    Returns:
        ValidationError if invalid, None if valid (empty is valid)
    """
    # Examiners are now optional - no validation error
    return None


def validate_external_examiners(examiners: List) -> Optional[ValidationError]:
    """
    Validate external examiners list - now optional.
    
    Args:
        examiners: List of external examiners
        
    Returns:
        ValidationError if invalid, None if valid (empty is valid)
    """
    # Examiners are now optional - no validation error
    return None


def validate_dates(dates: List[str], student_count: int) -> Tuple[Optional[ValidationError], Optional[str]]:
    """
    Validate dates list and check capacity - dates are optional but warned if insufficient.
    
    Args:
        dates: List of date strings
        student_count: Number of students to schedule
        
    Returns:
        Tuple of (ValidationError if invalid format, warning message if insufficient dates)
    """
    if not dates:
        # Dates are optional - will auto-generate if needed
        return None, "No dates provided. Please add exam dates for scheduling."
    
    # Validate date format
    for date_str in dates:
        try:
            datetime.strptime(date_str.strip(), '%d-%m-%y')
        except ValueError:
            return ValidationError(
                field="dates",
                message=f"Invalid date format: {date_str}. Expected DD-MM-YY"
            ), None
    
    # Check capacity - just warn, don't error
    additional_needed = calculate_additional_dates_needed(student_count, len(dates))
    if additional_needed > 0:
        required = calculate_required_dates(student_count)
        return None, f"Note: {student_count} students may need {required} dates. You provided {len(dates)}."
    
    return None, None


def validate_exam_metadata(metadata) -> Optional[ValidationError]:
    """
    Validate exam metadata - now optional.
    
    Args:
        metadata: ExamMetadata object
        
    Returns:
        ValidationError if invalid, None if valid (None metadata is valid)
    """
    # Metadata is now completely optional
    return None


def validate_schedule_request(request: ScheduleRequest) -> Tuple[List[ValidationError], List[str]]:
    """
    Validate complete schedule request - most fields are now optional.
    
    Args:
        request: ScheduleRequest object
        
    Returns:
        Tuple of (list of errors, list of warnings)
    """
    errors = []
    warnings = []
    
    # Validate metadata - optional, no error
    metadata_error = validate_exam_metadata(request.exam_metadata)
    if metadata_error:
        errors.append(metadata_error)
    
    # Validate register numbers - need at least 1
    reg_error = validate_register_numbers(request.register_numbers)
    if reg_error:
        errors.append(reg_error)
    
    # Validate labs - optional, use defaults
    labs_error, labs_to_use = validate_labs(request.labs)
    if labs_error:
        errors.append(labs_error)
    if not request.labs:
        warnings.append(f"Using default labs: {', '.join(DEFAULT_LABS)}")
        request.labs = labs_to_use
    
    # Validate examiners - optional
    internal_error = validate_internal_examiners(request.internal_examiners)
    if internal_error:
        errors.append(internal_error)
    if not request.internal_examiners:
        warnings.append("No internal examiners provided. Schedule will be generated without examiner assignments.")
    
    external_error = validate_external_examiners(request.external_examiners)
    if external_error:
        errors.append(external_error)
    if not request.external_examiners:
        warnings.append("No external examiners provided. Schedule will be generated without examiner assignments.")
    
    # Validate dates - optional but warn
    if request.register_numbers:
        dates_error, dates_warning = validate_dates(request.dates, len(request.register_numbers))
        if dates_error:
            errors.append(dates_error)
        if dates_warning:
            warnings.append(dates_warning)
    
    return errors, warnings
