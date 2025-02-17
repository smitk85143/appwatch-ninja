from typing import List, Optional, Any
from ninja import Schema, ModelSchema
from .models import AppDetail, Genre, Developer, Store
from pydantic import field_validator

class GenreSchema(ModelSchema):
    class Meta:
        model = Genre
        fields = ['genreId', 'genre']


class DeveloperSchema(ModelSchema):
    class Meta:
        model = Developer
        fields = ['developerId', 'sellerName', 'slug']


class StoreSchema(ModelSchema):
    class Meta:
        model = Store
        fields = ['name']


class AppListDetailSchema(ModelSchema):
    genre: GenreSchema
    store: StoreSchema

    class Meta:
        model = AppDetail
        fields = ['appID', 'name', 'released', 'userAvgRating', 'ratings', 'icon', 'genre', 'store']


class AppDetailSchema(ModelSchema):
    genre: GenreSchema
    developer: DeveloperSchema
    store: StoreSchema

    class Meta:
        model = AppDetail
        exclude = ['id', 'timestamp', 'updated', 'app_type', 'crawl_country']


class SingleDeveloperListSchema(Schema):
    name: str
    store: StoreSchema
    slug: str
    id: str
    total_apps: int | None
    removed_apps: int | None
    total_rating: int | None
    daily_installs: int | None


class DeveloperListSchema(Schema):
    results: List[SingleDeveloperListSchema]
    count: int
    current_page: int
    total_pages: int


class DeveloperAppSchema(ModelSchema):
    genre: GenreSchema
    store: StoreSchema

    class Meta:
        model = AppDetail
        fields = ['appID', 'name', 'released', 'userAvgRating', 'ratings', 'icon', 'downloads', 'removed', 'genre', 'store']


class SingleDeveloperSchema(Schema):
    developer: DeveloperSchema
    apps: List[DeveloperAppSchema]


# class AppSearchDetailSchema(Schema):
#     appID: str
#     name: str
#     icon: str
#     store: str


class AppSearchDetailSchemaV2(Schema):
    app_id: str
    name: str
    icon: str
    store__name: str
    

class PaginatedResponseSchema(Schema):
    count: int
    next: Optional[str]
    previous: Optional[str]
    first: Optional[str]
    last: Optional[str]
    results: List[Any]


class AppidStoreSchema(Schema):
    app_id: str
    store: str

    @field_validator("store")
    def validate_store(cls, value):
        if value not in ['google', 'apple']:
            raise ValueError("Invalid store name")
        return value
    

class DeveloperSlugSchema(Schema):
    dev_id: str