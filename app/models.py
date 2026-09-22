from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    model: str
    fallback_used: bool
    choices: List[Dict]
    usage: Optional[Dict] = None
