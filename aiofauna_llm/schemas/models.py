from aiofauna import *


class User(FaunaModel):
    """
    Auth0 User, Github User or Cognito User
    """

    email: Optional[str] = Field(default=None, index=True)
    email_verified: Optional[bool] = Field(default=False)
    family_name: Optional[str] = Field(default=None)
    given_name: Optional[str] = Field(default=None)
    locale: Optional[str] = Field(default=None, index=True)
    name: str = Field(...)
    nickname: Optional[str] = Field(default=None)
    picture: Optional[str] = Field(default=None)
    sub: str = Field(..., unique=True)
    updated_at: Optional[str] = Field(default=None)
