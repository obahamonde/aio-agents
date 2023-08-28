import json
from dataclasses import field
from os import environ

from aiofauna import APIClient
from aiohttp.web_exceptions import HTTPException

from ..data import *


class AuthClient(APIClient):
    base_url: str = field(default=environ["AUTH0_URL"])
    headers: dict = field(default_factory=lambda: {"Content-Type": "application/json"})

    async def user_info(self, token: str):
        try:
            user_dict = await self.update_headers(
                {"Authorization": f"Bearer {token}"}
            ).get("/userinfo")
            assert isinstance(user_dict, dict)
            return await User(**user_dict).save()

        except (AssertionError, HTTPException) as exc:
            return HTTPException(
                text=json.dumps({"status": "error", "message": str(exc)})
            )
