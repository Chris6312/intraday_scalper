from pydantic import BaseModel, ConfigDict, Field


class PublicAccessTokenResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    access_token: str = Field(alias="accessToken", min_length=1)
