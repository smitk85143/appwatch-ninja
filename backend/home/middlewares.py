import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class ThrottlingMiddleware(MiddlewareMixin):
    RATE_LIMIT = 100
    PERIOD = 60

    def process_request(self, request):
        if request.user.is_authenticated:
            key = f"throttle_user_{request.user.id}"
        else:
            key = f"throttle_ip_{self.get_client_ip(request)}"

        data = cache.get(key, (0, time.time()))
        requests, start_time = data
        current_time = time.time()

        if current_time - start_time > self.PERIOD:
            requests = 0
            start_time = current_time

        if requests >= self.RATE_LIMIT:
            return JsonResponse(
                {"detail": "Rate limit exceeded. Try again later."}, status=429
            )

        requests += 1
        cache.set(key, (requests, start_time), timeout=self.PERIOD)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip