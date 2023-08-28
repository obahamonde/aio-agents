from aiofauna import *
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module


class WordCount(BaseModel):
    word: str = Field(...)
    count: int = Field(...)


class DNSMeta(Document):
    auto_added: bool
    managed_by_apps: bool
    managed_by_argo_tunnel: bool
    source: str


class DNSRecord(Document):
    comment: Optional[str]
    content: str
    created_on: str
    id: str
    locked: bool
    meta: DNSMeta
    modified_on: str
    name: str
    proxiable: bool
    proxied: bool
    tags: List[str] = Field(default_factory=list)
    ttl: int
    type: str
    zone_id: str
    zone_name: str
