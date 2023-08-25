from typing import *

from aiofauna import *

from .typedefs import *


class ChatMessage(Document):
    role: Role = Field(..., description="The role of the message")
    content: str = Field(..., description="The content of the message")


class ChatCompletionRequest(Document):
    model: Model = Field(..., description="The model to use for the completion")
    messages: List[ChatMessage] = Field(
        ..., description="The messages to use for the completion"
    )
    temperature: float = Field(
        default=0.2, description="The temperature of the completion"
    )
    max_tokens: int = Field(
        1024, description="The maximum number of tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the completion or not")


class ChatCompletionUssage(Document):
    prompt_tokens: int = Field(..., description="The number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="The number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="The total number of tokens")


class ChatCompletionChoice(Document):
    index: int = Field(..., description="The index of the choice")
    message: ChatMessage = Field(..., description="The message of the choice")
    finish_reason: str = Field(..., description="The reason the choice was finished")


class ChatCompletionResponse(Document):
    id: str = Field(..., description="The id of the completion")
    object: str = Field(..., description="The object of the completion")
    created: int = Field(..., description="The creation time of the completion")
    model: Model = Field(..., description="The model used for the completion")
    choices: List[ChatCompletionChoice] = Field(
        ..., description="The choices of the completion"
    )
    usage: ChatCompletionUssage = Field(..., description="The usage of the completion")
    stream: bool = Field(..., description="Whether the completion was streamed or not")


class VectorResponse(Document):
    text: str = Field(..., description="The text of the completion")
    score: float = Field(..., description="The score of the completion")


class CreateImageResponse(Document):
    created: float = Field(...)
    data: List[Dict[Format, str]] = Field(...)


class CreateImageRequest(Document):
    """Creates an Image using Dall-E model from OpenAI.
    must use default values unless user prompts for a different configuration,
    will be use in case the user asks for an image that is not a logo or a photo.
    """

    prompt: str = Field(...)
    n: int = Field(default=1)
    size: Size = Field(default="1024x1024")
    response_format: Format = Field(default="url")
