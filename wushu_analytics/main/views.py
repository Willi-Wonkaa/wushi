from django.shortcuts import render
from django.http import JsonResponse
import sys
import os


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

def update_data(request):
    """Запускает синхронизацию данных с парсером"""
    from .DataController.parser import sync_all_data
    return sync_all_data(request)
