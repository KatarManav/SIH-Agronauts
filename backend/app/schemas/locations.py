from pydantic import BaseModel

from app.schemas.common import LocationResponse


class LocationListResponse(BaseModel):
    locations: list[LocationResponse]
