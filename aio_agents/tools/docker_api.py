from dataclasses import field

from aiofauna import *
from pydantic import Field

from ..config import env
from ..data import *
from ..schemas import *
from ..utils import nginx_config, parse_env_string, random_port

logger = setup_logging(__name__)


async def get_database_key(ref: str):
    """Get the database key"""
    try:
        instance = await DatabaseKey.find_unique(user=ref)

        if isinstance(instance, DatabaseKey):
            return instance
        fql = FaunaClient()
        # Create a new database
        database = await fql.query(q.create_database({"name": ref}))
        global_id = database["global_id"]
        db_ref = database["ref"]["@ref"]["id"]
        # Create a new key
        key = await fql.query(
            q.create_key({"database": q.database(db_ref), "role": "admin"})
        )
        key_ref = key["ref"]["@ref"]["id"]
        secret = key["secret"]
        hashed_secret = key["hashed_secret"]
        role = key["role"]
        return await DatabaseKey(
            user=ref,
            database=db_ref,
            global_id=global_id,
            key=key_ref,
            secret=secret,
            hashed_secret=hashed_secret,
            role=role,
        ).save()
    except Exception as e:
        return {"message": str(e), "status": "error"}


class DockerClient(APIClient):
    base_url: str = field(default="http://localhost:9898")
    headers: Dict[str, str] = field(
        default_factory=lambda: {"Accept": "application/json"}
    )

    async def create_container(
        self, name: str, envir: str, image="codeserver", port=8443
    ) -> str:
        host_port = random_port()
        response = await self.fetch(
            "/containers/create",
            method="POST",
            json={
                "Image": image,
                "ExposedPorts": {f"{port}/tcp": {}},
                "HostConfig": {
                    "PortBindings": {f"{port}/tcp": [{"HostPort": str(host_port)}]}
                },
                "Env": parse_env_string(envir),
                "Name": name,
            },
        )
        id_ = response["Id"]
        logger.info("Created container %s", id_)
        return id_, host_port

    async def start_container(self, container_id: str):
        return await self.text(f"/containers/{container_id}/start", method="POST")

    async def inspect_container(self, container_id: str) -> Dict[str, Any]:
        return await self.fetch(f"/containers/{container_id}/json")

    async def pipeline(
        self, name: str, user: str, port: int = 8443, image: str = "codeserver"
    ) -> int:
        database = await get_database_key(ref=user)
        fauna_secret = database.secret
        env_vars = f"FAUNA_SECRET={fauna_secret} DOCKER=1"
        id_, host_port = await self.create_container(name, env_vars, image, port)
        await self.start_container(id_)
        return host_port


class CloudFlareClient(APIClient):
    base_url: str = field(default="https://api.cloudflare.com")
    headers: Dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "application/json",
            "X-Auth-Key": env.CF_API_KEY,
            "X-Auth-Email": env.CF_EMAIL,
        }
    )

    @handle_errors
    async def list_dns_records(self):
        response = await self.fetch(f"/client/v4/zones/{env.CF_ZONE_ID}/dns_records")
        return [DNSRecord(**record) for record in response["result"]]

    async def create_dns_record(self, name: str, ip: str):
        await self.fetch(
            f"/client/v4/zones/{env.CF_ZONE_ID}/dns_records",
            method="POST",
            json={"type": "A", "name": name, "content": ip, "ttl": 1, "proxied": True},
        )

    @handle_errors
    async def get_dns_record(self, name: str):
        response = await self.fetch(f"/client/v4/zones/{env.CF_ZONE_ID}?name={name}")
        return DNSRecord(**response["result"])

    @handle_errors
    async def delete_dns_record(self, id: str):
        await self.text(
            f"/client/v4/zones/{env.CF_ZONE_ID}/dns_records/{id}", method="DELETE"
        )

    @handle_errors
    async def update_dns_record(self, id: str, name: str, ip: str):
        response = await self.fetch(
            f"/client/v4/zones/{env.CF_ZONE_ID}/dns_records/{id}",
            method="PUT",
            json={"type": "A", "name": name, "content": ip, "ttl": 1, "proxied": True},
        )
        return DNSRecord(**response["result"])


docker = DockerClient()  # pylint: disable=E1120
cloudflare = CloudFlareClient()  # pylint: disable=E1120


class CodeServer(FunctionDocument):
    """Creates a Visual Studio Code Server instance."""

    namespace: str = Field(
        ..., description="The namespace or subdomain, must be lowercase."
    )
    url: Optional[str] = Field(default=None, description="The url of the codeserver.")
    port: int = Field(default=8443, description="The port of the codeserver.")
    image: str = Field(default="codeserver", description="The image of the codeserver.")

    async def run(self):
        self.url = f"https://{self.namespace.lower()}.aiofauna.com"
        port = await docker.pipeline(
            self.namespace, self.namespace, self.port, self.image
        )
        await cloudflare.create_dns_record(self.namespace.lower(), env.IP_ADDR)
        nginx_config(self.namespace, port)
        return self.url
