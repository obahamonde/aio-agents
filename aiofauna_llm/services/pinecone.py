"""Pinecone API Client for the cheap developers."""
from __future__ import annotations

from dataclasses import dataclass, field
from os import environ
from typing import List

from aiofauna import APIClient
from aiohttp import ClientSession
from dotenv import load_dotenv

from ..schemas.pinecone import (
    Embedding,
    MetaData,
    Query,
    QueryBuilder,
    QueryMatch,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    Vector,
)

load_dotenv()


@dataclass(init=True, repr=True, unsafe_hash=False, frozen=False)
class PineconeClient(APIClient):
    """
    Cheapcone went greedy and removed the namespace feature from the free tier so let's query the API directly with MongoDB Filter Expressions.
    Also it's a good example of streamlining the development of API clients.
    """

    base_url: str = field(default=environ["PINECONE_API_URL"], init=True, repr=True)
    api_key: str = field(default=environ["PINECONE_API_KEY"], init=True, repr=False)

    def __load__(self) -> ClientSession:
        """Lazy load the client session."""
        return ClientSession(base_url=self.base_url, headers={"api-key": self.api_key})

    async def upsert(self, embeddings: List[Embedding]) -> UpsertResponse:
        """
        upsert
        Upsert embeddings into the vector index.

        Args:
            embeddings (List[Embedding]): Embeddings to upsert.

        Returns:
            UpsertResponse: Upsert response.
        """
        async with self.__load__() as session:
            values: List[Vector] = []
            metadata: List[MetaData] = []
            for embedding in embeddings:
                values.append(embedding.values)
                metadata.append(embedding.metadata)

            async with session.post(
                "/vectors/upsert",
                json={
                    "vectors": [
                        UpsertRequest(values=values, metadata=metadata).dict()
                        for values, metadata in zip(values, metadata)
                    ]
                },
            ) as response:
                return UpsertResponse(**await response.json())

    async def query(
        self, expr: Query, vector: Vector, includeMetadata: bool = True, topK: int = 4
    ) -> QueryResponse:
        """query
        Query the vector index.

        Args:
            expr (Query): Query expression.
            vector (Vector): Query vector.
            includeMetadata (bool, optional): Whether to include metadata in the response. Defaults to True.
            topK (int, optional): Number of results to return. Defaults to 10.

        Returns:
            QueryResponse: Query response.
        """
        async with self.__load__() as session:
            payload = QueryRequest(
                topK=topK,
                filter=expr,
                vector=vector,
                includeMetadata=includeMetadata,
            ).dict()
            async with session.post(
                "/query",
                json=payload,
            ) as response:
                return QueryResponse(**await response.json())
