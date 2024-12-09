from ninja import ModelSchema, Schema
from pydantic import field_validator

from home.models import Genre

class GenreSchema(ModelSchema):
    class Meta:
        model = Genre
        fields = ['genreId', 'genre']


class RequestLeaderboardSchema(Schema):
    store: str
    category: str
    genre: str
    country: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ["google", "apple"]:
            raise ValueError("Invalid store")
        return value
    
    @field_validator("category")
    def validate_category(cls, value):
        if value not in ["free", "paid", "grossing"]:
            raise ValueError("Invalid category")
        return value
    

class ResponseLeaderboardSchema(Schema):
    id: str
    name: str
    icon: str
    rank: int
    store: str


class KeywordNumberSchema(Schema):
    keyword: str
    number: int