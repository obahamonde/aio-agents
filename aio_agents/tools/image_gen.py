from ..config import env
from ..data import *
from ..schemas import *
from ..services import *
from ..utils import s3


class ImageGeneration(FunctionDocument):
	prompt: str = Field(..., description="The user input text")
	url: Optional[str] = Field(default=None, description="The url of the image that was generated")

	@property
	def llm(self):
		return LLMStack()

	@process_time
	@handle_errors
	async def run(self, **kwargs: Any) -> Any:
		url = await self.llm.create_image(self.prompt)
		async with ClientSession() as session:
			async with session.get(url) as response:
				data = await response.read()
				_id = str(uuid4())
				s3.put_object(Body=data, Bucket=env.AWS_S3_BUCKET, Key=_id+".png", ContentType="image/png", ACL="public-read", ContentDisposition="inline")
				_url = f"https://s3.amazonaws.com/{env.AWS_S3_BUCKET}/{_id}.png"
				await FileData(
					namespace="default",
					user="agent",
					size=len(data),
					content_type="image/png",
					name=_id+".png",
					url=_url,
				).save()
				return _url