import random
from django.conf import settings
from django.core.mail import send_mail
        
class EmailMessageHandler:

    def __init__(self, email) -> None:
        self.email = email
        self.otp = random.randint(100000, 999999)

    def send_otp(self):
        send_mail(
            "OTP Verification",
            f"Your OTP is {self.otp}",
            settings.EMAIL_HOST_USER,
            [self.email],
        )