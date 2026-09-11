from typing import Optional

from pydantic import BaseModel


class RetrievedDocument(BaseModel):
    id: str
    title: str
    source_name: str
    source_type: str
    source_url: Optional[str] = None
    content: str
    distance: Optional[float] = None
    retrieved_at: Optional[str] = None
