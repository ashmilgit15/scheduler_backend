"""
Property-based tests for scheduling algorithm
"""
import pytest
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.scheduler import (
    allocate_students,
    get_all_register_numbers,
    count_students_per_date,
    count_students_per_lab,
    STUDENTS_PER_LAB,
    FORENOON_CAPACITY,
    AFTERNOON_CAPACITY,
    DAILY_CAPACITY,
)


# Strategy for generating register numbers
register_number_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=3,
    max_size=15
).filter(lambda x: x.strip() == x and len(x) > 0)

# Strategy for generating dates in DD-MM-YY format
date_strategy = st.dates(
    min_value=__import__('datetime').date(2024, 1, 1),
    max_value=__import__('datetime').date(2026, 12, 31)
).map(lambda d: d.strftime('%d-%m-%y'))

# Strategy for lab names
lab_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=3,
    max_size=20
).filter(lambda x: x.strip() == x and len(x) > 0)


def generate_test_data(num_students: int, num_dates: int):
    """Helper to generate test data"""
    register_numbers = [f"REG{i:04d}" for i in range(num_students)]
    dates = [f"{(i % 28) + 1:02d}-01-25" for i in range(num_dates)]
    labs = [f"Lab {i+1}" for i in range(5)]
    return register_numbers, dates, labs


