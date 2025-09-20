from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name="index"),
    path('base/', base, name="base"),
    path('auth-confirm/', auth_confirm, name="auth_confirm"),
    path('profile/', profile, name="profile"),

    #PRUEBA LOGIN WEB
    path('login/', web_login, name='web_login'),
    path('logout/', web_logout, name='web_logout'),
    path('indexprueba/', indexprueba, name='indexprueba'),
    path('baseprueba/', baseprueba, name='baseprueba'),
    path('registro/', registro_gerente, name='registro'),
]