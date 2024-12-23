import uuid
from django.utils.timezone import datetime, timedelta
import jwt
from django.conf import settings
import datetime as dt
import requests

from .mixins import EmailMessageHandler


def generate_slug() -> str:
    return f"{str(uuid.uuid4())}"

def send_otp_on_email(user_obj):
    email = user_obj.email
    otp_obj = EmailMessageHandler(email)
    otp_obj.send_otp()
    user_obj.otp = otp_obj.otp
    user_obj.otp_expired_at = datetime.now() + timedelta(minutes=5)
    user_obj.save()
    return user_obj.slug


ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)

def create_access_token(user):
    payload = {
        "user_id": user.id,
        "type": "access",
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        "exp": dt.datetime.now(dt.timezone.utc) + ACCESS_TOKEN_LIFETIME,
        "iat": dt.datetime.now(dt.timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def create_refresh_token(user):
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        "exp": dt.datetime.now(dt.timezone.utc) + REFRESH_TOKEN_LIFETIME,
        "iat": dt.datetime.now(dt.timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def validate_google_id_token(id_token: str):
    url = "https://oauth2.googleapis.com/tokeninfo"
    params = {"id_token": id_token}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None