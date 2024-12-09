import jwt
from ninja.security import HttpBearer
from django.conf import settings
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

class AuthBearer(HttpBearer):
    async def authenticate(self, request, token: str):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            user = await sync_to_async(User.objects.get)(id=payload["user_id"])
            if user.password_changed_at and user.password_changed_at.isoformat() != payload["password_changed_at"]:
                raise jwt.ExpiredSignatureError("Token has expired due to password change")
            request.user = user
            return user
        except jwt.ExpiredSignatureError as e:
            raise self._unauthorized_response(str(e))
        except (jwt.DecodeError, User.DoesNotExist):
            return None
        
    def _unauthorized_response(self, message):
        from ninja.errors import HttpError
        return HttpError(401, message)
    

class PremiumBearer(HttpBearer):
    async def authenticate(self, request, token: str):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            user = await sync_to_async(User.objects.get)(id=payload["user_id"])
            if user.password_changed_at and user.password_changed_at.isoformat() != payload["password_changed_at"]:
                raise jwt.ExpiredSignatureError("Token has expired due to password change")
            if user.subscription_type == "free":
                raise jwt.ExpiredSignatureError("User is not premium")
            request.user = user
            return user
        except jwt.ExpiredSignatureError as e:
            raise self._unauthorized_response(str(e))
        except (jwt.DecodeError, User.DoesNotExist):
            return None
        

    def _unauthorized_response(self, message):
        from ninja.errors import HttpError
        return HttpError(401, message)