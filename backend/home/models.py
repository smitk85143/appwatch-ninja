from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.translation import gettext_lazy as _
from django_countries import countries
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from custom_account.utils import generate_slug

class CountryCode(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.code
    
    @receiver(post_migrate)
    def create_country_codes(sender, **kwargs):
        for code, name in list(countries):
            CountryCode.objects.get_or_create(code=code, name=name)

class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    @receiver(post_migrate)
    def create_stores(sender, **kwargs):
        Store.objects.get_or_create(name="google")
        Store.objects.get_or_create(name="apple")

class Genre(models.Model):
    genreId = models.CharField(max_length=100, unique=True)
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

class Developer(models.Model):
    developerId = models.CharField(max_length=500, unique=True)
    sellerName = models.CharField(max_length=500, blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return self.sellerName
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_slug()
        super(Developer, self).save(*args, **kwargs)



class AppDetail(models.Model):

    APPLICATION = 'application'
    GAME = 'game'

    APP_TYPES = [
        (APPLICATION, _('Application')),
        (GAME, _('Game'))
    ]

    appID = models.CharField(max_length=200, unique=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    userAvgRating = models.FloatField(blank=True, null=True)
    ratings = models.BigIntegerField(blank=True, null=True)
    histogram = ArrayField(models.BigIntegerField(), default=list, blank=True, null=True)
    free = models.BooleanField(blank=True, null=True)
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE, blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, blank=True, null=True)
    categories = models.TextField(blank=True, null=True)
    released = models.CharField(max_length=100, blank=True, null=True)
    currentVersionDate = models.CharField(max_length=100, blank=True, null=True)
    currentVersion = models.CharField(max_length=100, blank=True, null=True)
    icon = models.URLField(max_length=1000, blank=True, null=True)
    screenshots = ArrayField(models.URLField(), default=list)
    removed = models.BooleanField(default=False)
    history = models.JSONField(default=dict, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    crawl_country = models.ForeignKey(CountryCode, on_delete=models.CASCADE, blank=True, null=True)
    rank = models.JSONField(default=dict, blank=True, null=True)
    grossing_rank = models.JSONField(default=dict, blank=True, null=True)
    genre_rank = models.JSONField(default=dict, blank=True, null=True)
    grossing_genre_rank = models.JSONField(default=dict, blank=True, null=True)
    summary = models.CharField(max_length=1000, blank=True, null=True)
    reviews = models.BigIntegerField(blank=True, null=True)
    offersIAP = models.BooleanField(blank=True, null=True)
    developerEmail = models.CharField(max_length=1000, blank=True, null=True)
    developerWebsite = models.CharField(max_length=1000, blank=True, null=True)
    developerAddress = models.CharField(max_length=1000, blank=True, null=True)
    privacyPolicy = models.CharField(max_length=1000, blank=True, null=True)
    adSupported = models.BooleanField(blank=True, null=True)
    containsAds = models.BooleanField(blank=True, null=True)
    daily_downloads = ArrayField(models.BigIntegerField(), default=list, blank=True, null=True)
    headerImage = models.URLField(max_length=1000, blank=True, null=True)
    video = models.URLField(max_length=1000, blank=True, null=True)
    videoImage = models.URLField(max_length=1000, blank=True, null=True)
    installs = models.CharField(max_length=100, blank=True, null=True)
    downloads = models.JSONField(default=dict, blank=True, null=True)
    hide = models.BooleanField(default=False)
    app_type = models.CharField(
        _('app type'),
        max_length=20,
        choices=APP_TYPES,
        null=True,
        blank=True
    )

    def add_daily_download(self, daily_download):
        """
        Add a daily download count to the list.
        """
        self.daily_downloads.append(daily_download)

        if len(self.daily_downloads) > 30:
            self.daily_downloads.pop(0)
        self.save()

    
    def add_download(self, downloads):
        """
        Add a download count with the date as the key,
        only if it differs from the previous day's count.
        """
        date = timezone.now().strftime("%Y-%m-%d")
        if self.downloads is None:
            self.downloads = {}
        elif self.downloads:
            last_date = max(self.downloads.keys())
            if self.downloads[last_date] == downloads:
                return
        self.downloads[date] = downloads
        self.save()


    def __str__(self):
        return f"{self.name}"

    def store_history(self, changelog_data: dict):
        date = timezone.now().strftime("%Y-%m-%d")
        self._update_history(changelog_data, date)
        # self._cleanup_old_history_entries()

    def _update_history(self, changelog_data: dict, date: str):
        history = {}
        for key, value in changelog_data.items():
            if getattr(self, key) != value and getattr(self, key) is not None:
                history[key] = getattr(self, key)
        if history:
            self.history[date] = history
            self.save()

    def _cleanup_old_history_entries(self):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_dates = [
            date for date in self.history.keys() 
            if datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc) < thirty_days_ago
        ]
        for date in old_dates:
            del self.history[date]
        if old_dates:
            self.save()

    def update_rank(self, column_name, country_code, rank):
        field_value = getattr(self, column_name)
        field_value[country_code] = rank
        setattr(self, column_name, field_value)
        self.save()

    def delete_rank(self, column_name, country_code):
        field_value = getattr(self, column_name)
        if country_code in field_value:
            field_value.pop(country_code)
        setattr(self, column_name, field_value)
        self.save()