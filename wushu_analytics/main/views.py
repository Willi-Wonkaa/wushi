from django.shortcuts import render
from django.http import JsonResponse
from datetime import date
from .models import Competition
import sys
import os


def dashboard(request):
    # Получаем все соревнования из БД
    all_competitions = Competition.objects.all().order_by('-start_date')
    
    # Определяем актуальные соревнования (идущие сейчас)
    today = date.today()
    current_competitions = all_competitions.filter(
        start_date__lte=today, 
        end_date__gte=today
    )
    
    # Определяем статус для каждого соревнования
    competitions_with_status = []
    for comp in all_competitions:
        if comp.start_date > today:
            status = 'скоро'
            status_class = 'badge-warning'
        elif comp.end_date < today:
            status = 'прошли'
            status_class = 'badge-secondary'
        else:
            status = 'идет'
            status_class = 'badge-success'
            
        competitions_with_status.append({
            'competition': comp,
            'status': status,
            'status_class': status_class
        })
    
    context = {
        'current_competitions': current_competitions,
        'all_competitions': competitions_with_status,
        'has_current': current_competitions.exists(),
        'has_all': all_competitions.exists()
    }
    
    return render(request, "dashboard.html", context)

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
    from django.http import JsonResponse
    
    try:
        sync_all_data(request)
        return JsonResponse({'status': 'success', 'message': 'Данные успешно обновлены'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
