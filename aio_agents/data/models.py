from datetime import datetime
from typing import List, Optional

from aiofauna import FaunaModel, handle_errors
from pydantic import Field

from ..services import *
from .schemas import WordCount

llm = LLMStack()


class User(FaunaModel):
    """
    Auth0 User, Github User or Cognito User
    """

    email: Optional[str] = Field(default=None, index=True)
    email_verified: Optional[bool] = Field(default=False)
    family_name: Optional[str] = Field(default=None)
    given_name: Optional[str] = Field(default=None)
    locale: Optional[str] = Field(default=None, index=True)
    name: str = Field(...)
    nickname: Optional[str] = Field(default=None)
    picture: Optional[str] = Field(default=None)
    sub: str = Field(..., unique=True)
    updated_at: Optional[str] = Field(default=None)


class ChatMessage(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    owner: str = Field(..., description="The owner of the message.")
    content: str = Field(..., description="The content of the message.")


class Namespace(FaunaModel):
    messages: List[str] = Field(default_factory=list)
    title: str = Field(default="[New Namespace]", index=True)
    user: str = Field(..., index=True)
    participants: List[str] = Field(default_factory=list)

    @handle_errors
    async def set_title(self, text: str):
        response = await llm.chat(
            text=text,
            context=f"You are a namespace titles generator, you will generate this namespace name based on the user first prompt. It must be no longer than 1 sentence of 7 words. FIRST PROMPT: {text}",
        )
        return await self.update(self.ref, title=response)  # type:ignore


class FileData(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    user: str = Field(..., description="The owner of the file.", index=True)
    name: str = Field(..., description="The name of the file.")
    size: int = Field(..., description="The size of the file.", index=True)
    content_type: str = Field(
        ..., description="The content type of the file.", index=True
    )
    last_modified: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="The last modified date of the file.",
        index=True,
    )
    url: str = Field(..., description="The url of the file.", unique=True)


class Track(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    user: str = Field(..., description="The owner of the file.", index=True)
    upload: FileData = Field(..., description="The file data of the track.")
    duration: float = Field(..., description="The duration of the track.", index=True)
    title: str = Field(..., description="The title of the track.", index=True)
    cover: str = Field(..., description="The cover of the track.")
    description: str = Field(..., description="The description of the track.")


class Image(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    user: str = Field(..., description="The owner of the file.", index=True)
    upload: FileData = Field(..., description="The file data of the image.")
    title: str = Field(..., description="The title of the image.", index=True)
    description: str = Field(..., description="The description of the image.")


class Video(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    user: str = Field(..., description="The owner of the file.", index=True)
    upload: FileData = Field(..., description="The file data of the video.")
    duration: float = Field(..., description="The duration of the video.", index=True)
    title: str = Field(..., description="The title of the video.", index=True)
    description: str = Field(..., description="The description of the video.")


class DataVisualization(FaunaModel):
    labels: List[str] = Field(default_factory=list)
    datasets: list = Field(default_factory=list)
    namespace: str = Field(..., description="The namespace id.", index=True)


class BlogPost(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    user: str = Field(..., description="The owner of the file.", index=True)
    title: str = Field(..., description="The title of the blog post.", index=True)
    content: str = Field(..., description="The content of the blog post.")
    cover: Optional[str] = Field(
        default=None, description="The cover of the blog post."
    )
    description: str = Field(..., description="The description of the blog post.")
    theme: str = Field(
        default="light", description="The theme of the blog post.", index=True
    )
    category: str = Field(
        default="general", description="The category of the blog post.", index=True
    )
    tags: Optional[List[str]] = Field(default=None, index=True)


class BookOrDocument(FaunaModel):
    namespace: str = Field(..., description="The namespace id.", index=True)
    title: str = Field(..., description="The title of document.", index=True)
    wordcloud: List[WordCount] = Field(
        ..., description="The wordcloud of the document.", index=True
    )
    file: Optional[FileData] = Field(
        default=None, description="The file of the document.", index=True
    )
    audio: Optional[str] = Field(
        default=None, description="The audio of the document.", unique=True
    )
    cover: Optional[str] = Field(
        default=None, description="The image of the document.", unique=True
    )


class DatabaseKey(FaunaModel):
    """

    Fauna Database Key

    """

    user: str = Field(..., unique=True)
    database: str = Field(...)
    global_id: str = Field(...)
    key: str = Field(...)
    secret: str = Field(...)
    hashed_secret: str = Field(...)
    role: str = Field(...)
