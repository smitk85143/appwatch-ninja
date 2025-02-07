from typing import List
from ninja import Router
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async
from django.conf import settings
import configcatclient

from . import schemas, utils
from custom_account.security import AuthBearer
from .models import AiConversation, ConversationType

router = Router(auth=AuthBearer())
configcat_client = configcatclient.get(settings.CONFIGCAT_SDK_KEY)


@router.post("/app-conversation")
async def app_conversation(request, payload: schemas.RequestOllamaSchema):
    """
    Handles the Ollama interaction asynchronously.
    """
    my_setting_value = configcat_client.get_value('is_api_enabled', False)
    if not my_setting_value:
        return utils.create_error_response("Unable to process request, please try again later")
    user = request.user
    today_start, today_end = utils.get_today_time_range()

    conversation_limit, _ = await utils.get_or_update_conversation_limit(user, today_start, today_end)
    if conversation_limit.limit <= 0:
        return utils.create_error_response("Daily limit reached, for more limit contact us")

    conversation_limit.limit -= 1
    await sync_to_async(conversation_limit.save)()

    if not utils.is_valid_request(request.headers.get("User-Agent", "")):
        return utils.create_error_response("Unsupported User-Agent")
    if not payload.message:
        return utils.create_error_response("Invalid message")

    app_info, app_obj = await utils.retrieve_app_info_async(payload.store, payload.app_id)

    ai_conversation, _ = await utils.get_or_create_ai_conversation(user, app_obj)
    await utils.update_ai_conversation(ai_conversation, payload.message)

    messages = utils.prepare_messages(app_info, payload.message)

    response = StreamingHttpResponse(
        utils.generate_response_async(messages, ai_conversation, conversation_limit), 
        content_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache",
                 "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"}
    )
    return response


@router.post("/normal-conversation")
async def normal_conversation(request, payload: schemas.RequestNormalSchema):

    user = request.user
    today_start, today_end = utils.get_today_time_range()

    conversation_limit, _ = await utils.get_or_update_conversation_limit(user, today_start, today_end)
    if conversation_limit.limit <= 0:
        return utils.create_error_response("Daily limit reached, for more limit contact us")

    conversation_limit.limit -= 1
    await sync_to_async(conversation_limit.save)()

    if not utils.is_valid_request(request.headers.get("User-Agent", "")):
        return utils.create_error_response("Unsupported User-Agent")
    if not payload.message:
        return utils.create_error_response("Invalid message")
    ai_conversation, _ = await utils.get_or_create_ai_conversation(user, conversation_id=payload.conversation_id)
    await utils.update_ai_conversation(ai_conversation, payload.message)
    response = StreamingHttpResponse(
        utils.predict_react_agent_answer({'input': payload.message}, ai_conversation), 
        content_type="text/event-stream; charset=utf-8"
    )
    return response


@router.get("/all-normal-conversation", response=List[schemas.ResponseConversationSchema])
async def get_all_normal_conversation(request):
    user = request.user
    ai_conversations = await sync_to_async(list)(AiConversation.objects.filter(user=user, conversation_type=ConversationType.NORMAL))
    conversation_list = [ {"conversation_id": ai_conversation.slug, 'status': ai_conversation.status, "conversation_title": ai_conversation.conversation_title} 
                         for ai_conversation in ai_conversations]
    return conversation_list


@router.get("/normal-conversation", response=schemas.ResponseNormalSchema)
async def get_normal_conversation(request, conversation_id: str):
    user = request.user
    ai_conversation = await sync_to_async(AiConversation.objects.get)(slug=conversation_id, user=user)
    return ai_conversation