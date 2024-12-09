from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from .utils import generate_slug

from .manager import CustomUserManager

class CustomUser(AbstractUser):

    FREE = 'free'
    PREMIUM = 'premium'

    SUBSCRIPTION_TYPES = [
        (FREE, _('Free')),
        (PREMIUM, _('Premium'))
    ]

    username = None
    email = models.EmailField(_("email address"), unique=True)
    is_user_verified = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_expired_at = models.DateTimeField(null=True, blank=True)
    subscription_type = models.CharField(
        _('subscription type'),
        max_length=20,
        choices=SUBSCRIPTION_TYPES,
        default=FREE,
    )

    account_created_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2'):
            self.set_password(self.password)
        self.slug = generate_slug()
        super(CustomUser, self).save(*args, **kwargs)