"""
Property-based tests for AI response parsing
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
import re

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.file_parser import parse_groq_response, extract_register_numbers_from_text


# Strategy for valid register numbers matching the pattern: 2-4 uppercase letters + 2 digits + 2-3 uppercase letters + 3 digits
# Examples: TVE20CS001, ABC21EC123, ABCD22CSE456
def generate_register_number():
    """Generate a valid register number matching the expected pattern"""
    return st.builds(
        lambda prefix, year, dept, num: f"{prefix}{year:02d}{dept}{num:03d}",
        prefix=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=2, max_size=4),
        year=st.integers(min_value=10, max_value=99),
        dept=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=2, max_size=3),
        num=st.integers(min_value=0, max_value=999)
    )


register_number_strategy = generate_register_number()


class TestAIResponseRegisterNumberExtraction:
    """
    **Feature: exam-scheduler, Property 15: AI Response Register Number Extraction**
    **Validates: Requirements 12.5**
    
    For any text response containing register number patterns 
    (format: 2-4 uppercase letters + 2 digits + 2-3 uppercase letters + 3 digits),
    the parser should extract all matching patterns and return them as a list with no duplicates.
    """

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=30,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_extracts_all_register_numbers_from_formatted_response(self, register_numbers):
        """Parser should extract all register numbers from a formatted AI response"""
        # Create a formatted response like what Groq AI would return
        response = f"""SEMESTER: S1
BATCH: A
REGISTER_NUMBERS:
{chr(10).join(register_numbers)}
"""
        semesters, extracted = parse_groq_response(response)
        
        # All input register numbers should be extracted
        assert set(extracted) == set(register_numbers)
        
        # No duplicates in output
        assert len(extracted) == len(set(extracted))

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=20,
            unique=True
        ),
        noise_text=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_extracts_register_numbers_from_noisy_text(self, register_numbers, noise_text):
        """Parser should extract register numbers even with surrounding noise"""
        # Mix register numbers with noise
        response = f"Some text {noise_text}\n"
        for i, reg in enumerate(register_numbers):
            response += f"- {reg}\n"
            if i % 3 == 0:
                response += f"random text {noise_text[:20]}\n"
        
        semesters, extracted = parse_groq_response(response)
        
        # All input register numbers should be found
        for reg in register_numbers:
            assert reg in extracted, f"Missing register number: {reg}"

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=15
        )
    )
    @settings(max_examples=100)
    def test_handles_duplicates_in_response(self, register_numbers):
        """Parser should deduplicate register numbers in the response"""
        # Create response with duplicates
        duplicated = register_numbers + register_numbers[:len(register_numbers)//2]
        response = f"""REGISTER_NUMBERS:
{chr(10).join(duplicated)}
"""
        semesters, extracted = parse_groq_response(response)
        
        # Output should have no duplicates
        assert len(extracted) == len(set(extracted))
        
        # All unique values should be present
        assert set(extracted) == set(register_numbers)

    @given(
        semester=st.sampled_from(['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']),
        batch=st.sampled_from(['A', 'B', 'C', 'D']),
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_extracts_semester_and_batch_info(self, semester, batch, register_numbers):
        """Parser should extract semester and batch information when present"""
        response = f"""SEMESTER: {semester}
BATCH: {batch}
REGISTER_NUMBERS:
{chr(10).join(register_numbers)}
"""
        semesters, extracted = parse_groq_response(response)
        
        # Should have semester data
        assert len(semesters) > 0
        assert semesters[0]['name'] == semester
        assert semesters[0]['batches'][0]['name'] == batch

    def test_handles_empty_response(self):
        """Parser should handle empty response gracefully"""
        semesters, extracted = parse_groq_response("")
        
        assert semesters == []
        assert extracted == []

    def test_handles_response_with_no_register_numbers(self):
        """Parser should handle response with no valid register numbers"""
        response = "I could not find any register numbers in the image."
        
        semesters, extracted = parse_groq_response(response)
        
        assert extracted == []


class TestTextRegisterNumberExtraction:
    """
    Additional tests for extract_register_numbers_from_text function
    """

    @given(
        register_numbers=st.lists(
            register_number_strategy,
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_extracts_from_plain_text(self, register_numbers):
        """Should extract register numbers from plain text"""
        text = " ".join(register_numbers)
        
        semesters, extracted = extract_register_numbers_from_text(text)
        
        # All register numbers should be found
        assert set(extracted) == set(register_numbers)
