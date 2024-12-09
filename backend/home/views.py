from typing import List
from ninja import Query, Router
from ninja.errors import HttpError
from django.db.models import Q
from asgiref.sync import sync_to_async
from haystack.query import SearchQuerySet
from django.http import StreamingHttpResponse
import json
import asyncio

from .paginations import CustomPaginator
from . import schemas
from .models import AppDetail, Developer
from .utils import developer_data, retrieve_app_info_async, generate_response_async
from custom_account.security import AuthBearer

router = Router()
    

@router.get("/apps", response=schemas.PaginatedResponseSchema)
async def list_apps(
    request,
    store: str = Query("google"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
):
    if store not in ["google", "apple"]:
        raise HttpError(400, "Invalid store")
    
    queryset = await sync_to_async(list)(
        AppDetail.objects.filter(
            Q(name__isnull=False) & Q(hide=False) & Q(store__name=store)
        ).select_related("genre", "store")
    )

    paginator = CustomPaginator(queryset, page_size, request)
    return paginator.get_paginated_response(page, schemas.AppListDetailSchema)


@router.post("/app", response=schemas.AppDetailSchema)
async def single_app(
    request,
    payload: schemas.AppidStoreSchema,
):
    try:
        queryset = await sync_to_async(lambda: AppDetail.objects.filter(
                Q(appID=payload.app_id) & Q(hide=False) & Q(store__name=payload.store)
            ).select_related('genre', 'developer', 'store').first())()
        
        return queryset
    except Exception:
        HttpError(500, "An error occurred while fetching app data")


@router.get("/developers", response=schemas.PaginatedResponseSchema)
async def list_developers(
    request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1)
):
    try:
        queryset = await sync_to_async(list)(Developer.objects.all().order_by('slug', 'developerId').distinct('slug', 'developerId'))

        paginator = CustomPaginator(queryset, page_size, request)
        return await paginator.get_paginated_response_for_developers(page, schemas.SingleDeveloperListSchema)

    except Exception as e:
        print(e)
        raise HttpError(500, "An error occurred while fetching developer data")
    

@router.post("/developer", response=schemas.DeveloperSchema)
async def single_Developer(
    request,
    payload: schemas.DeveloperSlugSchema,
):
    try:
        one_developer, data = await sync_to_async(developer_data)(payload.dev_id)
        if one_developer is None:
            raise HttpError(404, "Invaild Developer")
        
        response = {
            "developer": one_developer,
            "apps": data
        }
        
        return response
    except Exception:
        HttpError(500, "An error occurred while fetching app data")


@router.get("/search", response=List[schemas.AppSearchDetailSchema])
async def search_apps(request, q: str = Query(...)):
    if not q:
        return []

    try:
        results = await sync_to_async(list)(
            SearchQuerySet()
            .models(AppDetail)
            .filter(appID=q, hide='false') |
            SearchQuerySet()
            .models(AppDetail)
            .filter(name_ngram__icontains=q, hide='false')
        )
        results = [result for result in results[:8]]
        return results
    
    except Exception:
        raise HttpError(400, "Invalid query")


@router.post("/conversation", response=None, auth=AuthBearer())
async def ai_conversation(request, payload: schemas.RequestOllamaSchema):
    """
    Handles the Ollama interaction asynchronously.
    """
    user_agent = request.headers.get("User-Agent", "")
    print(user_agent)
    if "curl" in user_agent.lower():
        return StreamingHttpResponse(
            f"event: error\ndata: {json.dumps({'error': 'Unsupported User-Agent'})}\n\n",
            content_type="text/event-stream; charset=utf-8",
        )
    if not payload.message:
        return StreamingHttpResponse(
            f"event: error\ndata: {json.dumps({'error': 'Invalid message'})}\n\n",
            content_type="text/event-stream; charset=utf-8",
        )

    app_info = await retrieve_app_info_async(payload.store, payload.app_id)

    if "error" not in app_info:
        app_context = (
            "system",
            "You are an intelligent assistant specializing in providing detailed and accurate information about mobile applications. "
            "You can answer user queries regarding app details, such as the app's name, description, rating, developer, genre, installs, and other relevant features. "
            "Please provide concise, informative, and professional responses. If a user asks about something unrelated to apps, kindly inform them that you can only assist with app-related queries. "
            "If you do not have enough information to answer a specific question, let the user know politely and guide them to ask for app-related details."
            f"\nApp details:\n"
            f"Name: {app_info.get('name', 'Unknown')}\n"
            f"Description: {app_info.get('description', 'Unknown')}\n"
            f"Average Rating: {app_info.get('userAvgRating', 'Unknown')}\n"
            f"Developer: {app_info.get('developer', 'Unknown')}\n"
            f"Genre: {app_info.get('genre', 'Unknown')}\n"
            f"Installs: {app_info.get('installs', 'Unknown')}\n"
            f"Free: {app_info.get('free', 'Unknown')}\n"
            f"Contains Ads: {app_info.get('containsAds', 'Unknown')}\n"
            f"Offers In-App Purchases: {app_info.get('offersIAP', 'Unknown')}\n"
            f"Developer Website: {app_info.get('developerWebsite', 'Unknown')}",
        )
        messages = [app_context, ("human", payload.message)]
    else:
        messages = [("system", app_info["error"]), ("human", payload.message)]

    response = StreamingHttpResponse(
        generate_response_async(messages), content_type="text/event-stream; charset=utf-8"
    )

    return response