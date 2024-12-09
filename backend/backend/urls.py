"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from home.views import router as home_router
from custom_account.views import router as account_router
from user.views import router as user_router
from market_intelligence.views import router as market_intelligence_router
from aso_app.views import router as aso_router

api = NinjaAPI()

api.add_router('/home/', home_router, tags=['Home'])
api.add_router('/account/', account_router, tags=['Account'])
api.add_router('/user/', user_router, tags=['User'])
api.add_router('/market_intelligence/', market_intelligence_router, tags=['Market Intelligence'])
api.add_router('/aso/', aso_router, tags=['ASO'])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
