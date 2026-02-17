from pydantic import BaseModel
from typing import Optional, List

class PushRequest (BaseModel) :

    do_reset : Optional[int] = 0
    project_name : Optional[str] = None


class ChatMessageForRequest (BaseModel) :
    role : str  # "user" | "assistant"
    content : str


class SearchRequest (BaseModel) :

    text : str
    project_name : Optional[str] = None
    limit : Optional[int] = 10
    chat_history : Optional[List[ChatMessageForRequest]] = None
