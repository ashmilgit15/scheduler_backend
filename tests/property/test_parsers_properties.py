"""
Property-based tests for parsers
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.parsers import (
    parse_register_numbers,
    format_register_numbers,
    parse_csv_register_numbers,
    format_csv_register_numbers,
    remove_duplicates,
    parse_dates,
)


# Strategy for valid register numbers (alphanumeric, no special chars that break parsing)
register_number_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
).filter(lambda x: x.strip() == x and len(x) > 0)


class TestRegisterNumberParsingRoundTrip:
    """
    **Feature: exam-scheduler, Property 1: Register Number Parsing Round-Trip**
    **Validates: Requirements 1.5**
    
    For any list of valid register numbers, formatting them as a string 
    and parsing back should produce an equivalent list.
    """

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=50,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_register_number_round_trip(self, register_numbers):
        """Format then parse should return equivalent list"""
        formatted = format_register_numbers(register_numbers)
        parsed = parse_register_numbers(formatted)
        
        assert parsed == register_numbers


class TestCSVParsingRoundTrip:
    """
    **Feature: exam-scheduler, Property 2: CSV Parsing Round-Trip**
    **Validates: Requirements 1.2**
    
    For any list of valid register numbers, serializing to CSV format 
    and parsing back should produce an equivalent list.
    """

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=50,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_csv_round_trip(self, register_numbers):
        """CSV format then parse should return equivalent list"""
        csv_content = format_csv_register_numbers(register_numbers)
        parsed = parse_csv_register_numbers(csv_content)
        
        assert parsed == register_numbers


class TestDuplicateRemoval:
    """
    **Feature: exam-scheduler, Property 3: Duplicate Removal Preserves Unique Values**
    **Validates: Requirements 1.3**
    
    For any list of register numbers (with or without duplicates), after deduplication:
    (1) the output contains no duplicates
    (2) all unique values from input are present in output
    (3) the count of removed duplicates equals input length minus output length
    """

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_duplicate_removal_properties(self, register_numbers):
        """Verify all three duplicate removal properties"""
        unique, removed = remove_duplicates(register_numbers)
        
        # Property 1: Output contains no duplicates
        assert len(unique) == len(set(unique))
        
        # Property 2: All unique values from input are present
        assert set(unique) == set(register_numbers)
        
        # Property 3: Count of removed equals input - output length
        assert len(removed) == len(register_numbers) - len(unique)

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=50,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_unique_list_unchanged(self, register_numbers):
        """List with no duplicates should be unchanged"""
        unique, removed = remove_duplicates(register_numbers)
        
        assert unique == register_numbers
        assert removed == []

    @given(
        base_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_preserves_first_occurrence_order(self, base_numbers):
        """First occurrence order should be preserved"""
        # Create list with duplicates by repeating some elements
        with_duplicates = base_numbers + base_numbers[:len(base_numbers)//2]
        
        unique, _ = remove_duplicates(with_duplicates)
        
        # Order should match original unique list
        assert unique == base_numbers


class TestDateSorting:
    """
    **Feature: exam-scheduler, Property 4: Dates Sorted Chronologically**
    **Validates: Requirements 2.1**
    
    For any list of valid dates provided as input, the output date list 
    should be sorted in chronological order.
    """

    @given(
        dates=st.lists(
            st.dates(
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime(2030, 12, 31).date()
            ),
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_dates_sorted_chronologically(self, dates):
        """Dates should be sorted in chronological order"""
        # Convert to DD-MM-YY format
        date_strings = [d.strftime('%d-%m-%y') for d in dates]
        
        sorted_dates = parse_dates(date_strings)
        
        # Parse back to datetime for comparison
        parsed_back = [datetime.strptime(d, '%d-%m-%y') for d in sorted_dates]
        
        # Verify sorted
        assert parsed_back == sorted(parsed_back)

    @given(
        dates=st.lists(
            st.dates(
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime(2030, 12, 31).date()
            ),
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_all_dates_preserved(self, dates):
        """All input dates should be present in output"""
        date_strings = [d.strftime('%d-%m-%y') for d in dates]
        
        sorted_dates = parse_dates(date_strings)
        
        assert set(sorted_dates) == set(date_strings)
