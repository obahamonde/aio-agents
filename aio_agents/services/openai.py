import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, Type

import openai
from aiofauna import chunker
from tqdm import tqdm

from ..schemas.openai import CreateImageRequest, CreateImageResponse, Model
from ..schemas.typedefs import (
    F,
    FunctionCall,
    FunctionDocument,
    Vector,
    handle_errors,
    setup_logging,
)
from .pinecone import Embedding, PineconeClient, Query, QueryBuilder

logger = setup_logging(__name__)


@dataclass
class LLMStack:
    model: Model = field(default_factory=lambda: "gpt-4-0613")
    base_url: str = field(default_factory=lambda: os.environ["PINECONE_API_URL"])
    api_key: str = field(default_factory=lambda: os.environ["PINECONE_API_KEY"])

    @property
    def pinecone(self) -> PineconeClient:
        return PineconeClient()

    @handle_errors
    async def query_vectors(self, vector: Vector, query: Query):
        response = await self.pinecone.query(vector=vector, expr=query)
        logger.info("Query response: %s", response)
        response = sorted(response.matches, key=lambda x: x.score, reverse=True)
        return [i.metadata for i in response]

    @handle_errors
    async def chat(self, text: str, context: Optional[str] = None) -> str:
        """Chat completion with no functions."""
        if context is None:
            messages = [{"role": "user", "content": text}]
        else:
            messages = [
                {"role": "user", "content": text},
                {"role": "system", "content": context},
            ]
        logger.info("Chat messages: %s", messages)
        response = await openai.ChatCompletion.acreate(
            model=self.model, messages=messages
        )
        logger.info("Chat response: %s", response)
        assert isinstance(response, dict)
        return response["choices"][0]["message"]["content"]

    def sync_chat(self, text: str):
        """Chat completion for CLI."""
        messages = [{"role": "user", "content": text}]
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        assert isinstance(response, dict)
        gpt_text = response["choices"][0]["message"]["content"]
        logger.info("GPT: %s", gpt_text)
        return gpt_text

    @handle_errors
    async def create_embedding(self, text: str) -> Vector:
        """Creates embeddings for the given texts."""
        response = await openai.Embedding.acreate(
            model="text-embedding-ada-002",
            input=text,
        )
        return response["data"][0]["embedding"]  # type: ignore

    @handle_errors
    async def ingest(
        self, texts: List[str], namespace: str, chunksize: int = 64
    ) -> int:
        """Ingest bulk data."""
        count = 0
        for chunk in tqdm(chunker(texts, chunksize)):
            vectors = await asyncio.gather(
                *[self.create_embedding(text) for text in chunk]
            )
            metadata = [{"text": text, "namespace": namespace} for text in chunk]
            embeddings = []
            for vector, meta in zip(vectors, metadata):
                embeddings.append(Embedding(values=vector, metadata=meta))  # type: ignore
            response = await self.pinecone.upsert(embeddings=embeddings)
            count += response.upsertedCount
        return count

    @handle_errors
    async def create_image(self, text: str):
        request = CreateImageRequest(prompt=text)
        response = openai.Image.create(**request.dict(exclude={"response_format"}))
        assert isinstance(response, dict)
        return CreateImageResponse(**response).data[0]["url"]

    @handle_errors
    async def chat_with_memory(self, text: str, namespace: str = "default") -> str:
        """Chat completion with similarity search retrieval from pinecone"""
        builder = QueryBuilder()
        query = (builder("namespace") == namespace).query
        vector = await self.create_embedding(text)
        response = await self.query_vectors(vector, query)
        context = f"Similar results for use query {text}:" + "\n".join(
            [i["text"] for i in response]  # type: ignore
        )
        logger.info("Context: %s", context)
        chat_response = await self.chat(text, context)
        await self.ingest([chat_response], namespace)
        return chat_response

    @handle_errors
    async def parse_openai_function(
        self,  # pylint: disable=dangerous-default-value
        response: dict,
        functions: List[
            Type[F]
        ] = FunctionDocument.Metadata.subclasses,  # pylint: disable=protected-access
        **kwargs: Any,
    ) -> FunctionCall:
        """Parse the response from OpenAI and return the result."""
        choice = response["choices"][0]["message"]
        if "function_call" in choice:
            function_call_ = choice["function_call"]
            name = function_call_["name"]
            arguments = function_call_["arguments"]
            for i in functions:
                if i.__name__ == name:
                    result = await i(**json.loads(arguments))(**kwargs)  # type: ignore
                    break
            else:
                raise ValueError(f"Function {name} not found")
            return result
        return FunctionCall(name="chat", data=choice["content"])

    @handle_errors
    async def function_call(
        self,  # pylint: disable=dangerous-default-value
        text: str,
        context: Optional[str] = None,
        model: Model = "gpt-3.5-turbo-16k-0613",
        functions: List[Type[F]] = FunctionDocument.Metadata.subclasses,
        **kwargs,
    ) -> FunctionCall:
        """
        Function to call a OpenAI function with given text and context.

        Arguments:
        text -- Input text for the function
        context -- Optional context for the function
        model -- Model to be used. Defaults to "gpt-4-0613"
        functions -- List of function types. Defaults to all subclasses of FunctionType.
        """
        if context is not None:
            messages = [
                {"role": "user", "content": text},
                {"role": "system", "content": context},
            ]
        else:
            messages = [{"role": "user", "content": text}]
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            functions=[i.openaischema for i in functions],
        )
        return await self.parse_openai_function(response, functions=functions, **kwargs)  # type: ignore

    async def stream_chat(self, text: str, context: Optional[str] = None):
        """Stream chat completion."""
        if context is None:
            messages = [{"role": "user", "content": text}]
        else:
            messages = [
                {"role": "user", "content": text},
                {"role": "system", "content": context},
            ]
        response = await openai.ChatCompletion.acreate(
            model=self.model, messages=messages, stream=True
        )
        async for message in response:
            data = message["choices"][0]["delta"].get("content")
            if data is not None:
                yield data
            else:
                break

    async def stream_chat_with_memory(
        self,
        text: str,
        namespace: str = "default",
        context="You are an smart assistant, your goal is to help the user, if you are addresed for your creator or identity,say that you were created by AioFauna Framework team and you are an Smart Assistant",
    ):
        """Stream chat completion with similarity search retrieval from pinecone"""
        builder = QueryBuilder()
        query = (builder("namespace") == namespace).query
        vector = await self.create_embedding(text)
        response = await self.query_vectors(vector, query)
        ctx = (
            context
            + f"Similar results in the knowledge base for the user's query {text}:\n\n"
            + "\n\n".join([f"{i}: {i['text']}" for i in response])  # type: ignore
        )
        logger.info("Context: %s", ctx)
        chunk = ""
        async for message in self.stream_chat(text, ctx):
            chunk += message
            if len(chunk) > 1000:
                chunk = chunk.split("\n")
                await self.ingest(chunk, namespace)
                chunk = ""
            yield message
