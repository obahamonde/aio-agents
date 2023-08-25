import aiohttp_cors
from boto3 import Session

from aiofauna_llm import *
from src import *
from src.config import env

llm = LLMStack()
s3 = Session().client("s3")
app = APIServer(servers=[{"url": "http://localhost:5000"}], client_max_size=2**21)


@app.sse("/api/chat/{namespace}")
async def chat_endpoint(text: str, namespace: str, sse: EventSourceResponse):
    async for response in llm.stream_chat_with_memory(text, namespace):
        await sse.send(response)
    done_event = "event: done\ndata: Done writing response\n\n"
    await sse.send(done_event, event="done")
    return sse


@app.post("/api/upload/{namespace}")
async def upload_endpoint(user: str, size: float, namespace: str, file: FileField):
    bucket = env.AWS_S3_BUCKET
    key = f"{namespace}/{user}/{file.filename}"
    data = file.file.read()
    content_type = file.content_type
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    url = f"https://s3.amazonaws.com/{bucket}/{key}"
    return await FileData(
        user=user,
        namespace=namespace,
        name=file.filename,
        size=size,
        content_type=content_type,
        url=url,
    ).save()


cors = aiohttp_cors.setup(
    app,
    defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    },
)


app.use(ChatRouter()).use(LoadRouter())

for route in list(app.router.routes()):
    cors.add(route)
