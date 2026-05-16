from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import List, Optional, Any, Dict

class QueryCategory(str, Enum):
    BASIC_INFO = "basic_info"
    REVIEWS = "reviews"
    RECOMMEND = "recommend"
    CATEGORY_SEARCH = "category_search"
    CHIT_CHAT = "chit_chat"
    UNCLEAR = "unclear"

class ExtractedFilters(BaseModel):
    faculty: Optional[str] = Field(default=None, description="Normalized Faculty Name")
    category: Optional[str] = Field(default=None, description="Normalized GenEd Category")

class ExpandedQuery(BaseModel):
    expanded_query: str = Field(description="The clarified user query")
    search_keywords: List[str] = Field(default=[], description="Keywords for vector search")
    extracted_filters: ExtractedFilters = Field(default_factory=ExtractedFilters)
    reasoning: str = Field(description="Why this expansion?")
    is_unclear: bool = Field(default=False, description="True if query is nonsense/unrelated")

class QueryIntent(BaseModel):
    category: QueryCategory = Field(..., description="The intent category of the user's query.")
    course_codes: List[str] = Field(default=[], description="List of extracted 8-digit course codes (e.g., '01234567').")
    course_names: List[str] = Field(default=[], description="List of extracted course names (e.g., 'Software Engineering').")
    reason: Optional[str] = Field(default=None, description="Reasoning for the intent classification")

class LogEntry(BaseModel):
    step: str
    details: Any
    timestamp: float

class ChatRequest(BaseModel):
    query: str = Field(..., example="วิชา 01999033 สอนยังไง?") 

    @field_validator('query')
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Query string cannot be empty or whitespace only')
        return v

class SourceNode(BaseModel):
    node_id: str
    text: str
    score: Optional[float]
    metadata: Dict[str, Any]

class ChatResponse(BaseModel):
    response: str
    sources: List[SourceNode]
    intent: Optional[QueryIntent] = None
    latency_ms: Optional[float] = None
    latency_breakdown: Optional[Dict[str, float]] = None
    suggested_queries: Optional[List[str]] = None 
    debug_logs: List[LogEntry] = Field(default=[], description="Trace of system decisions")

# from courses table
class CourseName(BaseModel):
    course_id: str
    course_name_th: str
    category_64: str
    competency_67: str
    credits: int
    faculty: str
    doc_type: str
    description: str
    clos: str
# from reviews table
class ReviewSubmission(BaseModel):
    course_id: str
    review_content: str
    course_name: str
    credits: str 
    faculty: str
    category_64: str
    competency_67: str

class Review(ReviewSubmission):
    id: int
