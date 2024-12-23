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
            self.validate_token_type(payload)
            user = await self._get_user_from_payload(payload)
            self.additional_checks(user, payload)
            request.user = user
            return user
        except jwt.ExpiredSignatureError as e:
            raise self._unauthorized_response(str(e))
        except (jwt.DecodeError, User.DoesNotExist):
            return None

    def validate_token_type(self, payload):
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Invalid token type")

    async def _get_user_from_payload(self, payload):
        user = await sync_to_async(User.objects.get)(id=payload["user_id"])
        if user.password_changed_at and user.password_changed_at.isoformat() != payload["password_changed_at"]:
            raise jwt.ExpiredSignatureError("Token has expired due to password change")
        return user

    def additional_checks(self, user, payload):
        """Override in subclasses for additional validation checks."""
        pass

    def _unauthorized_response(self, message):
        from ninja.errors import HttpError
        return HttpError(401, message)


class PremiumBearer(AuthBearer):
    def additional_checks(self, user, payload):
        if user.subscription_type == "free":
            raise jwt.ExpiredSignatureError("User is not premium")