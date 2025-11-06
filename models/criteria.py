"""
criteria.py
-----------
Pydantic models for paging, sorting, and filtering.
Used by tools.
"""

from typing import List, Optional, Set
from pydantic import BaseModel
from enum import Enum

class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

class SortModel(BaseModel):
    property: str
    direction: SortDirection = SortDirection.ASC

class DefaultCriteriaModel(BaseModel):
    page: Optional[int] = 0
    size: Optional[int] = 25
    sort: Optional[List[SortModel]] = []

class TimestampRange(BaseModel):
    start: Optional[str]
    end: Optional[str]

class AuditedCriteriaModel(DefaultCriteriaModel):
    creators: Optional[Set[str]] = None
    modifiers: Optional[Set[str]] = None
    createdAt: Optional[TimestampRange] = None
    modifiedAt: Optional[TimestampRange] = None
