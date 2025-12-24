from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class Examiner(BaseModel):
    """Examiner with ID and name"""
    id: str = Field(..., min_length=1, description="Examiner ID")
    name: str = Field(..., min_length=1, description="Examiner name")

    def to_string(self) -> str:
        """Format examiner for display"""
        return f"{self.id}: {self.name}"

    @classmethod
    def from_string(cls, s: str) -> "Examiner":
        """Parse examiner from formatted string"""
        parts = s.split(": ", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid examiner format: {s}")
        return cls(id=parts[0], name=parts[1])


class Batch(BaseModel):
    """A batch/sub-semester within a semester (e.g., S1A, S1B)"""
    name: str = Field(..., min_length=1, description="Batch name (e.g., A, B)")
    register_numbers: List[str] = Field(default_factory=list, description="Register numbers in this batch")


class Semester(BaseModel):
    """A semester with optional batches"""
    name: str = Field(..., min_length=1, description="Semester name (e.g., S1, S2)")
    batches: List[Batch] = Field(default_factory=list, description="Batches within this semester")
    
    def get_all_register_numbers(self) -> List[str]:
        """Get all register numbers from all batches"""
        all_numbers = []
        for batch in self.batches:
            all_numbers.extend(batch.register_numbers)
        return all_numbers
    
    def get_batch_label(self, batch_name: str) -> str:
        """Get full batch label (e.g., S1A)"""
        return f"{self.name}{batch_name}"


class ExamMetadata(BaseModel):
    """Exam metadata information - all fields optional"""
    exam_name: Optional[str] = Field(None, description="Name of the examination")
    semester: Optional[str] = Field(None, description="Semester")
    department: Optional[str] = Field(None, description="Department name")
    academic_year: Optional[str] = Field(None, description="Academic year")


class ExamDate(BaseModel):
    """Exam date with optional subject and register numbers"""
    date: str = Field(..., description="Date in DD-MM-YY format")
    subject: Optional[str] = Field(None, description="Subject name for this date (optional)")
    register_numbers: List[str] = Field(default_factory=list, description="Register numbers for this date")


class TimeSlot(BaseModel):
    """Time slot with session details and assigned students"""
    time: str = Field(..., description="Time range string")
    session: str = Field(..., pattern="^(forenoon|afternoon)$", description="Session name")
    capacity: int = Field(..., ge=0, le=13, description="Slot capacity")
    register_numbers: List[str] = Field(default_factory=list, description="Assigned register numbers")


class LabSchedule(BaseModel):
    """Schedule for a single lab on a single date"""
    date: str = Field(..., description="Date in DD-MM-YY format")
    subject: Optional[str] = Field(None, description="Subject name for this date")
    lab: str = Field(..., min_length=1, description="Lab name")
    slots: List[TimeSlot] = Field(..., min_length=2, max_length=2, description="Forenoon and afternoon slots")
    internal_examiner: Optional["Examiner"] = Field(None, description="Assigned internal examiner")
    external_examiner: Optional["Examiner"] = Field(None, description="Assigned external examiner")
    semester: Optional[str] = Field(None, description="Semester for this lab schedule")
    batch: Optional[str] = Field(None, description="Batch for this lab schedule")


class ScheduleRequest(BaseModel):
    """Request to generate exam schedule - all fields optional for flexible customization"""
    exam_metadata: Optional[ExamMetadata] = Field(None, description="Exam metadata (optional)")
    register_numbers: List[str] = Field(default_factory=list, description="List of register numbers (legacy)")
    semesters: List[Semester] = Field(default_factory=list, description="Semesters with batches")
    dates: List[str] = Field(default_factory=list, description="Exam dates in DD-MM-YY format (legacy)")
    exam_dates: List[ExamDate] = Field(default_factory=list, description="Exam dates with subjects")
    labs: List[str] = Field(default_factory=list, description="Lab names (optional, defaults will be used)")
    internal_examiners: List[Examiner] = Field(default_factory=list, description="Internal examiners (optional)")
    external_examiners: List[Examiner] = Field(default_factory=list, description="External examiners (optional)")
    
    def get_all_register_numbers(self) -> List[str]:
        """Get all register numbers from exam_dates, semesters, or legacy field"""
        # First check exam_dates (date-based input)
        if self.exam_dates:
            all_numbers = []
            for ed in self.exam_dates:
                all_numbers.extend(ed.register_numbers)
            if all_numbers:
                return all_numbers
        # Then check semesters
        if self.semesters:
            all_numbers = []
            for semester in self.semesters:
                all_numbers.extend(semester.get_all_register_numbers())
            return all_numbers
        return self.register_numbers
    
    def get_dates(self) -> List[str]:
        """Get dates from exam_dates or legacy dates field"""
        if self.exam_dates:
            return [ed.date for ed in self.exam_dates]
        return self.dates
    
    def get_subject_for_date(self, date: str) -> Optional[str]:
        """Get subject for a specific date"""
        for ed in self.exam_dates:
            if ed.date == date:
                return ed.subject
        return None


class ScheduleResponse(BaseModel):
    """Generated exam schedule response"""
    exam_metadata: Optional[ExamMetadata] = None
    examiners: Dict[str, List[Examiner]] = Field(default_factory=dict)
    schedule: List[LabSchedule] = Field(default_factory=list)

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict"""
        return self.model_dump()

    @classmethod
    def from_json(cls, data: dict) -> "ScheduleResponse":
        """Parse from JSON dict"""
        return cls.model_validate(data)


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str


class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[ScheduleResponse] = None
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
