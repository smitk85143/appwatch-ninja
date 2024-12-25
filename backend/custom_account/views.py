from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from asgiref.sync import sync_to_async
from ipware import get_client_ip
from django.contrib.auth import authenticate
from django.utils import timezone
import jwt
from django.conf import settings
from django.shortcuts import get_object_or_404

from . import utils, schemas
from .security import AuthBearer

User = get_user_model()

router = Router()

@router.post("/register", response=schemas.UserIdSchema)
async def register_user(request, payload: schemas.RegistrationSchema):
    if await sync_to_async(User.objects.filter(email=payload.email).exists)():
        return Response({"error": "Email is already in use"}, status=400)

    try:
        user = User(
            email=payload.email,
            password=make_password(payload.password),
        )
        client_ip, is_routable = get_client_ip(request)
        if client_ip:
            user.account_created_ip = client_ip
        await sync_to_async(user.save)()

        user_slug = await sync_to_async(utils.send_otp_on_email)(user)
        return {"user_id": user_slug}
    except Exception as e:
        print(f"Error: {e}")
        raise HttpError(500, "An error occurred while registering the user")
    

@router.post("/token-verify", response={200: schemas.ResponseVerifyTokenSchema, 400: dict})
async def verify_access_token(request, payload: schemas.TokenSchema):
    try:
        payload = jwt.decode(payload.token, settings.JWT_SECRET, algorithms=["HS256"])
        
        user_id = payload.get("user_id")
        
        user = await sync_to_async(User.objects.get)(id=user_id)
        if not user:
            return 400, {"error": "Invalid token", "status": "TOKEN_INVALID"}

        return 200, {"message": "Token is valid", "status": "TOKEN_VALID"}

    except jwt.ExpiredSignatureError:
        return 400, {"error": "Token has expired", "status": "TOKEN_INVALID"}
    except jwt.DecodeError:
        return 400, {"error": "Invalid token", "status": "TOKEN_INVALID"}
    except Exception as e:
        return 400, {"error": str(e), "status": "TOKEN_INVALID"}
    
    
@router.post("/token-refresh", response={200: schemas.ResponseAccessTokenSchema, 400: dict})
async def refresh_token(request, payload: schemas.TokenSchema):
    try:
        payload = jwt.decode(payload.token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")

        user = await sync_to_async(User.objects.get)(id=user_id)
        if not user:
            return 400, {"error": "Invalid refresh token"}

        access_token = utils.create_access_token(user)
        return 200, {"access": access_token}

    except jwt.ExpiredSignatureError:
        return 400, {"error": "Refresh token has expired"}
    except jwt.DecodeError:
        return 400, {"error": "Invalid refresh token"}
    

@router.get("/profile", auth=AuthBearer())
def protected_view(request):
    user = request.auth
    return {"email": user.email}
    

@router.post("/login", response={200: schemas.ResponseAccessRefreshTokenSchema, 403: schemas.ResponseErrorUserIdSchema, 400: dict})
async def login_user(request, payload: schemas.LoginSchema):
    user = await sync_to_async(authenticate)(email=payload.email, password=payload.password)
    if user is None:
        return 400, {"error": "Invalid email or password"}

    if not user.is_user_verified:
        slug = await sync_to_async(utils.send_otp_on_email)(user)
        return 403, {"error": "Please verify your account", "user_id": slug}

    client_ip, is_routable = get_client_ip(request)
    if client_ip:
        user.last_login_ip = client_ip
        user.last_login = timezone.now()
        await sync_to_async(user.save)()

    access_token = utils.create_access_token(user)
    refresh_token = utils.create_refresh_token(user)

    return 200, {"access": access_token, "refresh": refresh_token}


@router.post("/verify-otp", response={200: schemas.ResponseAccessRefreshTokenSchema, 403: schemas.ResponseErrorUserIdSchema, 400: dict})
async def verify_otp(request, payload: schemas.UserOTPSchema):
    try:
        user = await sync_to_async(get_object_or_404)(User, slug=payload.user_id)
        if timezone.now() > user.otp_expired_at:
            new_slug = await sync_to_async(utils.send_otp_on_email)(user)
            return 403, {"error": "OTP expired, a new one has been sent", "user_id": new_slug}
        elif str(payload.otp) == str(user.otp):
            user.is_user_verified = True
            client_ip, is_routable = get_client_ip(request)
            if client_ip:
                user.last_login_ip = client_ip
            await sync_to_async(user.save)()

            access_token = utils.create_access_token(user)
            refresh_token = utils.create_refresh_token(user)

            return 200, {"access": access_token, "refresh": refresh_token}
        else:
            return 400, {"error": "Invalid OTP"}

    except Exception as e:
        print(e)
        return 400, {"error": "An error occurred during OTP verification"}
    

@router.post("/resend-otp", response=schemas.UserIdSchema)
async def resend_otp(request, payload: schemas.UserIdSchema):
    user = await sync_to_async(get_object_or_404)(User, slug=payload.user_id)
    new_slug = await sync_to_async(utils.send_otp_on_email)(user)
    return {"user_id": new_slug}


@router.post("/send-otp-email", response=schemas.UserIdSchema)
async def send_otp_email(request, payload: schemas.EmailSchema):
    user = await sync_to_async(get_object_or_404)(User, email=payload.email)
    new_slug = await sync_to_async(utils.send_otp_on_email)(user)
    return {"user_id": new_slug}


@router.post("/forgot-password")
async def forgot_password(request, payload: schemas.ForgetPasswordSchema):
    user = await sync_to_async(get_object_or_404)(User, slug=payload.user_id)
    if not user:
        raise HttpError(400, "Invalid user")
    if timezone.now() > user.otp_expired_at:
        raise HttpError(400, "OTP expired")
    elif str(payload.otp) == str(user.otp):
        user.otp_expired_at = timezone.datetime.now()
        user.set_password(payload.password)
        user.password_changed_at = timezone.now()
        user.is_user_verified = True
        await sync_to_async(user.save)()
        return {"message": "Password reset successfully"}
    else:
        raise HttpError(400, "Invalid OTP")
    

@router.post("/change-password", auth=AuthBearer())
async def change_password(request, payload: schemas.ChangePasswordSchema):
    user = request.auth
    if not user.check_password(payload.old_password):
        raise HttpError(400, "Invalid old password")
    user.set_password(payload.new_password)
    user.password_changed_at = timezone.now()
    await sync_to_async(user.save)()
    return {"message": "Password changed successfully"}


@router.post("/auth/google", auth=None)
async def google_login(request, payload: schemas.TokenSchema):

    token_info = await sync_to_async(utils.validate_google_id_token)(payload.token)
    if not token_info:
        return HttpError(400, "Invalid ID token")

    email = token_info.get("email")
    if not email:
        return HttpError(400, "Email is missing in the ID token")

    if str(token_info.get("email_verified")).lower() != "true":
        return HttpError(400, "Email is not verified by Google")

    client_ip, is_routable = await sync_to_async(get_client_ip)(request)

    user, created = await sync_to_async(User.objects.get_or_create)(
        email=email, defaults={
            "is_user_verified": True
        }
    )

    if client_ip:

        if created:
            user.account_created_ip = client_ip
            user.last_login_ip = client_ip
            await sync_to_async(user.save)()
        else:
            user.last_login_ip = client_ip
            await sync_to_async(user.save)()

    access_token = await sync_to_async(utils.create_access_token)(user)
    refresh_token = await sync_to_async(utils.create_refresh_token)(user)

    return {
        "message": "User logged in successfully",
        "access": access_token,
        "refresh": refresh_token,
    }