from typing import List
from ninja import Router
from ninja.errors import HttpError
from asgiref.sync import sync_to_async
from django.db.models import Q
from backend.settings import exclude_countries
from django_countries import countries
from aso import TopKeywords

from home.models import CountryCode, AppDetail, Store
from .schemas import GenreSchema, RequestLeaderboardSchema, ResponseLeaderboardSchema, KeywordNumberSchema

all_exclude_countries = set(list(exclude_countries['google']) + list(exclude_countries['apple']))
country_choices = [("", "")]+[(code, name) for code, name in countries if code not in all_exclude_countries]

router = Router()

@router.get("/store-genre", response=List[GenreSchema])
async def store_genre(request, store: str):
    if store not in ["google", "apple"]:
        raise HttpError(400, "Invalid store")
    
    obj = await sync_to_async(list)(AppDetail.objects.filter(store__name=store, genre__genreId__isnull=False).values_list('genre__genre', "genre__genreId").distinct())

    print(obj)
    
    return [{"genre": genre, "genreId": genre_id} for genre, genre_id in obj]


@router.post("/leaderboard-data", response=List[ResponseLeaderboardSchema])
async def leaderboard_data(request, payload: RequestLeaderboardSchema):
    store_obj = await sync_to_async(Store.objects.get)(name=payload.store)
    if payload.category == 'free':
        queryset = await sync_to_async(list)(AppDetail.objects.filter(
            Q(genre__genreId=payload.genre) & Q(free=True) & Q(hide__exact=False) & Q(removed=False) & Q(store=store_obj)
            ).select_related("store"))
        rank_field = 'genre_rank'
    elif payload.category == 'paid':
        queryset = await sync_to_async(list)(AppDetail.objects.filter(
            Q(genre__genreId=payload.genre) & Q(free=False) & Q(hide__exact=False) & Q(removed=False) & Q(store=store_obj)
            ).select_related("store"))
        rank_field = 'genre_rank'
    elif payload.category == 'grossing':
        queryset = await sync_to_async(list)(AppDetail.objects.filter(
            Q(genre__genreId=payload.genre) & Q(free=True) & Q(hide__exact=False) & Q(removed=False) & Q(store=store_obj)
            ).select_related("store"))
        rank_field = 'grossing_genre_rank'
    apps = [
        {
            'id': item.appID,
            'name': item.name,
            'icon': item.icon,
            'rank': rank_data.get(payload.country),
            'store': item.store.name
        }
        for item in queryset
        if (rank_data := getattr(item, rank_field, {})) is not None and payload.country in rank_data
    ]
    return apps


@router.get("/top-keywords", response=List[KeywordNumberSchema])
async def top_keywords(request, store: str, country: str):
    if not store or not country:
        raise HttpError(400, "Store and country are required")
    
    all_country = await sync_to_async(list)(
        CountryCode.objects.values_list('code', flat=True).distinct()
    )
    selected_country = [code for code in all_country if code not in all_exclude_countries]
    
    if store not in ['google', 'apple'] or country not in selected_country:
        raise HttpError(400, "Invalid store or country")
    
    data = await sync_to_async(TopKeywords(store).top_keywords)(country)
    return data