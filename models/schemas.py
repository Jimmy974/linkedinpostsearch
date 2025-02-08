from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LinkedInPost(BaseModel):
    title: str
    url: Optional[str] = None
    id: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class SearchRequest(BaseModel):
    keywords: str = Field(..., description="Search keywords for LinkedIn posts")
    min_publish_date: Optional[str] = Field(None, description="Minimum publish date in YYYY-MM-DD format")
    max_publish_date: Optional[str] = Field(None, description="Maximum publish date in YYYY-MM-DD format")
    debug_html: bool = Field(False, description="Whether to generate debug HTML files")
    llm_provider: str = Field(
        "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        description="LLM provider for content extraction"
    )

class PostResponse(BaseModel):
    title: str
    url: Optional[str] = None
    id: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    debug_files: Optional[List[str]] = None

class SearchResponse(BaseModel):
    posts: List[PostResponse]
    total_posts: int
    search_metadata: dict = Field(
        default_factory=lambda: {
            "timestamp": datetime.utcnow().isoformat(),
        }
    ) 