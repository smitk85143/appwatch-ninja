from ninja import Schema
from pydantic import field_validator

class RequestOllamaSchema(Schema):
    store: str
    app_id: str
    message: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ['google', 'apple']:
            raise ValueError("Invalid store name")
        return value
    

class RequestDeveloperSchema(Schema):
    store: str
    dev_id: str
    message: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ['google', 'apple']:
            raise ValueError("Invalid store name")
        return value
    

class RequestNormalSchema(Schema):
    message: str
    conversation_id: str | None = None