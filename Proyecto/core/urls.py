from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name="index"),
    path('base/', base, name="base"),
    path('auth-confirm/', auth_confirm, name="auth_confirm"),
    path('profile/', profile, name="profile"),
]