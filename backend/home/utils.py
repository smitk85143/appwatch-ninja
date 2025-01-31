from django.db.models import Q
from django.utils import timezone
from itunes_app_scraper.util import AppStoreCategories

from .models import CountryCode, Developer, Genre, AppDetail

exclude_countries = { 'google' : {'KP', 'RU', 'SX', 'SS', 'SY'},
                    'apple': {'AX', 'AS', 'AD', 'AQ', 'AW', 'BD', 'BQ', 'BV', 'IO', 'BI', 'CF', 'CX', 'CC', 'KM', 'CK', 'CU', 'CW', 'DJ', 'GQ', 'ER', 
                        'ET', 'FK', 'FO', 'GF', 'PF', 'TF', 'GI', 'GL', 'GP', 'GU', 'GG', 'GN', 'HT', 'HM', 'VA', 'IR', 'IM', 'JE', 'KI', 'LS', 
                        'LI', 'MH', 'MQ', 'YT', 'MC', 'NC', 'NU', 'NF', 'KP', 'MP', 'PS', 'PN', 'PR', 'RE', 'BL', 'SH', 'MF', 'PM', 'WS', 'SM', 
                        'SX', 'SO', 'GS', 'SS', 'SD', 'SJ', 'SY', 'TL', 'TG', 'TK', 'TV', 'UM', 'VI', 'WF', 'EH'
                    }
       }


def developer_data(slug):
    data = AppDetail.objects.filter(Q(developer__slug=slug) & Q(name__isnull=False) & Q(hide__exact=False)).select_related("genre", "store")
    if not data:
        try:
            developer = Developer.objects.get(slug=slug)
        except Developer.DoesNotExist:
            return None, None
        return {'name': developer.sellerName, 'id': developer.developerId, 'slug': None,
                'total_apps': None, 'removed_apps': None, 'total_rating': None, 'daily_installs': None}, None

    developer_data = {
        'name': data[0].developer.sellerName,
        'store': data[0].store,
        'slug': data[0].developer.slug,
        'id': data[0].developer.developerId,
        'total_apps': len(data),
        'removed_apps': sum(1 for obj in data if obj.removed),
        'total_rating': sum(obj.ratings for obj in data if obj.ratings is not None),
        'daily_installs': None,
    }

    if developer_data['store'] == 'google':
        daily_installs = []
        for obj in data:
            daily_downloads = obj.daily_downloads
            if len(daily_downloads) > 2:
                daily_installs.append(daily_downloads[-1]-daily_downloads[-2] if daily_downloads else 0)
        developer_data['daily_installs'] = sum(daily_installs)


    return developer_data, data



class BaseAppStoreData:
    def __init__(self, obj, result, store, **kwargs):
        self.obj = obj
        self.result = result
        self.app_type = kwargs.get('app_type', None)
        self.genreId = None
        self.genre = None
        self.developerId = None
        self.developer = None
        self.store = store
        self.country_code = kwargs.get('country_code', None)

    def save_data(self):
        genre_obj = Genre.objects.get_or_create(genreId=self.genreId, genre=self.genre)
        if self.app_type is not None:
            self.obj.app_type = self.app_type
        developer_obj = Developer.objects.get_or_create(developerId=self.developerId)[0]
        developer_obj.sellerName=self.developer
        developer_obj.save()
        changelog_data = {'name': self.result['trackCensoredName'], 'currentVersion': self.result['version']}
        self.obj.store_history(changelog_data)
        self.obj.name=self.result['trackCensoredName']
        self.obj.description=self.result['description']
        self.obj.userAvgRating=self.result['averageUserRating']
        self.obj.histogram=self.result['histogram']
        self.obj.developer=developer_obj
        self.obj.genre = genre_obj[0]
        self.obj.currentVersion=self.result['version']
        self.rank = self.genre_rank = self.grossing_rank = self.grossing_genre_rank = {}
        if self.country_code is not None:
            self.obj.crawl_country = CountryCode.objects.get(code=self.country_code)
        self.obj.save()

        return self.obj

class AppleAppStoreData(BaseAppStoreData):
    def __init__(self, obj, result, store, **kwargs):
        super().__init__(obj, result, store, **kwargs)
        self.genreId, self.genre = self.apple_genre_id_to_name(result['primaryGenreId'], result['primaryGenreName'], result['formattedPrice'] == 'Free')

        self.developerId = result['artistId']
        self.developer = result['artistName']
        obj.ratings=result['userRatingCount']
        obj.categories=result['genres']
        obj.icon=result['artworkUrl512']
        obj.released=self.change_date_format(result['releaseDate'])
        obj.currentVersionDate=self.change_date_format(result['currentVersionReleaseDate'])
        obj.screenshots=result['screenshotUrls'].split(',')
        obj.free= True if result['formattedPrice'] == 'Free' else False

    def apple_genre_id_to_name(self, genreId, genreName, is_free):
        for attr_name in dir(AppStoreCategories):
            attr = getattr(AppStoreCategories, attr_name)
            if isinstance(attr, list) and genreId == attr[1]:
                genreId = attr_name
                genre = genreName
                if attr[1] == 6014 and is_free :
                    genreId = "APPLE_GAMES_FREE"
                elif attr[1] == 6014 and is_free:
                    genreId = "APPLE_GAMES_PAID"
                return genreId, genre
        return None, None
    
    def change_date_format(self, date):
        input_datetime = timezone.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        output_date_string = input_datetime.strftime("%b %d, %Y")

        return output_date_string


class GoogleAppStoreData(BaseAppStoreData):

    def __init__(self, obj, result, store, **kwargs):
        super().__init__(obj, result, store, **kwargs)

        obj.add_daily_download(result['realInstalls'])
        obj.add_download(result['realInstalls'])
        self.genreId = result['genreId']
        self.genre = result['genre']
        self.developerId = result['developerId']
        self.developer = result['sellerName']
        obj.ratings=result['ratings']
        obj.reviews=result['reviews']
        obj.free=result['free']
        obj.developerAddress=result['developerAddress']
        obj.privacyPolicy=result['privacyPolicy'],
        obj.developerEmail=result['developerEmail']
        obj.categories=", ".join([ i['name'] for i in result['categories'] ])
        obj.adSupported=result['adSupported']
        obj.containsAds=result['containsAds']
        obj.released=result['released']
        obj.icon=result['icon']
        obj.headerImage=result['headerImage']
        obj.video=result['video']
        obj.videoImage=result['videoImage']
        obj.currentVersionDate=result['currentVersionReleaseDate']
        obj.screenshots=result['screenshots']
        obj.summary=result['summary']
        obj.offersIAP=result['offersIAP']
        obj.developerWebsite=result['developerWebsite']
        obj.installs = result['installs']