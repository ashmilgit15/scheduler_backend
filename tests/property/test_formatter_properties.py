"""
Property-based tests for output formatter
"""
import pytest
from hypothesis import given, strategies as st, settings

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import ExamMetadata, Examiner, TimeSlot, LabSchedule, ScheduleResponse
from app.formatter import (
    format_schedule_response,
    schedule_to_json,
    schedule_from_json,
    validate_schedule_schema,
)
from app.scheduler import allocate_students


# Strategies for generating test data
text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=30
).filter(lambda x: x.strip() == x and len(x.strip()) > 0)

examiner_strategy = st.builds(
    Examiner,
    id=text_strategy,
    name=text_strategy
)

metadata_strategy = st.builds(
    ExamMetadata,
    exam_name=text_strategy,
    semester=text_strategy,
    department=text_strategy,
    academic_year=text_strategy
)


def generate_valid_schedule(num_students: int):
    """Generate a valid schedule for testing"""
    register_numbers = [f"REG{i:04d}" for i in range(num_students)]
    num_dates = (num_students // 125) + 2
    dates = [f"{(i % 28) + 1:02d}-01-25" for i in range(num_dates)]
    labs = [f"Lab {i+1}" for i in range(5)]
    return allocate_students(register_numbers, dates, labs)


class TestJSONRoundTrip:
    """
    **Feature: exam-scheduler, Property 12: Schedule JSON Round-Trip**
    **Validates: Requirements 6.3**
    
    For any valid schedule object, serializing to JSON and parsing back 
    should produce an equivalent schedule object.
    """

    @given(
        metadata=metadata_strategy,
        num_students=st.integers(min_value=25, max_value=200)
    )
    @settings(max_examples=50)
    def test_json_round_trip(self, metadata, num_students):
        """Serialize to JSON then parse should return equivalent object"""
        internal_examiners = [Examiner(id=f"INT{i}", name=f"Internal {i}") for i in range(6)]
        external_examiners = [Examiner(id=f"EXT{i}", name=f"External {i}") for i in range(5)]
        schedules = generate_valid_schedule(num_students)
        
        response = format_schedule_response(
            metadata, internal_examiners, external_examiners, schedules
        )
        
        # Round trip
        json_str = schedule_to_json(response)
        parsed = schedule_from_json(json_str)
        
        # Verify equivalence
        assert parsed.exam_metadata.exam_name == response.exam_metadata.exam_name
        assert parsed.exam_metadata.semester == response.exam_metadata.semester
        assert parsed.exam_metadata.department == response.exam_metadata.department
        assert parsed.exam_metadata.academic_year == response.exam_metadata.academic_year
        
        assert len(parsed.examiners["internal"]) == len(response.examiners["internal"])
        assert len(parsed.examiners["external"]) == len(response.examiners["external"])
        
        assert len(parsed.schedule) == len(response.schedule)
        for orig, parsed_sched in zip(response.schedule, parsed.schedule):
            assert parsed_sched.date == orig.date
            assert parsed_sched.lab == orig.lab
            assert len(parsed_sched.slots) == len(orig.slots)

    def test_specific_round_trip(self):
        """Test with specific known values"""
        metadata = ExamMetadata(
            exam_name="Computer Science Lab Exam",
            semester="S6",
            department="CSE",
            academic_year="2024-25"
        )
        internal_examiners = [Examiner(id=f"INT{i}", name=f"Dr. Internal {i}") for i in range(6)]
        external_examiners = [Examiner(id=f"EXT{i}", name=f"Dr. External {i}") for i in range(5)]
        schedules = generate_valid_schedule(50)
        
        response = format_schedule_response(
            metadata, internal_examiners, external_examiners, schedules
        )
        
        json_str = schedule_to_json(response)
        parsed = schedule_from_json(json_str)
        
        assert parsed.exam_metadata.exam_name == "Computer Science Lab Exam"
        assert len(parsed.schedule) == len(schedules)


class TestSchemaValidation:
    """
    **Feature: exam-scheduler, Property 13: Schedule Schema Validation**
    **Validates: Requirements 6.1, 6.2**
    
    For any generated schedule JSON, it should contain: exam_metadata object, 
    examiners object with internal and external arrays, and schedule array 
    where each entry has date, lab, and slots with time, session, capacity, 
    and register_numbers.
    """

    @given(
        metadata=metadata_strategy,
        num_students=st.integers(min_value=25, max_value=200)
    )
    @settings(max_examples=50)
    def test_schema_validation_passes(self, metadata, num_students):
        """Valid schedules should pass schema validation"""
        internal_examiners = [Examiner(id=f"INT{i}", name=f"Internal {i}") for i in range(6)]
        external_examiners = [Examiner(id=f"EXT{i}", name=f"External {i}") for i in range(5)]
        schedules = generate_valid_schedule(num_students)
        
        response = format_schedule_response(
            metadata, internal_examiners, external_examiners, schedules
        )
        
        errors = validate_schedule_schema(response)
        
        assert errors == [], f"Schema validation failed: {errors}"

    def test_schema_has_required_fields(self):
        """Verify all required fields are present"""
        metadata = ExamMetadata(
            exam_name="Test Exam",
            semester="S1",
            department="Test",
            academic_year="2024-25"
        )
        internal_examiners = [Examiner(id=f"INT{i}", name=f"Internal {i}") for i in range(6)]
        external_examiners = [Examiner(id=f"EXT{i}", name=f"External {i}") for i in range(5)]
        schedules = generate_valid_schedule(50)
        
        response = format_schedule_response(
            metadata, internal_examiners, external_examiners, schedules
        )
        
        # Check structure
        assert response.exam_metadata is not None
        assert response.examiners is not None
        assert "internal" in response.examiners
        assert "external" in response.examiners
        assert response.schedule is not None
        
        # Check schedule entries
        for sched in response.schedule:
            assert sched.date is not None
            assert sched.lab is not None
            assert len(sched.slots) == 2
            for slot in sched.slots:
                assert slot.time is not None
                assert slot.session in ["forenoon", "afternoon"]
                assert slot.capacity is not None
                assert slot.register_numbers is not None
