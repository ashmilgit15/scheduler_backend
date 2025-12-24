"""
Output formatter for schedule generation
"""
import json
from typing import List, Dict, Any

from .models import (
    ExamMetadata,
    Examiner,
    LabSchedule,
    ScheduleResponse,
)


def format_schedule_response(
    exam_metadata: ExamMetadata,
    internal_examiners: List[Examiner],
    external_examiners: List[Examiner],
    schedules: List[LabSchedule]
) -> ScheduleResponse:
    """
    Format the complete schedule response.
    All fields are optional - will use empty defaults if not provided.
    
    Args:
        exam_metadata: Exam metadata (optional)
        internal_examiners: List of internal examiners (optional)
        external_examiners: List of external examiners (optional)
        schedules: List of lab schedules
        
    Returns:
        ScheduleResponse object
    """
    return ScheduleResponse(
        exam_metadata=exam_metadata,
        examiners={
            "internal": internal_examiners or [],
            "external": external_examiners or []
        },
        schedule=schedules or []
    )


def schedule_to_json(response: ScheduleResponse) -> str:
    """
    Convert schedule response to JSON string.
    
    Args:
        response: ScheduleResponse object
        
    Returns:
        JSON string
    """
    return response.model_dump_json(indent=2)


def schedule_from_json(json_str: str) -> ScheduleResponse:
    """
    Parse schedule response from JSON string.
    
    Args:
        json_str: JSON string
        
    Returns:
        ScheduleResponse object
    """
    data = json.loads(json_str)
    return ScheduleResponse.model_validate(data)


def validate_schedule_schema(response: ScheduleResponse) -> List[str]:
    """
    Validate that schedule response has required fields.
    Now more lenient - only checks for schedule array with proper structure.
    
    Args:
        response: ScheduleResponse object
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # exam_metadata is now optional - no validation
    # examiners are now optional - no validation
    
    # Check schedule - this is the only required part
    if response.schedule:
        for i, lab_schedule in enumerate(response.schedule):
            if not lab_schedule.date:
                errors.append(f"Missing schedule[{i}].date")
            if not lab_schedule.lab:
                errors.append(f"Missing schedule[{i}].lab")
            if not lab_schedule.slots or len(lab_schedule.slots) != 2:
                errors.append(f"schedule[{i}] should have exactly 2 slots")
            else:
                for j, slot in enumerate(lab_schedule.slots):
                    if not slot.time:
                        errors.append(f"Missing schedule[{i}].slots[{j}].time")
                    if not slot.session:
                        errors.append(f"Missing schedule[{i}].slots[{j}].session")
                    if slot.capacity is None:
                        errors.append(f"Missing schedule[{i}].slots[{j}].capacity")
                    if slot.register_numbers is None:
                        errors.append(f"Missing schedule[{i}].slots[{j}].register_numbers")
    
    return errors
