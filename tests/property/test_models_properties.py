"""
Property-based tests for data models
"""
import pytest
from hypothesis import given, strategies as st, settings

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import Examiner


# Strategies for generating test data
examiner_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
).filter(lambda x: ': ' not in x and x.strip() == x)

examiner_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() == x and len(x.strip()) > 0)


class TestExaminerRoundTrip:
    """
    **Feature: exam-scheduler, Property 6: Examiner Data Round-Trip**
    **Validates: Requirements 3.4**
    
    For any list of examiner objects (with id and name), serializing and 
    parsing back should produce equivalent examiner data.
    """

    @given(
        examiner_id=examiner_id_strategy,
        examiner_name=examiner_name_strategy
    )
    @settings(max_examples=100)
    def test_examiner_round_trip(self, examiner_id: str, examiner_name: str):
        """Single examiner round-trip: to_string -> from_string"""
        original = Examiner(id=examiner_id, name=examiner_name)
        formatted = original.to_string()
        parsed = Examiner.from_string(formatted)
        
        assert parsed.id == original.id
        assert parsed.name == original.name

    @given(
        examiners=st.lists(
            st.tuples(examiner_id_strategy, examiner_name_strategy),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_examiner_list_round_trip(self, examiners):
        """List of examiners round-trip"""
        original_list = [Examiner(id=eid, name=ename) for eid, ename in examiners]
        formatted_list = [e.to_string() for e in original_list]
        parsed_list = [Examiner.from_string(s) for s in formatted_list]
        
        assert len(parsed_list) == len(original_list)
        for orig, parsed in zip(original_list, parsed_list):
            assert parsed.id == orig.id
            assert parsed.name == orig.name
