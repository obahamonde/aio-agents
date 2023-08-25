from __future__ import annotations

from uuid import uuid4

from aiofauna import Document
from pydantic import Field

from .typedefs import List, MetaData, Query, Value, Vector


class QueryBuilder:
    """Query builder for Pinecone Query API with MongoDB-like syntax."""

    def __init__(self, field: str = None, query: Query = None):  # type: ignore
        self.field = field
        self.query = query if query else {}

    def __repr__(self) -> str:
        return f"{self.query}"

    def __call__(self, field_name: str) -> QueryBuilder:
        return QueryBuilder(field_name)

    def __and__(self, other: QueryBuilder) -> QueryBuilder:
        return QueryBuilder(query={"$and": [self.query, other.query]})

    def __or__(self, other: QueryBuilder) -> QueryBuilder:
        return QueryBuilder(query={"$or": [self.query, other.query]})

    def __eq__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$eq": value}})

    def __ne__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$ne": value}})

    def __lt__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$lt": value}})

    def __le__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$lte": value}})

    def __gt__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$gt": value}})

    def __ge__(self, value: Value) -> QueryBuilder:
        return QueryBuilder(query={self.field: {"$gte": value}})

    def in_(self, values: List[Value]) -> QueryBuilder:
        """MongoDB-like syntax for $in operator."""
        return QueryBuilder(query={self.field: {"$in": values}})

    def nin_(self, values: List[Value]) -> QueryBuilder:
        """MongoDB-like syntax for $nin operator."""
        return QueryBuilder(query={self.field: {"$nin": values}})


class UpsertRequest(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    values: Vector = Field(...)
    metadata: MetaData = Field(...)


class Embedding(Document):
    values: Vector = Field(...)
    metadata: MetaData = Field(...)


class QueryRequest(Document):
    topK: int = Field(default=10)
    filter: dict = Field(...)
    includeMetadata: bool = Field(default=True)
    vector: Vector = Field(...)


class QueryMatch(Document):
    id: str = Field(...)
    score: float = Field(...)
    metadata: MetaData = Field(...)


class QueryResponse(Document):
    matches: List[QueryMatch] = Field(...)


class UpsertResponse(Document):
    upsertedCount: int = Field(...)
