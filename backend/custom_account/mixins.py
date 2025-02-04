import random
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class EmailMessageHandler:

    def __init__(self, email) -> None:
        self.email = email
        self.otp = random.randint(100000, 999999)

    def send_otp(self):
        context = {
            "otp": self.otp
        }
        html_message = render_to_string("emails/otp-verification.html", context)
        plain_message = strip_tags(html_message)
        send_mail(
            subject="OTP Verification",
            message=plain_message,  # Fallback text version
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.email],
            html_message=html_message,  # Send HTML email
        )