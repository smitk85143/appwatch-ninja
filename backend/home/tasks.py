from celery import shared_task
from google_play_scraper import app as google_app
from django_countries import countries
from itunes_app_scraper.scraper import AppStoreScraper
from django.core.mail import EmailMessage
from django.db.models import Q

from home.models import AppDetail, Store
from user.models import UserWatchlist
from user.models import UserDesireApp
from .utils import exclude_countries, AppleAppStoreData, GoogleAppStoreData

appStoreScraper = AppStoreScraper()

app_details_function = { 'google': google_app, 'apple': appStoreScraper.get_app_details }


def crawl_app(appID, store, country_code=None):
    result = None 
    try:
        if country_code is not None:
            result = app_details_function[store](appID, country=country_code)
        else:
            result = app_details_function[store](appID)
    except Exception:
        for code, name in list(countries):
            if code not in exclude_countries[store]:
                try:
                    result = app_details_function[store](appID, country=code)
                    country_code = code
                    break
                except Exception:
                    continue
    return result, country_code


def email_notification_desire_app(found, user_email, app_id, store):
    if found:
        subject = 'App Store Optimization - App is now available'
        message = f'App with ID {app_id} is now available on {store} store.'
    else:
        subject = 'App Store Optimization - App is not available'
        message = f'App with ID {app_id} is not available on {store} store.'
    rebuild_index()
    email = EmailMessage(subject, message, to=[user_email])
    email.send()


@shared_task(name='save_store_data')
def save_store_data(appID, store, id=None, app_type=None):
    store_obj = Store.objects.get(name=store)
    obj, _ = AppDetail.objects.get_or_create(appID=appID, store=store_obj)
    code = obj.crawl_country.code if obj.crawl_country else None
    result, country_code = crawl_app(appID, store, code)

    if result is None:
        if not obj.name:
            obj.delete()
        else:
            obj.removed = True
            obj.save()
        email_result = False
    else:
        kwargs = {'country_code': country_code, 'app_type': app_type}
        app_data_class = AppleAppStoreData if store == 'apple' else GoogleAppStoreData
        app_data_class(obj, result, store, **kwargs).save_data()
        email_result = True

    if id:
        email_notification_desire_app(email_result, UserDesireApp.objects.get(pk=id).user.email, appID, store)
        UserDesireApp.objects.filter(pk=id).delete()
        

@shared_task
def daily_task():
    watchlist_apps = UserWatchlist.objects.filter(Q(user__is_active=True) & Q(app__removed=False))
    
    for watchlist_item in watchlist_apps:
        save_store_data.apply_async((watchlist_item.app.appID, watchlist_item.app.store.name, None), priority=4)

    watchlist_app_ids = watchlist_apps.values_list('app_id', flat=True)
    
    apps_to_process = AppDetail.objects.filter(removed=False).exclude(id__in=watchlist_app_ids)
    for app in apps_to_process:
        platform = app.store.name
        priority = 5 if platform == "google" else 7
        save_store_data.apply_async((app.appID, platform, None), priority=priority)


@shared_task
def check_removed_apps():
    apps = AppDetail.objects.filter(removed=True)
    for app in apps:
        result, _ = crawl_app(app.appID, app.store.name)
        if result is not None:
            app.removed = False
            app.save()


@shared_task
def save_user_desire_app():
    apps = UserDesireApp.objects.all()
    for app in apps:
        save_store_data.apply_async((app.appID, app.store.name, app.user.id), priority=10)


@shared_task
def rebuild_index():
    from haystack.management.commands import update_index
    update_index.Command().handle()


def get_app_store_data():
    list_app = ["com.meesho.supply", "in.startv.hotstar", "com.amazon.avod.thirdpartyclient", "com.crunchyroll.crunchyroid", "com.netflix.mediaclient", 
                "com.duolingo", "com.truecaller", "com.microsoft.office.officehubrow", "com.microsoft.office.word", "cn.wps.moffice_eng", "com.adobe.scan.android",
                "notion.id", "com.linkedin.android", "us.zoom.videomeetings", "com.whatsapp", "com.ubercab", "com.instagram.android"]
    for app in list_app:
        save_store_data(app, "google")