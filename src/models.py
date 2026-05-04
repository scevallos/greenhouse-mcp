from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    id: int
    name: str
    status: str
    departments: List[Dict[str, Any]] = []
    offices: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    requisition_id: Optional[str] = None
    notes: Optional[str] = None


class Candidate(BaseModel):
    id: int
    first_name: str
    last_name: str
    company: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    email_addresses: List[Dict[str, Any]] = []
    phone_numbers: List[Dict[str, Any]] = []
    addresses: List[Dict[str, Any]] = []
    applications: List[Dict[str, Any]] = []
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}


class Application(BaseModel):
    id: int
    candidate_id: int
    prospect: bool = False
    applied_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    source: Optional[Dict[str, Any]] = None
    credited_to: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[Dict[str, Any]] = None
    rejection_details: Optional[Dict[str, Any]] = None
    jobs: List[Dict[str, Any]] = []
    job_post_id: Optional[int] = None
    status: str
    current_stage: Optional[Dict[str, Any]] = None
    answers: List[Dict[str, Any]] = []
    custom_fields: Dict[str, Any] = {}


class Note(BaseModel):
    body: str
    visibility: str = Field(
        default="private",
        description="Options: 'admin_only', 'private', 'public'",
    )


class CandidateCreateRequest(BaseModel):
    first_name: str
    last_name: str
    company: Optional[str] = None
    title: Optional[str] = None
    phone_numbers: Optional[List[Dict[str, str]]] = None
    email_addresses: Optional[List[Dict[str, str]]] = None
    addresses: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[List[Dict[str, Any]]] = None


class ApplicationAdvanceRequest(BaseModel):
    from_stage_id: int
    to_stage_id: Optional[int] = None
