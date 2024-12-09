from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from home.models import AppDetail, Store


class UserWatchlist(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    app = models.ForeignKey(AppDetail, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} watching {self.app}"
    

class UserDesireApp(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    appID = models.CharField(max_length=200)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} desires {self.appID}"
    

class ASOGoal(models.Model):
    name = models.CharField(_('Goal Name'), max_length=255)
    description = models.TextField(_('Description'))
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @receiver(post_migrate)
    def add_default_goal(sender, **kwargs):
        ASO_GOALS = [
            ('visibility', 'Improve App Visibility'),
            ('downloads', 'Increase Downloads'),
            ('engagement', 'Enhance User Engagement'),
            ('revenue', 'Increase Revenue'),
            ('customer_acquisition', 'Acquire New Customers'),
            ('retention', 'Improve Customer Retention')
        ]
        for goal in ASO_GOALS:
            ASOGoal.objects.get_or_create(name=goal[0], description=goal[1])


class ASORequest(models.Model):

    APPROVED_CHOICES = [
        (True, _('Approved')),
        (False, _('Pending'))
    ]

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    organization_name = models.CharField(_('Organization Name'), max_length=255)
    organization_website = models.URLField(_('Organization Website'), blank=True)
    role = models.CharField(_('Role'), max_length=255)
    aso_goals = models.ManyToManyField(ASOGoal, blank=True)
    additional_context = models.TextField(_('Additional Context'), blank=True)
    approved = models.BooleanField(_('Approved'), choices=APPROVED_CHOICES, default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organization_name
    
    def save(self, *args, **kwargs):
        if self.approved and self.approved!= ASORequest.objects.get(id=self.id).approved:
            self.user.subscription_type = "premium"
            self.user.save()
        super().save(*args, **kwargs)