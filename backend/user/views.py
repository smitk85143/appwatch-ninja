from typing import List
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from django.db.models import Q

from .models import UserWatchlist, ASORequest, ASOGoal, UserDesireApp
from custom_account.security import AuthBearer
from home.models import AppDetail, Store
from .schemas import AddToWatchlistSchema, ASORequestSchema, AddDesireAppSchema
from home.schemas import AppListDetailSchema
from home.tasks import save_store_data

User = get_user_model()

router = Router(auth=AuthBearer())

        
@router.get("/watchlist", response=List[AppListDetailSchema])
async def user_watchlist(request, store: str = None):
    user = request.user
    if store in ["google", "apple"]:
        watchlist_qs = await sync_to_async(list)(
            UserWatchlist.objects.filter(user=user, app__store__name=store).select_related("app", "app__genre", "app__store")
        )
    else:
        watchlist_qs = await sync_to_async(list)(
            UserWatchlist.objects.filter(user=user).select_related("app", "app__genre", "app__store")
        )
    watchlist = [
        item.app
        for item in watchlist_qs
    ]
    return watchlist


@router.post("/watchlist")
async def add_to_watchlist(request, payload: AddToWatchlistSchema):
    user = request.user
    if not user.is_authenticated:
        raise HttpError(401, "User not authenticated")
    try:
        app_obj = await sync_to_async(AppDetail.objects.get)(Q(appID=payload.app_id) & Q(store__name=payload.store))
    except AppDetail.DoesNotExist:
        raise HttpError(404, "App not found")
    
    obj_exists = await sync_to_async(UserWatchlist.objects.filter(user=user, app=app_obj).exists)()
    if payload.watchlist_type == 'add':
        if obj_exists:
            raise HttpError(400, "App already in watchlist")
        else:
            await sync_to_async(UserWatchlist.objects.create)(user=user, app=app_obj)
            raise HttpError(201, "App added to watchlist")
    elif payload.watchlist_type == 'remove':
        if obj_exists:
            await sync_to_async(UserWatchlist.objects.filter(user=user, app=app_obj).delete)()
            return HttpError(200, "App removed from watchlist")
        else:
            raise HttpError(400, "App not in watchlist")
        

@router.get("/watchlist-status")
async def watchlist_status(request, app_id: str, store: str):
    user = request.user
    if not user.is_authenticated:
        raise HttpError(401, "User not authenticated")
    obj_exists = await sync_to_async(UserWatchlist.objects.filter(user=user, app__appID=app_id, app__store__name=store).exists)()
    return {"watchlist_status": obj_exists}
    

@router.post("/access-aso")
async def access_aso(request, payload: ASORequestSchema):
    user = request.user
    if not user.is_authenticated:
        raise HttpError(401, "User not authenticated")
    if user.subscription_type == "premium":
        raise HttpError(403, "You have already access to ASO tools")
    aso_obj = await sync_to_async(ASORequest.objects.filter(user=user).exists)()
    if aso_obj:
        raise HttpError(400, "You have already requested for access")
    aso_goals = await sync_to_async(list)(
        ASOGoal.objects.filter(id__in=payload.aso_goals)
    )
    aso_request= await sync_to_async(ASORequest.objects.create)(
        user=user,
        organization_name=payload.organization_name,
        organization_website=payload.organization_website,
        role=payload.role,
        additional_context=payload.additional_context,
    )
    await sync_to_async(aso_request.aso_goals.set)(aso_goals)
    return {"message": "Your request has been submitted successfully."}


@router.post("/add-desire-app")
async def add_desire_app(request, payload: AddDesireAppSchema):
    user = request.user
    if not user.is_authenticated:
        raise HttpError(401, "User not authenticated")
    try:
        userdesire_objs = await sync_to_async(list)(UserDesireApp.objects.filter(user=user))
        if len(userdesire_objs) > 5:
            raise HttpError(400, "You can only add 5 apps at a time! Wait for them to be added.")
        store_obj = await sync_to_async(Store.objects.get)(name=payload.store)
        obj_exists = await sync_to_async(AppDetail.objects.filter(appID=payload.app_id, store=store_obj, hide=True).exists)()
        if obj_exists:
            raise HttpError(400, "We cannot add this app due to copyright issues.")
        obj_exists = await sync_to_async(AppDetail.objects.filter(appID=payload.app_id, store=store_obj).exists)()
        if obj_exists:
            raise HttpError(400, "This app already exists, just search for it.")
        obj_exists = await sync_to_async(UserDesireApp.objects.filter(appID=payload.app_id, store=store_obj).exists)()
        if obj_exists:
            raise HttpError(400, "This app is already on our waitlist.")
        obj = await sync_to_async(UserDesireApp.objects.create)(
            user=user,
            appID=payload.app_id,
            store=store_obj
        )
        save_store_data.apply_async((payload.app_id, payload.store, obj.id))
        return {"message": "Your desired app will be added soon."}
    except HttpError as e:
        raise HttpError(400, str(e))
    except Exception:
        raise HttpError(400, "Invalid appID or store")