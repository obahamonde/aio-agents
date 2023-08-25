from aiofauna import Document, Field


class WordCount(Document):
    word: str = Field(...)
    count: int = Field(...)
