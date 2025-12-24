"""
Property-based tests for validators
Note: Many validations are now optional, so tests focus on the remaining required validations
"""
import pytest
import math
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.validators import (
    calculate_required_dates,
    calculate_additional_dates_needed,
    validate_register_numbers,
    validate_labs,
    validate_dates,
    DAILY_CAPACITY,
    MIN_REGISTER_NUMBERS,
    DEFAULT_LABS,
)
from app.models import Examiner


class TestDateCapacityCalculation:
    """
    **Feature: exam-scheduler, Property 5: Date Capacity Calculation**
    **Validates: Requirements 2.2**
    
    For any student count and date count, the system should correctly calculate 
    additional dates needed as: max(0, ceil(students / 125) - dates).
    """

    @given(
        student_count=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100)
    def test_required_dates_formula(self, student_count):
        """Required dates should equal ceil(students / 125)"""
        expected = math.ceil(student_count / DAILY_CAPACITY)
        actual = calculate_required_dates(student_count)
        
        assert actual == expected

    @given(
        student_count=st.integers(min_value=1, max_value=1000),
        provided_dates=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100)
    def test_additional_dates_formula(self, student_count, provided_dates):
        """Additional dates should equal max(0, required - provided)"""
        required = math.ceil(student_count / DAILY_CAPACITY)
        expected = max(0, required - provided_dates)
        actual = calculate_additional_dates_needed(student_count, provided_dates)
        
        assert actual == expected

    @given(
        student_count=st.integers(min_value=1, max_value=1000),
        extra_dates=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100)
    def test_sufficient_dates_returns_zero(self, student_count, extra_dates):
        """When dates are sufficient, additional needed should be 0"""
        required = calculate_required_dates(student_count)
        # Provide exactly enough or more dates
        provided = required + extra_dates
        
        additional = calculate_additional_dates_needed(student_count, provided)
        
        assert additional == 0

    @given(
        student_count=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100)
    def test_capacity_constraint(self, student_count):
        """Required dates * capacity should be >= student count"""
        required = calculate_required_dates(student_count)
        
        assert required * DAILY_CAPACITY >= student_count


class TestValidationErrors:
    """
    **Feature: exam-scheduler, Property 14: Validation Errors for Invalid Inputs**
    **Validates: Requirements 10.1, 10.2**
    
    For any input with missing required fields, the system should return 
    a validation error identifying the specific missing field.
    
    Note: Most fields are now optional. Only register_numbers requires at least 1.
    """

    def test_empty_register_numbers_error(self):
        """Empty register numbers should return error (need at least 1)"""
        error = validate_register_numbers([])
        
        assert error is not None
        assert error.field == "register_numbers"
        assert "required" in error.message.lower() or "at least" in error.message.lower()

    @given(
        count=st.integers(min_value=MIN_REGISTER_NUMBERS, max_value=500)
    )
    @settings(max_examples=100)
    def test_sufficient_register_numbers_no_error(self, count):
        """Register numbers at or above minimum should not return error"""
        register_numbers = [f"REG{i:03d}" for i in range(count)]
        
        error = validate_register_numbers(register_numbers)
        
        assert error is None

    def test_empty_labs_returns_defaults(self):
        """Empty labs list should return default labs (not an error)"""
        error, labs = validate_labs([])
        
        # No error - defaults are used
        assert error is None
        assert labs == DEFAULT_LABS

    @given(
        count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_any_lab_count_accepted(self, count):
        """Any number of labs should be accepted (flexible)"""
        labs = [f"Lab {i+1}" for i in range(count)]
        
        error, returned_labs = validate_labs(labs)
        
        assert error is None
        assert returned_labs == labs

    def test_empty_dates_returns_warning(self):
        """Empty dates list should return warning (not error)"""
        error, warning = validate_dates([], 100)
        
        # No error for empty dates - just a warning
        assert error is None
        assert warning is not None
        assert "no dates" in warning.lower() or "add" in warning.lower()

    @given(
        student_count=st.integers(min_value=126, max_value=500)
    )
    @settings(max_examples=100)
    def test_insufficient_dates_returns_warning(self, student_count):
        """Insufficient dates for student count should return warning (not error)"""
        # Provide only 1 date for more than 125 students
        dates = ["01-01-25"]
        
        error, warning = validate_dates(dates, student_count)
        
        # No error - just a warning about capacity
        assert error is None
        assert warning is not None

    def test_invalid_date_format_returns_error(self):
        """Invalid date format should return error"""
        dates = ["2025-01-01"]  # Wrong format (should be DD-MM-YY)
        
        error, _ = validate_dates(dates, 100)
        
        assert error is not None
        assert error.field == "dates"
        assert "format" in error.message.lower() or "invalid" in error.message.lower()

    def test_valid_date_format_no_error(self):
        """Valid date format should not return error"""
        dates = ["01-01-25", "02-01-25"]
        
        error, _ = validate_dates(dates, 100)
        
        assert error is None
