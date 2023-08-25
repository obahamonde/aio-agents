from collections import Counter

from aiofauna import *

from aiofauna_llm import *

from ..context import *
from ..schemas import *
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
            word_count = Counter()
            async for i, chunk in loader(file):
                await self.llm.ingest(texts=[chunk], namespace=namespace)
                doc = nlp(chunk)
                words = [
                    token.text.lower()
                    for token in doc
                    if token.is_alpha and not token.is_stop
                ]
                word_count.update(words)
                logger.info("Progress: %s", i)
            sorted_word_count = sorted(
                word_count.items(), key=lambda x: x[1], reverse=True
            )
            return [
                {"word": word, "count": count} for word, count in sorted_word_count[:25]
            ]

        @self.post("/load/website/{namespace}")
        async def load_website(url: str, namespace: str):
            """Loads a website and returns a list of pages"""
            async for i, chunk in website_loader(url):
                await self.llm.ingest(texts=[chunk], namespace=namespace)
                logger.info("Progress: %s", i)
            return {"message": "Success"}
