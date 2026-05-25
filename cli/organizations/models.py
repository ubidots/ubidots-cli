from pydantic import BaseModel


class OrganizationCreatePayload(BaseModel):
    name: str


class OrganizationUpdatePayload(BaseModel):
    name: str | None = None


class OrgUserAddPayload(BaseModel):
    user: str
