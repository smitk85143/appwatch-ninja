from ninja import Router
from ninja.errors import HttpError
from typing import List
from aso import PositionKeywordApp, TrendKeywords
from asgiref.sync import sync_to_async
from backend.settings import exclude_countries
from django_countries import countries
import asyncio

from . import schemas
from .models import Keyword
from home.models import CountryCode
from .utils import extract_keywords
from custom_account.security import PremiumBearer
from home.tasks import app_details_function

router = Router(auth=PremiumBearer())


@router.post("/keyword-performance", response=List[schemas.KeywordNumberSchema])
async def keyword_performance(request, payload: schemas.KeywordPerformanceRequestSchema):
    """
    Endpoint for retrieving keyword performance data.
    """

    country_exists = await sync_to_async(CountryCode.objects.filter(code=payload.country).exists)()
    if not country_exists:
        return HttpError(400, "Invalid country code")
    
    data = await sync_to_async(PositionKeywordApp(payload.store).position_keyword_app)(
        payload.app_id, 
        payload.country, 
        num=50
    )
    
    return data


@router.post("/keyword-suggestion", response=List[schemas.KeywordNumberSchema])
async def keyword_suggestion(request, payload: schemas.KeywordSuggestionRequestSchema):
    """
    Endpoint for retrieving keyword suggestion data.
    """

    country_exists = await sync_to_async(CountryCode.objects.filter(code=payload.country).exists)()
    if not country_exists:
        return HttpError(400, "Invalid country code")
    
    data = await sync_to_async(TrendKeywords("google").tread_keywords)(
        payload.keyword,
        "en",
        payload.country,
    )

    obj, created = await sync_to_async(Keyword.objects.get_or_create)(keyword=payload.keyword)
    await sync_to_async(obj.update_synced)()

    return data


@router.post("/keyword-list", response=List[schemas.KeywordFloatSchema])
async def keyword_list(request, payload: schemas.KeywordListRequestSchema):
    """
    Endpoint for retrieving keyword list data.
    """
    
    selected_number = (len(payload.desc) % (50 - 10 + 1)) + 10
    keywords = await sync_to_async(extract_keywords)(payload.desc, selected_number)

    return keywords


@router.post("/rating-by-country", response=List[schemas.CountryRatingSchema])
async def rating_by_country(request, payload: schemas.AppidStoreSchema):
    try:
        country = [i[0] for i in countries if i[0] not in exclude_countries[payload.store]]
        app_func = app_details_function[payload.store]
        
        async def fetch_rating(code):
            try:
                return code, app_func(payload.app_id, lang='en', country=code)['averageUserRating']
            except Exception:
                return code, None
        
        tasks = [fetch_rating(code) for code in country]
        results = await asyncio.gather(*tasks)

        ratings = [
            schemas.CountryRatingSchema(country_code=code, rating=rating) 
            for code, rating in results if rating is not None
        ]
        
        return ratings
    except Exception:
        return HttpError(500, "An error occurred while fetching rating data")