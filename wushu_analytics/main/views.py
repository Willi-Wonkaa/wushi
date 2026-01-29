from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
import threading
import json
import time
from io import BytesIO


# Страница входа
def dashboard(request):
    return render(request, "dashboard.html")

def analytics(request):
    return render(request, "analytics.html")

def competitions(request):
    return render(request, "competitions.html")

def regions(request):
    return render(request, "regions.html")

def athletes(request):
    return render(request, "athletes.html")
