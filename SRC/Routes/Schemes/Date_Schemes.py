from pydantic import BaseModel
from typing import Optional

class ProcessRequest (BaseModel) :
    file_id : str = None
    Do_reset : Optional[int] = 0

class ScrapeRequest (BaseModel) :
    base_url : str
    library_name : str  # Unique name for the library/project
    Do_reset : Optional[int] = 0


class ProcessScrapeCacheRequest (BaseModel) :
    """Request to run chunking/embedding from a previously saved scrape cache (e.g. after frontend timeout)."""
    base_url : str

