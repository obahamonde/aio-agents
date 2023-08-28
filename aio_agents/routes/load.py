import json

import pandas as pd
from aiofauna import *

from ..data import *
from ..helpers import *
from ..tools import *
from ..utils import *

logger = setup_logging(__name__)


class LoadRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(prefix="/api", tags=["Load"], *args, **kwargs)
        self.llm = LLMStack()

        @self.post("/load/document/{namespace}")
        async def load_pdf(namespace: str, file: FileField):
            """Loads a PDF file and returns a list of pages"""
            if "pdf" in file.content_type:
                loader = pdf_loader
            else:
                loader = text_loader
            text = ""
            async for i, chunk in loader(file):
                await self.llm.ingest(texts=[chunk], namespace=namespace)
                text += chunk
            wordcounts = word_cloud(text)
            upload_file = await upload_handler(
                file=file, user="agent", namespace=namespace
            )
            response = await BookOrDocument(
                namespace=namespace,
                title=upload_file.name,
                file=upload_file,
                wordcloud=[WordCount(**wordcount) for wordcount in wordcounts],
            ).save()
            logger.info("Response: %s", response)
            return response

        @self.post("/load/website/{namespace}")
        async def load_website(url: str, namespace: str):
            """Loads a website and returns a list of pages"""
            async for i, chunk in website_loader(url):
                await self.llm.ingest(texts=[chunk], namespace=namespace)
                logger.info("Progress: %s", i)
            return {"message": "Success"}

        @self.post("/load/csv/{namespace}")
        async def load_csv(namespace: str, file: FileField):
            """Loads a CSV file and returns a list of pages"""
            df = pd.read_csv(file.file)
            json_data = df.to_json(orient="records")
            data = json.loads(json_data)
            datasets = [list(d.values()) for d in data]
            labels = list(data[0].keys())
            return await DataVisualization(
                namespace=namespace, labels=labels, datasets=datasets
            ).save()

        @self.get("/books/{namespace}")
        async def get_book(namespace: str):
            """Gets a book"""
            return await BookOrDocument.find_many(namespace=namespace)

        @self.get("/load/urls")
        async def get_urls(url: str):
            """Gets a book"""
            async with ClientSession() as session:
                return await sitemap(url=url, session=session)
