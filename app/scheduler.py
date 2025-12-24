"""
Core scheduling algorithm for exam scheduler
"""
from typing import List, Tuple
from datetime import datetime
import math
from .models import TimeSlot, LabSchedule


# Constants
STUDENTS_PER_LAB = 25
FORENOON_CAPACITY = 13
AFTERNOON_CAPACITY = 12
LABS_PER_DAY = 5
DAILY_CAPACITY = STUDENTS_PER_LAB * LABS_PER_DAY  # 125

FORENOON_TIME = "09:30 am - 12:30 pm"
AFTERNOON_TIME = "01:30 pm - 04:30 pm"


def parse_date(date_str: str) -> datetime:
    """Parse DD-MM-YY format to datetime"""
    return datetime.strptime(date_str, '%d-%m-%y')


def date_diff_days(date1: str, date2: str) -> int:
    """Calculate difference in days between two dates"""
    d1 = parse_date(date1)
    d2 = parse_date(date2)
    return abs((d2 - d1).days)


def select_optimal_dates(
    available_dates: List[str],
    student_count: int,
    min_gap_days: int = 1
) -> Tuple[List[str], str]:
    """
    Select optimal dates from available dates based on student count and gap requirements.
    
    Algorithm:
    1. Calculate required number of exam days (125 students per day)
    2. Sort available dates chronologically
    3. Select dates with minimum gap between them
    4. Prefer evenly spaced dates when possible
    
    Args:
        available_dates: List of available dates in DD-MM-YY format
        student_count: Total number of students to schedule
        min_gap_days: Minimum gap between exam days (default 1 = consecutive days allowed)
        
    Returns:
        Tuple of (selected_dates, explanation_message)
    """
    if not available_dates:
        return [], "No dates provided"
    
    # Calculate required days
    required_days = math.ceil(student_count / DAILY_CAPACITY)
    
    if required_days == 0:
        return [], "No students to schedule"
    
    # Sort dates chronologically
    sorted_dates = sorted(available_dates, key=lambda d: parse_date(d))
    
    if len(sorted_dates) < required_days:
        return sorted_dates, f"Warning: Only {len(sorted_dates)} dates available, need {required_days} for {student_count} students"
    
    if required_days == 1:
        return [sorted_dates[0]], f"Selected 1 date for {student_count} students"
    
    # Try to find dates with optimal spacing
    selected = []
    
    if min_gap_days <= 1:
        # Just take first N dates needed
        selected = sorted_dates[:required_days]
    else:
        # Try to find dates with minimum gap
        selected = [sorted_dates[0]]
        
        for date in sorted_dates[1:]:
            if len(selected) >= required_days:
                break
            
            # Check gap from last selected date
            gap = date_diff_days(selected[-1], date)
            if gap >= min_gap_days:
                selected.append(date)
        
        # If we couldn't find enough dates with the gap, relax the constraint
        if len(selected) < required_days:
            # Fall back to taking dates in order
            selected = sorted_dates[:required_days]
            return selected, f"Selected {len(selected)} dates (gap constraint relaxed due to limited dates)"
    
    # Calculate actual gaps for message
    gaps = []
    for i in range(1, len(selected)):
        gaps.append(date_diff_days(selected[i-1], selected[i]))
    
    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    
    message = f"Selected {len(selected)} dates for {student_count} students"
    if gaps:
        message += f" (avg gap: {avg_gap:.1f} days)"
    
    return selected, message


def auto_schedule_dates(
    available_dates: List[str],
    student_count: int,
    min_gap_days: int = 1,
    subjects: List[str] = None
) -> Tuple[List[dict], str]:
    """
    Automatically select and assign dates for exams.
    
    Args:
        available_dates: List of available dates
        student_count: Total students
        min_gap_days: Minimum gap between exam days
        subjects: Optional list of subjects to assign to dates
        
    Returns:
        Tuple of (exam_dates with subjects, message)
    """
    selected_dates, message = select_optimal_dates(available_dates, student_count, min_gap_days)
    
    exam_dates = []
    for i, date in enumerate(selected_dates):
        exam_date = {
            'date': date,
            'subject': subjects[i] if subjects and i < len(subjects) else None,
            'register_numbers': []
        }
        exam_dates.append(exam_date)
    
    return exam_dates, message


