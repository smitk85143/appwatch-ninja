from ninja import Schema
from pydantic import Field, field_validator, EmailStr

class RegistrationSchema(Schema):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserIdSchema(Schema):
    user_id: str


class LoginSchema(Schema):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class ResponseAccessRefreshTokenSchema(Schema):
    access: str
    refresh: str


class ResponseAccessTokenSchema(Schema):
    access: str


class ResponseErrorUserIdSchema(Schema):
    error: str
    user_id: str


class UserOTPSchema(Schema):
    otp: int = Field(...)
    user_id: str

    @field_validator('otp')
    def check_otp_length(cls, v):
        if len(str(v)) != 6:
            raise ValueError('OTP must be 6 digits long')
        return v


class EmailSchema(Schema):
    email: str


class ForgetPasswordSchema(Schema):
    user_id: str
    otp: int = Field(...)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('otp')
    def check_otp_length(cls, v):
        if len(str(v)) != 6:
            raise ValueError('OTP must be 6 digits long')
        return v
    
class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ResponseVerifyTokenSchema(Schema):
    message: str


class TokenSchema(Schema):
    token: str 