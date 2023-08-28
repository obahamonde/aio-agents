from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Type, TypeVar, Union

from aiofauna import Document, handle_errors, setup_logging
from aiofauna.utils import process_time
from pydantic import BaseModel  # pylint: disable=no-name-in-module

from ..utils import snakify

Role = Literal["assistant", "user", "system", "function"]
Model = Literal["gpt-4-0613", "gpt-3.5-turbo-16k-0613"]
Size = Literal["256x256", "512x512", "1024x1024"]
Format = Literal["url", "base64"]
Vector = List[float]
Value = Union[str, int, float, bool, List[str]]
MetaData = Dict[str, Value]
Filter = Literal["$eq", "$ne", "$lt", "$lte", "$gt", "$gte", "$in", "$nin"]
AndOr = Literal["$and", "$or"]
Query = Union[
    Dict[str, Union[Value, "Query", List["Query"]]],
    Dict[Filter, Value],
    Dict[AndOr, List["Query"]],
]
Size = Literal["256x256", "512x512", "1024x1024"]
Format = Literal["url", "b64_json"]

logger = setup_logging(__name__)

F = TypeVar("F", bound="FunctionDocument")


class FunctionCall(Document):
    name: str
    data: Any


class FunctionDocument(BaseModel, ABC):
    class Metadata:
        subclasses: List[Type[F]] = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        logger.debug("OpenAI Function %s called", self.__class__.__name__)

    @classmethod
    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        cls.__name__ = snakify(cls.__name__)
        _schema = cls.schema()
        if cls.__doc__ is None:
            cls.__doc__ = f"```json\n{cls.schema_json(indent=2)}\n```"
        cls.openaischema = {
            "name": cls.__name__,
            "description": cls.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    k: v for k, v in _schema["properties"].items() if k != "self"
                },
                "required": [
                    k
                    for k, v in _schema["properties"].items()
                    if v.get("required", False)
                ],
            },
        }
        logger.debug("%s function schema: %s", cls.__name__, cls.openaischema)
        cls.Metadata.subclasses.append(cls)

    @process_time
    @handle_errors
    async def __call__(self, **kwargs: Any) -> FunctionCall:
        response = await self.run(**kwargs)

        name = snakify(self.__class__.__name__)

        return FunctionCall(name=name, data=response)

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        ...


F = TypeVar("F", bound=FunctionDocument)
