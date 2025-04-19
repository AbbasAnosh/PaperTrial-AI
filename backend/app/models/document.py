from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel

class DocumentBase(BaseModel):
    filename: str
    form_type: str
    status: str = "pending"
    extracted_fields: Optional[Dict] = {}
    submission_history: Optional[List[Dict]] = []

class DocumentCreate(DocumentBase):
    user_email: str

class DocumentUpdate(DocumentBase):
    pass

class DocumentInDB(DocumentBase):
    id: str
    user_email: str
    created_at: datetime
    updated_at: datetime
    file_path: str

    class Config:
        from_attributes = True 