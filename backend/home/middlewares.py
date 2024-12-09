import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class ThrottlingMiddleware(MiddlewareMixin):
    RATE_LIMIT = 100  # Max requests
    PERIOD = 60  # In seconds

    def process_request(self, request):
        # Use user-specific key if authenticated; otherwise, use IP
        if request.user.is_authenticated:
            key = f"throttle_user_{request.user.id}"
        else:
            key = f"throttle_ip_{self.get_client_ip(request)}"

        # Get throttling data from cache
        data = cache.get(key, (0, time.time()))
        requests, start_time = data
        current_time = time.time()

        # Reset counter after period
        if current_time - start_time > self.PERIOD:
            requests = 0
            start_time = current_time

        # Check rate limit
        if requests >= self.RATE_LIMIT:
            return JsonResponse(
                {"detail": "Rate limit exceeded. Try again later."}, status=429
            )

        # Update the cache
        requests += 1
        cache.set(key, (requests, start_time), timeout=self.PERIOD)

    def get_client_ip(self, request):
        """Retrieve client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip