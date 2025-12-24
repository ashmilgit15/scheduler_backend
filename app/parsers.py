"""
Parsers for register numbers, dates, and CSV content
"""
import re
import csv
import io
from datetime import datetime
from typing import List, Tuple


def parse_register_numbers(text: str) -> List[str]:
    """
    Parse register numbers from textarea input.
    Accepts newline, comma, or space separated values.
    Preserves input order.
    
    Args:
        text: Raw text input containing register numbers
        
    Returns:
        List of register numbers in input order
    """
    if not text or not text.strip():
        return []
    
    # Split by newlines, commas, or multiple spaces
    parts = re.split(r'[\n,]+|\s{2,}', text)
    
    # Clean and filter empty strings
    register_numbers = []
    for part in parts:
        cleaned = part.strip()
        if cleaned:
            register_numbers.append(cleaned)
    
    return register_numbers


def format_register_numbers(register_numbers: List[str]) -> str:
    """
    Format register numbers list as newline-separated string.
    
    Args:
        register_numbers: List of register numbers
        
    Returns:
        Newline-separated string
    """
    return '\n'.join(register_numbers)


def parse_csv_register_numbers(csv_content: str) -> List[str]:
    """
    Parse register numbers from CSV content.
    Handles single column or first column of multi-column CSV.
    Preserves input order.
    
    Args:
        csv_content: CSV file content as string
        
    Returns:
        List of register numbers in input order
    """
    if not csv_content or not csv_content.strip():
        return []
    
    register_numbers = []
    reader = csv.reader(io.StringIO(csv_content))
    
    for row in reader:
        if row:
            # Take first column value
            value = row[0].strip()
            if value and not value.lower() in ('register_number', 'reg_no', 'regno', 'register number'):
                register_numbers.append(value)
    
    return register_numbers


def format_csv_register_numbers(register_numbers: List[str]) -> str:
    """
    Format register numbers as CSV content.
    
    Args:
        register_numbers: List of register numbers
        
    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    for reg_no in register_numbers:
        writer.writerow([reg_no])
    return output.getvalue()


def remove_duplicates(register_numbers: List[str]) -> Tuple[List[str], List[str]]:
    """
    Remove duplicate register numbers while preserving first occurrence order.
    
    Args:
        register_numbers: List of register numbers (may contain duplicates)
        
    Returns:
        Tuple of (unique_list, removed_duplicates)
    """
    seen = set()
    unique = []
    duplicates = []
    
    for reg_no in register_numbers:
        if reg_no in seen:
            duplicates.append(reg_no)
        else:
            seen.add(reg_no)
            unique.append(reg_no)
    
    return unique, duplicates


def parse_dates(date_strings: List[str]) -> List[str]:
    """
    Parse and sort dates in DD-MM-YY format chronologically.
    
    Args:
        date_strings: List of date strings in DD-MM-YY format
        
    Returns:
        Sorted list of date strings
    """
    if not date_strings:
        return []
    
    # Parse dates and sort
    parsed = []
    for date_str in date_strings:
        try:
            dt = datetime.strptime(date_str.strip(), '%d-%m-%y')
            parsed.append((dt, date_str.strip()))
        except ValueError:
            # Keep invalid dates as-is for validation to catch
            parsed.append((datetime.max, date_str.strip()))
    
    # Sort by datetime
    parsed.sort(key=lambda x: x[0])
    
    return [date_str for _, date_str in parsed]


def format_dates(dates: List[str]) -> str:
    """
    Format dates list as comma-separated string.
    
    Args:
        dates: List of date strings
        
    Returns:
        Comma-separated string
    """
    return ', '.join(dates)
