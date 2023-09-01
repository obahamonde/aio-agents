from aiofauna import *

from ..data import *
from ..schemas import *
from ..services import *

logger = setup_logging(__name__)

class ConversationMessage(BaseModel):
    """A full conversation message"""
    user:Optional[User] = Field(default=None)
    content: str = Field(...)

class Conversation(Document):
    """A conversation"""
    namespace:str = Field(...)
    title:Optional[str] = Field(default=None)
    participants:Optional[List[User]] = Field(default=[])
    messages:Optional[List[ConversationMessage]] = Field(default=[])

    async def fetch(self):
        """Fetches all the nested ids full information"""
        namespace = await Namespace.get(self.namespace)
        messages = await ChatMessage.find_many(namespace=self.namespace)
        messages_with_users = []
        for message in messages:
            user = await User.get(message.owner) if message.owner != "agent" else User(name="Agent", sub="agent", picture="/logo.png")  # type:ignore
            messages_with_users.append(
                ConversationMessage(
                    user=user,
                    content=message.content,
                )
            )
        return Conversation(
            namespace=namespace.ref,
            title=namespace.title,
            participants=await asyncio.gather(*[User.get(participant) for participant in namespace.participants]),
            messages=messages_with_users,
        )
    
class ChatRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(prefix="/api", tags=["Chat"], *args, **kwargs)
        self.llm = LLMStack()

        @self.post("/auth")
        async def auth_endpoint(request: Request):
            """Authenticates a user using Auth0 and saves it to the database"""
            token = request.headers.get("Authorization", "").split("Bearer ")[-1]
            user_dict = (
                await AuthClient()  # pylint: disable=E1120
                .update_headers({"Authorization": f"Bearer {token}"})
                .get("/userinfo")
            )
            user = User(**user_dict)
            return await user.save()

        @self.get("/namespace/new")
        async def namespace_create(user: str):
            """Creates a new namespace for a user"""
            return await Namespace(user=user, participants=[user]).save()  # type:ignore

        @self.get("/namespace/get/{namespace}")
        async def namespace_get(namespace: str):
            namespace_obj = await Namespace.get(namespace)
            if (
                namespace_obj.title == "[New Namespace]"
                and len(namespace_obj.messages) > 0
            ):
                first_prompt = (await ChatMessage.find_many(namespace=namespace))[0]
                await namespace_obj.set_title(first_prompt.content)
            return await Namespace.get(namespace)

        @self.get("/namespace/list")
        async def namespace_list(user: str):
            """Lists all namespaces for a user"""
            return await Namespace.find_many(user=user)

        @self.delete("/namespace")
        async def namespace_delete(id: str):
            """Deletes a namespace"""
            return await Namespace.delete(id)

        @self.get("/messages/audio")
        async def audio_response(text: str, namespace: str, lang: str = "en-US"):
            """Returns an audio response from a text"""
            text = await self.llm.chat_with_memory(
                text=text,
                namespace=namespace,
            )
            polly = Polly.load(text=text, language=lang)
            return Response(
                body=await polly.get_audio(),
                content_type="application/octet-stream",
            )

        @self.get("/messages/list/{namespace}")
        async def get_messages(namespace: str):
            """Returns a list of messages from a namespace"""
            return await ChatMessage.find_many(namespace=namespace)

        @self.post("/messages/{namespace}")
        async def post_message(namespace: str, message: ChatMessage):
            """Posts a message to a conversation"""
            instance = await message.save()
            namespace = await Namespace.get(namespace)
            await namespace.update(
                namespace.ref,
                messages=namespace.messages + [instance.ref],  # type:ignore
            )
            return instance


        @self.get("/namespace/fetch/{namespace}")
        async def fetch_messages(namespace: str)->Conversation:
            """Fetches messages from a namespace"""
            return await Conversation(
                namespace=namespace,
            ).fetch()