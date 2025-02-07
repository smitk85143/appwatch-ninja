from typing import List
from ninja import Query, Router
from ninja.errors import HttpError
from django.db.models import Q
from asgiref.sync import sync_to_async
from haystack.query import SearchQuerySet

from .paginations import CustomPaginator
from . import schemas
from .models import AppDetail, Developer
from .search_indexes import SearchIndex

router = Router()

search_index = SearchIndex().get_index()

# @router.get("/apps", response=schemas.PaginatedResponseSchema)
# async def list_apps(
#     request,
#     store: str = Query("google"),
#     page: int = Query(1, ge=1),
#     page_size: int = Query(10, ge=1),
# ):
#     if store not in ["google", "apple"]:
#         raise HttpError(400, "Invalid store")
    
#     queryset = await sync_to_async(list)(
#         AppDetail.objects.filter(
#             Q(name__isnull=False) & Q(hide=False) & Q(store__name=store)
#         ).select_related("genre", "store")
#     )

#     paginator = CustomPaginator(queryset, page_size, request)
#     return paginator.get_paginated_response(page, schemas.AppListDetailSchema)


@router.get("/apps/v2", response=schemas.PaginatedResponseSchema)
async def list_apps_v2(
    request,
    store: str = Query("google"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
):
    if store not in ["google", "apple"]:
        raise HttpError(400, "Invalid store")
    
    offset = (page - 1) * page_size
    
    total = await AppDetail.objects.filter(
        hide=False,
        store__name=store
    ).acount()
    
    total_pages = (total + page_size - 1) // page_size
    
    queryset = AppDetail.objects.filter(
        hide=False,
        store__name=store
    ).select_related(
        "genre", 
        "store"
    ).values(
        'appID', 'name', 'icon', 'ratings', 'released', 'userAvgRating',
        'genre__genreId', 'genre__genre', 'store__name'
    )[offset:offset + page_size]
    
    results = await sync_to_async(list)(queryset)
    
    base_url = str(request.build_absolute_uri())
    base_url = base_url.split('?')[0]
    
    def get_page_url(page_num):
        return f"{base_url}?store={store}&page={page_num}&page_size={page_size}"
    
    return {
        "count": total,
        "next": get_page_url(page + 1) if page < total_pages else None,
        "previous": get_page_url(page - 1) if page > 1 else None,
        "first": get_page_url(1) if page > 1 else None,
        "last": get_page_url(total_pages) if page < total_pages else None,
        "results": results
    }


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
    

@router.post("/developer", response=schemas.SingleDeveloperSchema)
async def single_Developer(
    request,
    payload: schemas.DeveloperSlugSchema,
):
    try:
        developer_obj = await sync_to_async(Developer.objects.get)(slug=payload.dev_id)

        if not developer_obj:
            raise HttpError(404, "Developer not found")

        developer_apps = await sync_to_async(list)(AppDetail.objects.filter(
            Q(developer=developer_obj) & Q(name__isnull=False) & Q(hide__exact=False)
        ).select_related('genre', 'store'))

        if not developer_apps:
            raise HttpError(404, "No apps found for the specified developer.") 
    
        return {
            "developer": developer_obj,
            "apps": developer_apps,
        }
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
    

@router.get("/search/v2", response=List[schemas.AppSearchDetailSchema])
async def search_apps_v2(request, q: str = Query(...)):
    if not q:
        return []

    try:
        search_index.update_searchable_attributes(['name', 'appID'])
        results = search_index.search(q, {'limit': 8, "attributesToHighlight": ["name", "appID"]})
        return results['hits']
    except Exception:
        raise HttpError(400, "Invalid query")