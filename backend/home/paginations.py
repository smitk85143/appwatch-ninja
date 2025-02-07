from typing import Optional
from urllib.parse import urlencode, urljoin
from django.http import HttpRequest
from django.core.paginator import Paginator, Page
from asgiref.sync import sync_to_async

from .utils import developer_data


class CustomPaginator:
    def __init__(self, queryset, page_size: int, request: HttpRequest):
        self.queryset = queryset
        self.page_size = page_size
        self.request = request
        self.paginator = Paginator(queryset, page_size)

    # def get_paginated_response(self, page_number: int, results_schema):
    #     current_page: Page = self.paginator.get_page(page_number)

    #     def build_url(page_number: Optional[int]) -> Optional[str]:
    #         if page_number is None:
    #             return None
    #         query_params = self.request.GET.copy()
    #         query_params['page'] = page_number
    #         return urljoin(self.request.build_absolute_uri(self.request.path), f"?{urlencode(query_params)}")

    #     first_url = build_url(1) if page_number > 1 else None
    #     last_url = build_url(self.paginator.num_pages) if current_page.number < self.paginator.num_pages else None

    #     return {
    #         "count": self.paginator.count,
    #         "next": build_url(current_page.next_page_number() if current_page.has_next() else None),
    #         "previous": build_url(current_page.previous_page_number() if current_page.has_previous() else None),
    #         "first": first_url,
    #         "last": last_url,
    #         "results": [results_schema.from_orm(obj) for obj in current_page.object_list]
    #     }

    async def get_paginated_response_for_developers(self, page_number: int, results_schema):
        current_page: Page = self.paginator.get_page(page_number)

        def build_url(page_number: Optional[int]) -> Optional[str]:
            if page_number is None:
                return None
            query_params = self.request.GET.copy()
            query_params['page'] = page_number
            return urljoin(self.request.build_absolute_uri(self.request.path), f"?{urlencode(query_params)}")

        first_url = build_url(1) if page_number > 1 else None
        last_url = build_url(self.paginator.num_pages) if current_page.number < self.paginator.num_pages else None

        all_developer_data = []
        for developer in current_page.object_list:
            one_developer, _ = await sync_to_async(developer_data)(developer.slug)
            all_developer_data.append(one_developer)

        return {
            "count": self.paginator.count,
            "next": build_url(current_page.next_page_number() if current_page.has_next() else None),
            "previous": build_url(current_page.previous_page_number() if current_page.has_previous() else None),
            "first": first_url,
            "last": last_url,
            "results": [results_schema(**obj) for obj in all_developer_data]
        }