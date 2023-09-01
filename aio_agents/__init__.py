import aiohttp_cors
from aiofauna import *
from aiohttp.web import HTTPFound, HTTPNotFound
from aiohttp_sse import EventSourceResponse
from boto3 import Session
from dotenv import load_dotenv

from .config import *
from .data import *
from .helpers import *
from .routes import *
from .schemas import *
from .services import *
from .tasks import *
from .tools import *
from .utils import *

load_dotenv()


llm = LLMStack()
s3 = Session().client("s3")
app = APIServer(servers=[{"url": "https://www.aiofauna.com"}], client_max_size=2**22)


def create_app():
    @app.get("/")
    async def index(request):
        return Response(text=open("static/index.html").read(), content_type="text/html")

    @app.sse("/api/chat/{namespace}")
    async def chat_endpoint(text: str, namespace: str, sse: EventSourceResponse):
        async for response in llm.stream_chat_with_memory(text, namespace):
            await sse.send(response)
        done_event = "event: done\ndata: Done writing response\n\n"
        await sse.send(done_event, event="done")
        return sse

    @app.sse("/api/subscription/{namespace}")
    async def suscribe_endpoint(namespace: str, sse: EventSourceResponse):
        queue = FunctionQueue(namespace=namespace)
        while True:
            async for response in queue.sub():
                await sse.send(response)

    @app.post("/api/subscription/{namespace}")
    async def publish_endpoint(namespace: str, text: str):
        queue = FunctionQueue(namespace=namespace)
        await queue.pub(text)
        return {
            "status": "success",
            "message": f"message {text} sent to queue {namespace}",
        }

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

    @app.get("/api/audio/{text}")
    async def audio_endpoint(text: str):
        options = await Voice.assign(text=text)
        language = [option.LanguageCode for option in options][0]
        app.logger.info(f"Selected language {language}")
        polly = Polly(Text=text, LanguageCode=language)

        async def generator():
            async for chunk in polly.stream_audio():
                yield chunk

        return Response(body=generator(), headers={"Content-Type": "audio/mpeg"})

    @app.get("/api/functions")
    async def functions(request):
        return [i.openaischema for i in FunctionDocument.Metadata.subclasses]

    app.use(ChatRouter()).use(LoadRouter()).use(PaymentsRouter())

    app.router.add_static("/", "static")


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

    for route in list(app.router.routes()):
        cors.add(route)
        

    return app