def create_time_slot(session: str, register_numbers: List[str]) -> TimeSlot:
    """
    Create a time slot with the given session and register numbers.
    
    Args:
        session: "forenoon" or "afternoon"
        register_numbers: List of register numbers for this slot
        
    Returns:
        TimeSlot object
    """
    if session == "forenoon":
        return TimeSlot(
            time=FORENOON_TIME,
            session="forenoon",
            capacity=len(register_numbers),
            register_numbers=register_numbers
        )
    else:
        return TimeSlot(
            time=AFTERNOON_TIME,
            session="afternoon",
            capacity=len(register_numbers),
            register_numbers=register_numbers
        )


def split_into_slots(students: List[str]) -> tuple[List[str], List[str]]:
    """
    Split a list of students (up to 25) into forenoon and afternoon slots.
    Forenoon gets first 13 (or all if less), afternoon gets remaining (up to 12).
    
    Args:
        students: List of register numbers (max 25)
        
    Returns:
        Tuple of (forenoon_students, afternoon_students)
    """
    forenoon = students[:FORENOON_CAPACITY]
    afternoon = students[FORENOON_CAPACITY:FORENOON_CAPACITY + AFTERNOON_CAPACITY]
    return forenoon, afternoon


def create_lab_schedule(
    date: str, 
    lab: str, 
    students: List[str],
    internal_examiner: dict = None,
    external_examiner: dict = None,
    semester: str = None,
    batch: str = None,
    subject: str = None
) -> LabSchedule:
    """
    Create a lab schedule for a single lab on a single date.
    
    Args:
        date: Date string in DD-MM-YY format
        lab: Lab name
        students: List of register numbers (max 25)
        internal_examiner: Assigned internal examiner dict
        external_examiner: Assigned external examiner dict
        semester: Semester name (optional)
        batch: Batch name (optional)
        subject: Subject name (optional)
        
    Returns:
        LabSchedule object
    """
    forenoon_students, afternoon_students = split_into_slots(students)
    
    slots = [
        create_time_slot("forenoon", forenoon_students),
        create_time_slot("afternoon", afternoon_students)
    ]
    
    return LabSchedule(
        date=date, 
        subject=subject,
        lab=lab, 
        slots=slots,
        internal_examiner=internal_examiner,
        external_examiner=external_examiner,
        semester=semester,
        batch=batch
    )


