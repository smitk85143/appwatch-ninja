from ninja import Schema
from pydantic import field_validator

class KeywordNumberSchema(Schema):
    keyword: str
    number: int


class KeywordPerformanceRequestSchema(Schema):
    store: str
    app_id: str
    country: str


class KeywordSuggestionRequestSchema(Schema):
    keyword: str
    country: str
    

class KeywordListRequestSchema(Schema):
    desc: str


class KeywordFloatSchema(Schema):
    keyword: str
    number: float


class CountryRatingSchema(Schema):
    country_code: str
    rating: float


class AppidStoreSchema(Schema):
    app_id: str
    store: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ['google', 'apple']:
            raise ValueError("Invalid store name")
        return value