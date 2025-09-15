from django.shortcuts import render

# Create your views here.
def index(request):
	return render(request, 'core/index.html')

def base(request):
    return render(request, 'core/base.html')

def auth_confirm(request):
    return render(request, 'core/auth-confirm.html')

def profile(request):
    return render(request, 'core/profile.html')