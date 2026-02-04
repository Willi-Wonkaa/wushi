from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import date
import os

from ...models import (
    CompetitionLevel,           # Уровень соревнования (КМС, МС и т.д.)
    DisciplineCategory,         # Категория дисциплины
    AgeCategory,               # Возрастная категория
    Regions,                   # Регионы/команды
    Participant,               # Участники/спортсмены
    Competition,               # Соревнования
    PerformanceCarpet,         # Ковер выступлений
    PerformanceCategoryBlock,  # Блок категорий выступлений
    Performance,               # Выступления
    UserProfile,               # Профили пользователей
    Coach,                     # Тренера
    TrackedParticipants,        # Отслеживаемые участники
    TrackedCompetition,        # Отслеживаемые соревнования
    TrackedRegion,             # Отслеживаемые регионы
    TrackedCategoryBlock,      # Отслеживаемые блоки категорий
    TrackedCarpet              # Отслеживаемые ковры
)


from django.db.models import Count, Avg, Q

def get_dashboard_context():
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

    # Получаем общую статистику
    total_athletes = Participant.objects.count()
    total_regions = Participant.objects.values('region').distinct().count()

    # Статистика соревнований
    upcoming_competitions = all_competitions.filter(start_date__gt=today).count()
    past_competitions = all_competitions.filter(end_date__lt=today).count()

    # Общая статистика выступлений (исключая нули)
    total_performances = Performance.objects.exclude(mark=0).count()
    total_gold = Performance.objects.filter(place=1).count()
    total_silver = Performance.objects.filter(place=2).count()
    total_bronze = Performance.objects.filter(place=3).count()

    # Средний балл по всем выступлениям (исключая нули)
    overall_avg_score = Performance.objects.exclude(mark=0).aggregate(avg=Avg('mark'))['avg'] or 0

    context = {
        'current_competitions': current_competitions,
        'all_competitions': competitions_with_status,
        'has_current': current_competitions.exists(),
        'has_all': all_competitions.exists(),
        # Новая статистика
        'total_athletes': total_athletes,
        'total_regions': total_regions,
        'current_competitions_count': current_competitions.count(),
        'upcoming_competitions': upcoming_competitions,
        'past_competitions': past_competitions,
        'total_performances': total_performances,
        'total_gold': total_gold,
        'total_silver': total_silver,
        'total_bronze': total_bronze,
        'total_medals': total_gold + total_silver + total_bronze,
        'overall_avg_score': round(overall_avg_score, 2) if overall_avg_score else 0,
    }

    return context