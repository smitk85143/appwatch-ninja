from celery import shared_task
from google_play_scraper import list as google_list, app
from django_countries import countries
from django.db.models import Q
from itunes_app_scraper.scraper import AppStoreScraper
from aso import PositionKeywordApp, TrendKeywords
from django.contrib.auth import get_user_model
from celery.utils.log import get_task_logger
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.settings import exclude_countries, category
from home.models import Genre, Store, AppDetail
from user.models import UserDesireApp
from home.tasks import save_store_data

User = get_user_model()

logger = get_task_logger(__name__)

appStoreScraper = AppStoreScraper()

def update_of_country_rank(rank, column_name, app_data):
    if rank is not None:
        app_data['app_obj'].update_rank(column_name, app_data['country_code'], rank)
    else:
        app_data['app_obj'].delete_rank(column_name, app_data['country_code'])

def fetch_and_update(app_objs, category_list, code, update_string):
    for app_obj in app_objs:
        rank = None
        if app_obj.free:
            rank = category_list[0].index(app_obj.appID) + 1 if app_obj.appID in category_list[0] else None
            if len(category_list) == 3:
                grossing_rank = category_list[2].index(app_obj.appID) + 1 if app_obj.appID in category_list[2] else None
                
                update_of_country_rank(grossing_rank, f"grossing_{update_string}", {'app_obj':app_obj, 'country_code':code})
        else:
            rank = category_list[1].index(app_obj.appID) + 1 if app_obj.appID in category_list[1] else None
        update_of_country_rank(rank, update_string, {'app_obj':app_obj, 'country_code':code})

def add_not_available_app(app_ids, data, genre):
    try:
        for app in app_ids:
            if app not in data['all_app_ids']:
                save_store_data.apply_async(args=[app, data['store_obj'].name, None, genre], priority=8)
                data['all_app_ids'].append(app)
    except Exception as e:
        print(f"Error (add_not_available_app): {e}")
    return data['all_app_ids']

def category_leaderboard(country_code, data, leaderboard_funtion, genre=None, main_genre=None):
    category_list = {}
    store_category = ['top-free', 'top-paid', 'topgrossingapplications'] if genre is not None and data['store_obj'].name == 'apple' else category[data['store_obj'].name]
    for i, single_category in enumerate(store_category):
        try:
            category_data = leaderboard_funtion(single_category, country=country_code, num=45) if genre is None else leaderboard_funtion(collection=single_category, category=genre, country=country_code)
            if category_data is not None:
                category_list[i] = category_data
                data['all_app_ids'] = add_not_available_app(category_data[:2], data, main_genre)
            else:
                category_list[i] = []
        except Exception as e:
            print(f"Error (category_leaderboard): {e} {country_code} {single_category} {genre} {main_genre}")
            category_list[i] = []
    return category_list, data['all_app_ids']

def get_genre_obj(store):
    genre_obj = Genre.objects.values_list('genreId', flat=True).distinct()
    return [i for i in genre_obj if 'APPLE' not in i] if store == 'google' else [i for i in genre_obj if 'APPLE' in i]

def get_all_app_ids(store_obj):
    obj_list = AppDetail.objects.filter(store=store_obj).values_list('appID', flat=True)
    user_desire_app_ids = UserDesireApp.objects.filter(store=store_obj).values_list('appID', flat=True)
    return list(set(user_desire_app_ids.union(obj_list)))


def process_google_store_main_genre_leaderboard(store_countries, data, genre_leaderboard):
    leaderboard_genre_obj = ('APPLICATION', 'GAME')
    for code in store_countries:
        for genre in leaderboard_genre_obj:
            category_list, all_app_ids = category_leaderboard(code, data, genre_leaderboard, genre, genre)
            fetch_and_update(AppDetail.objects.filter(Q(removed=False) & Q(store=data['store_obj']) & Q(app_type=genre)), category_list, code, "rank")
    return all_app_ids

def process_apple_store_leaderboard(store_countries, data, all_leaderboard):
    obj_list = AppDetail.objects.filter(Q(removed=False) & Q(store=data['store_obj']))
    for code in store_countries:
        category_list, all_app_ids = category_leaderboard(code, data, all_leaderboard)
        fetch_and_update(obj_list, category_list, code, "rank")
    return all_app_ids

def all_and_genre(store, all_leaderboard, genre_leaderboard):
    store_obj = Store.objects.get(name=store)
    all_app_ids = get_all_app_ids(store_obj)
    store_countries = [i[0] for i in countries if i[0] not in exclude_countries[store]]
    data = {"all_app_ids": all_app_ids, 'store_obj': store_obj}
    all_app_ids = process_google_store_main_genre_leaderboard(store_countries, data, genre_leaderboard) if store == 'google' else process_apple_store_leaderboard(store_countries, data, all_leaderboard)
    for code in store_countries:
        for genre in get_genre_obj(store):
            category_list, all_app_ids = category_leaderboard(code, data, genre_leaderboard, genre)
            app_objs = AppDetail.objects.filter(Q(genre__genreId=genre) & Q(removed=False) & Q(store=store_obj))
            fetch_and_update(app_objs, category_list, code, "genre_rank")

@shared_task
def country_rank():
    AppDetail.objects.filter(removed=True).update(
        rank={},
        genre_rank={},
        grossing_rank={},
        grossing_genre_rank={}
    )
    all_and_genre('google', "leaderboard", google_list)
    all_and_genre('apple', appStoreScraper.get_app_ids_for_collection, appStoreScraper.get_app_from_collection_category)

@shared_task
def keyword_performance(app_id, select_country, store):
    try:
        res = PositionKeywordApp(store).position_keyword_app(app_id, select_country, num=50)
        return (res, 200)
    except Exception:
        return ({'error': 'Invalid appID or country or store'}, 400)
    
@shared_task
def keyword_suggestion(keyword_data, select_country):
    try:
        res = TrendKeywords('google').tread_keywords(keyword_data, "en", select_country)
        return (res, 200)
    except Exception:
        return ({'error': 'Invalid appID or country or store'}, 400)
    

@shared_task
def rating_by_country(app_id, store):
    try:
        country = [i[0] for i in countries if i[0] not in exclude_countries[store]]
        if store == 'google':
            app_func = app
        elif store == 'apple':
            app_func = appStoreScraper.get_app_details
        
        ratings = {}

        def fetch_rating(code):
            try:
                return code, app_func(app_id, country=code.lower())['averageUserRating']
            except Exception:
                return code, None

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_code = {executor.submit(fetch_rating, code): code for code in country}
            for future in as_completed(future_to_code):
                code, rating = future.result()
                if rating is not None:
                    ratings[code] = rating

        return (ratings, 200)
    except Exception:
        return ({'error': 'Invalid appID or store'}, 400)