def allocate_students(
    register_numbers: List[str],
    dates: List[str],
    labs: List[str],
    internal_examiners: List[dict] = None,
    external_examiners: List[dict] = None,
    semesters: List[dict] = None,
    date_subjects: dict = None,
    date_register_numbers: dict = None
) -> List[LabSchedule]:
    """
    Allocate students to labs and time slots across dates.
    Assigns 1 internal + 1 external examiner per lab.
    
    Algorithm:
    1. If date_register_numbers provided, use students for each specific date
    2. Otherwise, split register numbers into chunks of 25
    3. Assign each chunk to a lab in order
    4. Each lab gets 13 students in forenoon, 12 in afternoon
    5. After 5 labs (125 students), move to next date
    6. Handle partial fills on final date
    7. Assign examiners to labs (cycling through available examiners)
    
    Args:
        register_numbers: List of all register numbers (preserves order)
        dates: List of exam dates (sorted chronologically)
        labs: List of 5 lab names
        internal_examiners: List of internal examiner dicts
        external_examiners: List of external examiner dicts
        semesters: List of semester dicts with batches (optional)
        date_subjects: Dict mapping date to subject name (optional)
        date_register_numbers: Dict mapping date to list of register numbers (optional)
        
    Returns:
        List of LabSchedule objects
    """
    schedules = []
    internal_examiners = internal_examiners or []
    external_examiners = external_examiners or []
    date_subjects = date_subjects or {}
    date_register_numbers = date_register_numbers or {}
    
    # Build a mapping of register number to semester/batch if semesters provided
    reg_to_sem_batch = {}
    if semesters:
        for sem in semesters:
            sem_name = sem.get('name', '')
            for batch in sem.get('batches', []):
                batch_name = batch.get('name', '')
                for reg_no in batch.get('register_numbers', []):
                    reg_to_sem_batch[reg_no] = (sem_name, f"{sem_name}{batch_name}")
    
    # If date-based register numbers provided, use them
    if date_register_numbers:
        for date in dates:
            date_students = date_register_numbers.get(date, [])
            subject = date_subjects.get(date)
            
            student_index = 0
            total_students = len(date_students)
            
            for lab_index, lab in enumerate(labs):
                if student_index >= total_students:
                    break
                
                # Get next chunk of up to 25 students
                chunk_end = min(student_index + STUDENTS_PER_LAB, total_students)
                chunk = date_students[student_index:chunk_end]
                
                if chunk:
                    internal_exam = None
                    external_exam = None
                    
                    if internal_examiners:
                        internal_exam = internal_examiners[lab_index % len(internal_examiners)]
                    if external_examiners:
                        external_exam = external_examiners[lab_index % len(external_examiners)]
                    
                    # Get semester/batch info
                    semester = None
                    batch = None
                    if reg_to_sem_batch:
                        batch_counts = {}
                        for reg_no in chunk:
                            if reg_no in reg_to_sem_batch:
                                sem_batch = reg_to_sem_batch[reg_no]
                                batch_counts[sem_batch] = batch_counts.get(sem_batch, 0) + 1
                        
                        if batch_counts:
                            most_common = max(batch_counts.items(), key=lambda x: x[1])
                            semester, batch = most_common[0]
                            if len(batch_counts) > 1:
                                all_batches = sorted(set(b for (_, b) in batch_counts.keys()))
                                batch = ", ".join(all_batches)
                    
                    schedule = create_lab_schedule(
                        date, lab, chunk,
                        internal_examiner=internal_exam,
                        external_examiner=external_exam,
                        semester=semester,
                        batch=batch,
                        subject=subject
                    )
                    schedules.append(schedule)
                    student_index = chunk_end
        
        return schedules
    
    # Original algorithm for non-date-based input
    student_index = 0
    total_students = len(register_numbers)
    
    for date in dates:
        if student_index >= total_students:
            break
        
        # Get subject for this date
        subject = date_subjects.get(date)
            
        for lab_index, lab in enumerate(labs):
            if student_index >= total_students:
                break
            
            # Get next chunk of up to 25 students
            chunk_end = min(student_index + STUDENTS_PER_LAB, total_students)
            chunk = register_numbers[student_index:chunk_end]
            
            if chunk:  # Only create schedule if there are students
                # Assign examiners (cycle through available ones)
                internal_exam = None
                external_exam = None
                
                if internal_examiners:
                    internal_exam = internal_examiners[lab_index % len(internal_examiners)]
                if external_examiners:
                    external_exam = external_examiners[lab_index % len(external_examiners)]
                
                # Get semester/batch info - find the most common batch in this chunk
                semester = None
                batch = None
                if reg_to_sem_batch:
                    batch_counts = {}
                    for reg_no in chunk:
                        if reg_no in reg_to_sem_batch:
                            sem_batch = reg_to_sem_batch[reg_no]
                            batch_counts[sem_batch] = batch_counts.get(sem_batch, 0) + 1
                    
                    if batch_counts:
                        # Get the most common batch in this chunk
                        most_common = max(batch_counts.items(), key=lambda x: x[1])
                        semester, batch = most_common[0]
                        
                        # If multiple batches, show them all
                        if len(batch_counts) > 1:
                            all_batches = sorted(set(b for (_, b) in batch_counts.keys()))
                            batch = ", ".join(all_batches)
                
                schedule = create_lab_schedule(
                    date, lab, chunk,
                    internal_examiner=internal_exam,
                    external_examiner=external_exam,
                    semester=semester,
                    batch=batch,
                    subject=subject
                )
                schedules.append(schedule)
                student_index = chunk_end
    
    return schedules


def get_all_register_numbers(schedules: List[LabSchedule]) -> List[str]:
    """
    Extract all register numbers from schedules in order.
    
    Args:
        schedules: List of LabSchedule objects
        
    Returns:
        Flattened list of all register numbers in schedule order
    """
    all_numbers = []
    for schedule in schedules:
        for slot in schedule.slots:
            all_numbers.extend(slot.register_numbers)
    return all_numbers


def count_students_per_date(schedules: List[LabSchedule]) -> dict[str, int]:
    """
    Count total students per date.
    
    Args:
        schedules: List of LabSchedule objects
        
    Returns:
        Dict mapping date to student count
    """
    counts = {}
    for schedule in schedules:
        date = schedule.date
        student_count = sum(len(slot.register_numbers) for slot in schedule.slots)
        counts[date] = counts.get(date, 0) + student_count
    return counts


def count_students_per_lab(schedules: List[LabSchedule]) -> List[int]:
    """
    Get student count for each lab schedule.
    
    Args:
        schedules: List of LabSchedule objects
        
    Returns:
        List of student counts per lab
    """
    return [
        sum(len(slot.register_numbers) for slot in schedule.slots)
        for schedule in schedules
    ]
