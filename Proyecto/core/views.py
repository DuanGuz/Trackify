from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from .serializers import UserSerializer
from django.contrib.auth.decorators import login_required
from .forms import *

# Create your views here.
def index(request):
	return render(request, 'core/index.html')

def base(request):
    return render(request, 'core/base.html')

def auth_confirm(request):
    return render(request, 'core/auth-confirm.html')

def profile(request):
    return render(request, 'core/profile.html')





#PRUEBA LOGIN/REGISTRO WEB
def registro_gerente(request):
    if request.method == 'POST':
        form = RegistroGerenteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('web_login')
    else:
        form = RegistroGerenteForm()
    return render(request, 'core/registro_gerente.html', {'form': form})

# Login web
def web_login(request):
    if request.user.is_authenticated:
        return redirect('indexprueba')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('indexprueba')
        else:
            error = "Usuario o contraseña incorrectos"
    return render(request, 'core/pruebalogin.html', {'error': error})

# Logout web
def web_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('baseprueba')
    return redirect('indexprueba')

# Index prueba (requiere login)
@login_required(login_url='web_login')
def indexprueba(request):
    return render(request, 'core/indexprueba.html')

# Base prueba (pública)
def baseprueba(request):
    return render(request, 'core/baseprueba.html')







'''
creo que esto es necesario para la app móvil
# Iniciar y cerrar sesión )
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Sesión cerrada correctamente'}, status=status.HTTP_200_OK)
'''