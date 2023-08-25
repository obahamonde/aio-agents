import base64
import json

from dotenv import load_dotenv
from pydantic import BaseConfig, BaseSettings
from pydantic import Field as Data

load_dotenv()


class AWSCredentials(BaseSettings):
    """AWS credentials for boto3"""

    class Config(BaseConfig):
        """Extra config for AWS credentials"""

        env_file = ".env"
        env_file_encoding = "utf-8"

    AWS_ACCESS_KEY_ID: str = Data(..., env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Data(..., env="AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION: str = Data(..., env="AWS_DEFAULT_REGION")

    secret: str = Data(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secret = base64.b64encode(json.dumps(self.dict()).encode("utf-8")).decode(
            "utf-8"
        )

    def dict(self):
        return {
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
            "region_name": self.AWS_DEFAULT_REGION,
        }


credentials = AWSCredentials().dict()


class Env(BaseSettings):
    """Environment Variables"""

    class Config(BaseConfig):
        env_file = ".env"
        env_file_encoding = "utf-8"

    FAUNA_SECRET: str = Data(..., env="FAUNA_SECRET")
    AUTH0_URL: str = Data(..., env="AUTH0_URL")
    OPENAI_API_KEY: str = Data(..., env="OPENAI_API_KEY")
    PINECONE_API_KEY: str = Data(..., env="PINECONE_API_KEY")
    PINECONE_API_URL: str = Data(..., env="PINECONE_API_URL")
    GH_API_TOKEN: str = Data(..., env="GH_API_TOKEN")
    AWS_S3_BUCKET: str = Data(..., env="AWS_S3_BUCKET")
    AWS_LAMBDA_ROLE: str = Data(..., env="AWS_LAMBDA_ROLE")
    AWS_ECR_URL: str = Data(..., env="AWS_ECR_URL")
    GH_CLIENT_ID: str = Data(..., env="GH_CLIENT_ID")
    GH_CLIENT_SECRET: str = Data(..., env="GH_CLIENT_SECRET")
    CF_API_KEY: str = Data(..., env="CF_API_KEY")
    CF_EMAIL: str = Data(..., env="CF_EMAIL")
    CF_ZONE_ID: str = Data(..., env="CF_ZONE_ID")
    CF_ACCOUNT_ID: str = Data(..., env="CF_ACCOUNT_ID")
    IP_ADDR: str = Data(..., env="IP_ADDR")
    REDIS_URL: str = Data(..., env="REDIS_URL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


env = Env()