class TestMaxStudentsPerLab:
    """
    **Feature: exam-scheduler, Property 7: Maximum 25 Students Per Lab Per Day**
    **Validates: Requirements 4.2, 5.1**
    
    For any generated schedule, every lab on every date should have 
    at most 25 students assigned.
    """

    @given(
        num_students=st.integers(min_value=25, max_value=500)
    )
    @settings(max_examples=100)
    def test_max_25_students_per_lab(self, num_students):
        """Each lab should have at most 25 students"""
        num_dates = (num_students // DAILY_CAPACITY) + 2  # Ensure enough dates
        register_numbers, dates, labs = generate_test_data(num_students, num_dates)
        
        schedules = allocate_students(register_numbers, dates, labs)
        
        for schedule in schedules:
            total_in_lab = sum(len(slot.register_numbers) for slot in schedule.slots)
            assert total_in_lab <= STUDENTS_PER_LAB, \
                f"Lab {schedule.lab} on {schedule.date} has {total_in_lab} students, max is {STUDENTS_PER_LAB}"


class TestSlotDistribution:
    """
    **Feature: exam-scheduler, Property 8: Slot Distribution 13+12**
    **Validates: Requirements 5.2**
    
    For any generated schedule with a full lab (25 students), the forenoon slot 
    should have exactly 13 students and the afternoon slot should have exactly 12 students.
    For partial labs, forenoon fills first (up to 13), then afternoon (up to 12).
    """

    @given(
        num_students=st.integers(min_value=25, max_value=500)
    )
    @settings(max_examples=100)
    def test_slot_distribution(self, num_students):
        """Forenoon should have up to 13, afternoon up to 12"""
        num_dates = (num_students // DAILY_CAPACITY) + 2
        register_numbers, dates, labs = generate_test_data(num_students, num_dates)
        
        schedules = allocate_students(register_numbers, dates, labs)
        
        for schedule in schedules:
            forenoon = schedule.slots[0]
            afternoon = schedule.slots[1]
            
            # Forenoon should have at most 13
            assert len(forenoon.register_numbers) <= FORENOON_CAPACITY, \
                f"Forenoon has {len(forenoon.register_numbers)}, max is {FORENOON_CAPACITY}"
            
            # Afternoon should have at most 12
            assert len(afternoon.register_numbers) <= AFTERNOON_CAPACITY, \
                f"Afternoon has {len(afternoon.register_numbers)}, max is {AFTERNOON_CAPACITY}"
            
            # If afternoon has students, forenoon should be full (13)
            if len(afternoon.register_numbers) > 0:
                assert len(forenoon.register_numbers) == FORENOON_CAPACITY, \
                    f"Forenoon should be full ({FORENOON_CAPACITY}) before afternoon gets students"

    def test_full_lab_exact_distribution(self):
        """A full lab should have exactly 13 + 12 = 25"""
        register_numbers, dates, labs = generate_test_data(25, 1)
        
        schedules = allocate_students(register_numbers, dates, labs)
        
        assert len(schedules) == 1
        schedule = schedules[0]
        
        assert len(schedule.slots[0].register_numbers) == FORENOON_CAPACITY
        assert len(schedule.slots[1].register_numbers) == AFTERNOON_CAPACITY


class TestMaxStudentsPerDay:
    """
    **Feature: exam-scheduler, Property 9: Maximum 125 Students Per Day**
    **Validates: Requirements 5.3**
    
    For any generated schedule, no single date should have more than 
    125 students assigned across all labs.
    """

    @given(
        num_students=st.integers(min_value=25, max_value=500)
    )
    @settings(max_examples=100)
    def test_max_125_students_per_day(self, num_students):
        """Each date should have at most 125 students"""
        num_dates = (num_students // DAILY_CAPACITY) + 2
        register_numbers, dates, labs = generate_test_data(num_students, num_dates)
        
        schedules = allocate_students(register_numbers, dates, labs)
        date_counts = count_students_per_date(schedules)
        
        for date, count in date_counts.items():
            assert count <= DAILY_CAPACITY, \
                f"Date {date} has {count} students, max is {DAILY_CAPACITY}"


class TestNoDuplicatesInOutput:
    """
    **Feature: exam-scheduler, Property 10: No Duplicate Register Numbers in Output**
    **Validates: Requirements 5.5**
    
    For any generated schedule, the set of all register numbers in the output 
    should equal the set of input register numbers, and the total count should match.
    """

    @given(
        num_students=st.integers(min_value=25, max_value=500)
    )
    @settings(max_examples=100)
    def test_no_duplicates_all_present(self, num_students):
        """All input register numbers should appear exactly once in output"""
        num_dates = (num_students // DAILY_CAPACITY) + 2
        register_numbers, dates, labs = generate_test_data(num_students, num_dates)
        
        schedules = allocate_students(register_numbers, dates, labs)
        output_numbers = get_all_register_numbers(schedules)
        
        # Same set of numbers
        assert set(output_numbers) == set(register_numbers), \
            "Output should contain exactly the same register numbers as input"
        
        # Same count (no duplicates)
        assert len(output_numbers) == len(register_numbers), \
            f"Output has {len(output_numbers)} numbers, input has {len(register_numbers)}"


class TestInputOrderPreserved:
    """
    **Feature: exam-scheduler, Property 11: Input Order Preserved**
    **Validates: Requirements 5.6**
    
    For any generated schedule, flattening all register numbers in schedule order 
    should produce the original input list in the same order.
    """

    @given(
        num_students=st.integers(min_value=25, max_value=500)
    )
    @settings(max_examples=100)
    def test_input_order_preserved(self, num_students):
        """Register numbers should appear in same order as input"""
        num_dates = (num_students // DAILY_CAPACITY) + 2
        register_numbers, dates, labs = generate_test_data(num_students, num_dates)
        
        schedules = allocate_students(register_numbers, dates, labs)
        output_numbers = get_all_register_numbers(schedules)
        
        assert output_numbers == register_numbers, \
            "Output order should match input order"

    def test_specific_order_example(self):
        """Verify specific ordering with known input"""
        register_numbers = [f"STU{i:03d}" for i in range(50)]
        dates = ["01-01-25", "02-01-25"]
        labs = [f"Lab {i+1}" for i in range(5)]
        
        schedules = allocate_students(register_numbers, dates, labs)
        output_numbers = get_all_register_numbers(schedules)
        
        assert output_numbers == register_numbers
