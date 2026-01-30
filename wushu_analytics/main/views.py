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
    """Страница соревнований с выбором конкретного соревнования"""
    from .models import Competition
    from .DataController.parser import parse_competition_detail
    from datetime import date
    
    # Получаем все соревнования, отсортированные по дате
    all_competitions = Competition.objects.all().order_by('-start_date')
    
    # Если есть параметр competition_id, показываем детальную страницу
    competition_id = request.GET.get('competition_id')
    if competition_id:
        try:
            competition = Competition.objects.get(id=competition_id)
            
            # Парсим детальную информацию о соревновании
            detail_data = None
            has_current_categories = False
            has_next_categories = False
            if competition.link:
                detail_data = parse_competition_detail(competition.link)
                if detail_data and detail_data.get('categories'):
                    has_current_categories = any(cat.get('status') == 'current' for cat in detail_data['categories'])
                    has_next_categories = any(cat.get('status') == 'next' for cat in detail_data['categories'])
            
            # Определяем статус соревнования
            today = date.today()
            if competition.start_date <= today <= competition.end_date:
                competition_status = "active"
            elif competition.start_date > today:
                competition_status = "upcoming"
            else:
                competition_status = "completed"
            
            context = {
                'competition': competition,
                'detail_data': detail_data,
                'competition_status': competition_status,
                'has_current_categories': has_current_categories,
                'has_next_categories': has_next_categories,
                'selected': True
            }
            return render(request, "competition_detail.html", context)
        except Competition.DoesNotExist:
            pass
    
    context = {
        'competitions': all_competitions,
        'selected': False,
        'today': date.today()
    }
    return render(request, "competitions.html", context)

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
        return JsonResponse({'success': True, 'message': 'Данные успешно обновлены'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
