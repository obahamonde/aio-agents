from typing import TypeVar

from aiofauna import Document, FaunaModel
from jinja2 import Template
from pydantic import Field
from typing_extensions import ParamSpec

from ..data import *

T = TypeVar("T")
P = ParamSpec("P")


class Block(FaunaModel):
    id: str = Field(..., description="The id of the tiptap block", unique=True)
    content: str = Field(..., description="The content of the tiptap block")
    type: str = Field(..., description="The type of the tiptap block", index=True)


class TipTap(FaunaModel):
    namespace: str = Field(
        ..., description="The namespace of the tiptap block", index=True
    )
    user: str = Field(
        ..., description="The user that edited the tiptap block", index=True
    )
    block: Block = Field(..., description="The tiptap block")

    @classmethod
    async def fetch(cls, namespace: str):
        """Fetches all the blocks for a given namespace."""
        return await cls.find_many(namespace=namespace)


class TipTapHtml(Document):
    tiptap: TipTap = Field(..., description="The tiptap block")
    template: str = Field(..., description="The template of the tiptap block")

    async def render(self):
        """Renders the tiptap block."""
        template = Template(self.template)
        user = await User.get(self.tiptap.user)
        return template.render(tiptap=await self.tiptap.fetch(), user=user)
