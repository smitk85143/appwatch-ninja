from ninja import Schema, ModelSchema
from pydantic import field_validator

from .models import AiConversation

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


class ResponseConversationSchema(Schema):
    conversation_id: str
    conversation_title: str
    status: str

class ResponseNormalSchema(ModelSchema):

    class Meta:
        model = AiConversation
        fields = ['conversation_end', 'conversation_data', 'status']