from ninja import Schema, ModelSchema
from pydantic import field_validator

from .models import ASORequest

class AddToWatchlistSchema(Schema):
    app_id: str
    store: str
    watchlist_type: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ["google", "apple"]:
            raise ValueError("Invalid store")
        return value
    
    @field_validator("watchlist_type")
    def validate_watchlist_type(cls, value):
        if value not in ["add", "remove"]:
            raise ValueError("Invalid watchlist type")
        return value



class ASORequestSchema(ModelSchema):
    class Meta:
        model = ASORequest
        exclude = ['id', 'timestamp', 'updated', 'user', 'approved']


class AddDesireAppSchema(Schema):
    app_id: str
    store: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ["google", "apple"]:
            raise ValueError("Invalid store")
        return value