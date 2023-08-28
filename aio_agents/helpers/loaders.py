import csv
import io
from typing import AsyncGenerator, List, Tuple

from aiofauna import FileField, handle_errors, setup_logging
from aiohttp import ClientSession
from boto3 import client
from bs4 import BeautifulSoup  # pylint: disable=import-error
from pypdf import PdfReader  # pylint: disable=import-error

logger = setup_logging(__name__)
s3 = client("s3", region_name="us-east-1")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
BAD_EXT = (
    "png",
    "jpg",
    "jpeg",
    "gif",
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
    "zip",
    "rar",
    "gz",
    "7z",
    "exe",
    "mp3",
    "mp4",
    "avi",
    "mkv",
    "mov",
    "wmv",
    "flv",
    "swf",
)


@handle_errors
async def sitemap(url: str, session: ClientSession) -> List[str]:
    urls = []
    if not url.endswith("xml"):
        url = f"{url.rstrip('/')}/sitemap.xml"
    async with session.get(url) as response:
        text = await response.text()
        soup = BeautifulSoup(text, features="xml")
        for loc in soup.findAll("loc"):
            if loc.text.endswith(BAD_EXT):
                continue
            urls.append(loc.text)
            logger.info("Found url: %s", loc.text)
        for nested_sitemap in soup.findAll("sitemap"):
            urls.extend(await sitemap(nested_sitemap.loc.text, session))
    return urls


@handle_errors
async def fetch_website(url: str, session: ClientSession, max_size: int = 16000) -> str:
    async with session.get(url) as response:
        html = await response.text()
        truncated_html = html[:max_size]
        return BeautifulSoup(truncated_html, features="lxml").get_text(
            separator="\n", strip=True
        )


async def pdf_loader(file: FileField) -> AsyncGenerator[Tuple[float, str], None]:
    """Reads a PDF file from the request and returns a list of strings"""
    data = file.file.read()
    pdf = PdfReader(io.BytesIO(data))
    for page, index in enumerate(pdf.pages):
        text = index.extract_text()
        progress = page / len(pdf.pages)
        logger.info("Progress: %s", progress)
        yield progress, text


async def website_loader(url: str) -> AsyncGenerator[Tuple[float, str], None]:
    """Reads a website and returns a list of strings"""

    async with ClientSession(headers=HEADERS) as session:
        urls = await sitemap(url, session)
        for index, url in enumerate(urls):
            text = await fetch_website(url, session)
            progress = index / len(urls)
            logger.info("Progress: %s", progress)
            yield progress, text


async def text_loader(file: FileField) -> AsyncGenerator[Tuple[float, str], None]:
    """Reads a text file from the request and returns a list of strings"""
    data = file.file.read()
    for index, line in enumerate(data.decode("utf-8").splitlines()):
        progress = index / len(data)
        logger.info("Progress: %s", progress)
        yield progress, line
