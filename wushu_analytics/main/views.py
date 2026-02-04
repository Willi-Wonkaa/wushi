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
from .models import Competition, UserProfile
import os


from  .main_logic.context_creators.dashboard import *

def get_telegram_bot_context():
    bot_username = os.getenv('TELEGRAM_BOT_USERNAME', 'wushu_analytics_bot')
    bot_link = f"https://t.me/{bot_username}" if bot_username else "https://t.me"
    return {
        'telegram_bot_username': bot_username,
        'telegram_bot_link': bot_link,
    }


def user_has_telegram_auth(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        profile = user.user_profile
    except UserProfile.DoesNotExist:
        return False
    return profile.is_telegram_verified


def dashboard(request):
    context = get_dashboard_context()
    return render(request, "dashboard.html", context)


def analytics(request):
    """Страница аналитики - только для тренеров и администраторов"""
    from django.http import HttpResponseForbidden
    
    # Проверка доступа: только авторизованные тренеры или администраторы
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, войдите в систему.")
    
    is_admin = request.user.is_superuser
    is_coach = hasattr(request.user, 'coach_profile')
    
    if not is_admin and not is_coach:
        return HttpResponseForbidden("Доступ запрещён. Только для тренеров и администраторов.")
    
    return render(request, "analytics.html")

def competitions(request):
    """Страница соревнований с выбором конкретного соревнования"""
    from .models import Competition
    from .DataController.parser import parse_competition_detail
    from datetime import date

    has_telegram_auth = user_has_telegram_auth(request.user)
    
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
                'has_telegram_auth': has_telegram_auth,
                'selected': True,
                **get_telegram_bot_context(),
            }
            return render(request, "competition_detail.html", context)
        except Competition.DoesNotExist:
            pass
    
    context = {
        'competitions': all_competitions,
        'selected': False,
        'today': date.today(),
        'has_telegram_auth': has_telegram_auth,
        **get_telegram_bot_context(),
    }
    return render(request, "competitions.html", context)

def regions(request):
    """Страница списка регионов/команд - для всех зарегистрированных пользователей"""
    from .models import RegionStatistics
    from django.http import HttpResponseForbidden
    
    # Проверка доступа: только для авторизованных пользователей
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, <a href='/auth/telegram/'>войдите через Telegram</a> для доступа.")
    
    # Получаем статистику регионов из сводной таблицы
    regions_stats = RegionStatistics.objects.all().order_by('-gold_count', '-silver_count', '-bronze_count')
    
    # Формируем данные для шаблона
    regions_data = []
    for stat in regions_stats:
        regions_data.append({
            'region': stat.region,
            'participants_count': stat.participants_count,
            'competitions_count': stat.competitions_count,
            'avg_score': stat.avg_score,
            'gold_count': stat.gold_count,
            'silver_count': stat.silver_count,
            'bronze_count': stat.bronze_count,
            'total_medals': stat.gold_count + stat.silver_count + stat.bronze_count,
            'last_updated': stat.last_updated,
        })
    
    context = {
        'regions': regions_data,
    }
    
    return render(request, "regions.html", context)


def region_detail(request, region_name):
    """Детальная страница региона/команды - только для тренеров и администраторов"""
    from .models import Participant, Performance, Competition
    from django.db.models import Count, Avg, Q
    from django.http import HttpResponseForbidden
    from datetime import date, timedelta
    from urllib.parse import unquote
    import json
    
    # Проверка доступа: только авторизованные тренеры или администраторы
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, войдите в систему.")
    
    is_admin = request.user.is_superuser
    is_coach = hasattr(request.user, 'coach_profile')
    
    if not is_admin and not is_coach:
        return HttpResponseForbidden("Доступ запрещён. Только для тренеров и администраторов.")
    
    region_name = unquote(region_name)
    two_years_ago = date.today() - timedelta(days=730)
    
    # Участники региона
    participants = Participant.objects.filter(sity=region_name).order_by('name')
    
    # Данные по каждому участнику
    participants_data = []
    for participant in participants:
        performances = Performance.objects.filter(participant=participant)
        competitions_count = performances.values('competition').distinct().count()
        
        # Средний балл за последние 2 года
        avg_score = performances.filter(
            competition__start_date__gte=two_years_ago,
            mark__isnull=False
        ).aggregate(avg=Avg('mark'))['avg'] or 0
        
        # Медали (по полю place)
        gold = performances.filter(place=1).count()
        silver = performances.filter(place=2).count()
        bronze = performances.filter(place=3).count()
        
        participants_data.append({
            'participant': participant,
            'competitions_count': competitions_count,
            'avg_score': round(avg_score, 2) if avg_score else 0,
            'gold': gold,
            'silver': silver,
            'bronze': bronze,
        })
    
    # Сортируем по количеству медалей
    participants_data.sort(key=lambda x: (x['gold'], x['silver'], x['bronze']), reverse=True)
    
    # Соревнования, в которых участвовал регион
    competition_ids = Performance.objects.filter(
        participant__sity=region_name
    ).values_list('competition', flat=True).distinct()
    
    competitions_data = []
    for comp_id in competition_ids:
        competition = Competition.objects.get(id=comp_id)
        
        # Статистика команды на этом соревновании
        team_performances = Performance.objects.filter(
            participant__sity=region_name,
            competition=competition
        )
        team_participants = team_performances.values('participant').distinct().count()
        team_performances_count = team_performances.count()
        
        # Средний балл команды на соревновании
        team_avg = team_performances.filter(mark__isnull=False).aggregate(avg=Avg('mark'))['avg'] or 0
        
        # Медали команды на соревновании (по полю place)
        gold = team_performances.filter(place=1).count()
        silver = team_performances.filter(place=2).count()
        bronze = team_performances.filter(place=3).count()
        
        # Общее количество участников в соревновании
        total_participants_in_comp = Performance.objects.filter(
            competition=competition
        ).values('participant').distinct().count()
        
        competitions_data.append({
            'competition': competition,
            'team_participants': team_participants,
            'team_performances': team_performances_count,
            'team_avg': round(team_avg, 2) if team_avg else 0,
            'gold': gold,
            'silver': silver,
            'bronze': bronze,
            'total_participants': total_participants_in_comp,
        })
    
    # Сортируем по дате соревнования
    competitions_data.sort(key=lambda x: x['competition'].start_date, reverse=True)
    
    # Общая статистика региона
    total_gold = sum(p['gold'] for p in participants_data)
    total_silver = sum(p['silver'] for p in participants_data)
    total_bronze = sum(p['bronze'] for p in participants_data)
    
    overall_avg = Performance.objects.filter(
        participant__sity=region_name,
        competition__start_date__gte=two_years_ago,
        mark__isnull=False
    ).aggregate(avg=Avg('mark'))['avg'] or 0
    
    total_medals = total_gold + total_silver + total_bronze
    
    context = {
        'region_name': region_name,
        'participants': participants_data,
        'participants_count': len(participants_data),
        'competitions_data': competitions_data,
        'competitions_count': len(competitions_data),
        'total_gold': total_gold,
        'total_silver': total_silver,
        'total_bronze': total_bronze,
        'total_medals': total_medals,
        'overall_avg': round(overall_avg, 2) if overall_avg else 0,
    }
    
    return render(request, "region_detail.html", context)

def athletes(request):
    """Страница списка спортсменов - для всех зарегистрированных пользователей"""
    from .models import Participant, AthleteStatistics
    from django.http import HttpResponseForbidden
    
    # Проверка доступа: только для авторизованных пользователей
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, <a href='/auth/telegram/'>войдите через Telegram</a> для доступа.")
    
    # Получаем всех спортсменов со статистикой
    participants_with_stats = []
    participants = Participant.objects.all().order_by('name')
    
    for participant in participants:
        # Получаем статистику из сводной таблицы
        try:
            stats = participant.statistics
            participants_with_stats.append({
                'participant': participant,
                'competitions_count': stats.competitions_count,
                'performances_count': stats.performances_count,
                'gold_count': stats.gold_count,
                'silver_count': stats.silver_count,
                'bronze_count': stats.bronze_count,
                'avg_score': stats.avg_score,
                'total_medals': stats.gold_count + stats.silver_count + stats.bronze_count,
                'last_updated': stats.last_updated,
            })
        except AthleteStatistics.DoesNotExist:
            # Если статистики нет, добавляем пустые значения
            participants_with_stats.append({
                'participant': participant,
                'competitions_count': 0,
                'performances_count': 0,
                'gold_count': 0,
                'silver_count': 0,
                'bronze_count': 0,
                'avg_score': 0,
                'total_medals': 0,
                'last_updated': None,
            })
    
    # Сортируем по количеству медалей
    participants_with_stats.sort(key=lambda x: (x['total_medals'], x['gold_count'], x['silver_count']), reverse=True)
    
    # Получаем общую статистику
    total_athletes = Participant.objects.count()
    regions = list(Participant.objects.values_list('sity', flat=True).distinct().order_by('sity'))
    total_regions = len(regions)
    
    # Заглушки для званий (пока нет данных о званиях в БД)
    kms_count = 0  # КМС
    ms_count = 0   # МС
    msmk_count = 0 # МСМК
    razryadniki_count = 0  # Разрядники
    
    context = {
        'participants': participants_with_stats,
        'total_athletes': total_athletes,
        'total_regions': total_regions,
        'regions': regions,
        'kms_count': kms_count,
        'ms_count': ms_count,
        'msmk_count': msmk_count,
        'razryadniki_count': razryadniki_count,
    }
    
    return render(request, "athletes.html", context)


def athlete_detail(request, athlete_id):
    """Детальная страница спортсмена - только для тренеров и администраторов"""
    from .models import Participant, Performance, Competition, AgeCategory, AthleteStatistics
    from django.db.models import Count, Avg, Max, Min
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponseForbidden
    import json
    
    # Проверка доступа: только авторизованные тренеры или администраторы
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, войдите в систему.")
    
    is_admin = request.user.is_superuser
    is_coach = hasattr(request.user, 'coach_profile')
    
    if not is_admin and not is_coach:
        return HttpResponseForbidden("Доступ запрещён. Только для тренеров и администраторов.")
    
    participant = get_object_or_404(Participant, id=athlete_id)
    
    # Получаем параметр показа всех выступлений (включая нулевые)
    show_all = request.GET.get('show_all', 'false').lower() == 'true'
    
    # Фильтруем выступления в зависимости от настройки
    if show_all:
        performances = Performance.objects.filter(participant=participant).select_related(
            'competition', 'ages_category', 'disciplines_category'
        ).order_by('-competition__start_date', 'est_start_datetime')
    else:
        # По умолчанию скрываем нулевые выступления
        performances = Performance.objects.filter(participant=participant).exclude(mark=0).select_related(
            'competition', 'ages_category', 'disciplines_category'
        ).order_by('-competition__start_date', 'est_start_datetime')
    
    # Количество соревнований
    competitions_count = performances.values('competition').distinct().count()
    
    # Текущая возрастная категория (из последнего выступления)
    latest_performance = performances.first()
    current_age_category = latest_performance.ages_category if latest_performance else None
    
    # Получаем статистику из сводной таблицы (исключая нули)
    try:
        stats = participant.statistics
        gold_count = stats.gold_count
        silver_count = stats.silver_count
        bronze_count = stats.bronze_count
        avg_score = stats.avg_score
    except AthleteStatistics.DoesNotExist:
        # Если статистики нет, считаем напрямую
        gold_count = performances.filter(place=1).count()
        silver_count = performances.filter(place=2).count()
        bronze_count = performances.filter(place=3).count()
        avg_score = performances.filter(mark__isnull=False).exclude(mark=0).aggregate(avg=Avg('mark'))['avg'] or 0
    
    # Группируем выступления по соревнованиям
    competitions_data = []
    competitions_dict = {}
    
    for perf in performances:
        comp_id = perf.competition.id
        if comp_id not in competitions_dict:
            competitions_dict[comp_id] = {
                'competition': perf.competition,
                'performances': [],
                'performances_count': 0,
            }
        competitions_dict[comp_id]['performances'].append(perf)
        competitions_dict[comp_id]['performances_count'] += 1
    
    # Для каждого соревнования получаем дополнительную информацию
    for comp_id, comp_data in competitions_dict.items():
        competition = comp_data['competition']
        
        # Количество участников в соревновании
        participants_in_comp = Performance.objects.filter(
            competition=competition
        ).values('participant').distinct().count()
        
        # Получаем информацию о каждом выступлении с результатами категории
        performances_with_category = []
        for perf in comp_data['performances']:
            # Получаем всех участников в той же категории
            category_performances = Performance.objects.filter(
                competition=competition,
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category
            ).select_related('participant', 'ages_category').order_by('place', '-mark')
            
            # Используем место из БД
            place = perf.place if perf.place else None
            
            performances_with_category.append({
                'performance': perf,
                'place': place,
                'category_performances': list(category_performances),
                'category_name': f"{perf.ages_category} | {perf.disciplines_category}" if perf.ages_category and perf.disciplines_category else perf.origin_title,
            })
        
        # Получаем все баллы в возрастной категории спортсмена для гистограммы
        age_category = comp_data['performances'][0].ages_category if comp_data['performances'] else None
        if age_category:
            all_scores_in_age = list(Performance.objects.filter(
                competition=competition,
                ages_category=age_category,
                mark__isnull=False
            ).values_list('mark', flat=True))
        else:
            all_scores_in_age = []
        
        competitions_data.append({
            'competition': competition,
            'participants_count': participants_in_comp,
            'performances': performances_with_category,
            'performances_count': comp_data['performances_count'],
            'age_category_scores': json.dumps(all_scores_in_age),
            'age_category': age_category,
        })
    
    # Данные для графика изменения балла во времени
    score_timeline = []
    for perf in performances.filter(mark__isnull=False).order_by('competition__start_date'):
        score_timeline.append({
            'date': perf.competition.start_date.strftime('%Y-%m-%d'),
            'score': float(perf.mark),
            'competition': perf.competition.name,
            'category': perf.origin_title,
        })
    
    total_medals = gold_count + silver_count + bronze_count
    
    context = {
        'participant': participant,
        'competitions_count': competitions_count,
        'performances_count': performances.count(),
        'current_age_category': current_age_category,
        'gold_count': gold_count,
        'silver_count': silver_count,
        'bronze_count': bronze_count,
        'total_medals': total_medals,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'competitions_data': competitions_data,
        'score_timeline': json.dumps(score_timeline),
        'show_all': show_all,
    }
    
    return render(request, "athlete_detail.html", context)

def update_data(request):
    """Запускает синхронизацию данных с парсером"""
    from .DataController.parser import sync_all_data
    from django.http import JsonResponse
    
    try:
        sync_all_data(request)
        return JsonResponse({'success': True, 'message': 'Данные успешно обновлены'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def check_categories(request):
    print('hello')
    return JsonResponse({
        'success': True, 
        'message': f'Статистика обновлена.'
        })


def full_sync(request):
    """Запускает полную синхронизацию всех данных (соревнования + выступления)"""
    from .DataController.parser import full_sync_all_data
    from django.http import JsonResponse
    
    try:
        result = full_sync_all_data()
        return JsonResponse({
            'success': True, 
            'message': f'Синхронизация завершена. Соревнований: {result["competitions"]}, участников: {result["participants"]}, выступлений: {result["performances"]}'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def competition_analytics(request, competition_id):
    """Аналитика по конкретному соревнованию - только для тренеров и администраторов"""
    from .models import Competition, Performance, Participant, AgeCategory, Coach
    from django.db.models import Count, Avg, Q
    from django.http import HttpResponseForbidden
    import json
    
    # Проверка доступа: только авторизованные тренеры или администраторы
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Доступ запрещён. Пожалуйста, войдите в систему.")
    
    is_admin = request.user.is_superuser
    is_coach = hasattr(request.user, 'coach_profile')
    
    if not is_admin and not is_coach:
        return HttpResponseForbidden("Доступ запрещён. Только для тренеров и администраторов.")
    
    try:
        competition = Competition.objects.get(id=competition_id)
    except Competition.DoesNotExist:
        return render(request, "404.html", status=404)
    
    # Получаем все выступления на соревновании
    performances = Performance.objects.filter(competition=competition).select_related(
        'participant', 'ages_category', 'disciplines_category'
    )
    
    total_performances = performances.count()
    total_participants = performances.values('participant').distinct().count()
    
    # Общий средний балл по соревнованию
    avg_score = performances.filter(mark__isnull=False).aggregate(avg=Avg('mark'))['avg'] or 0
    
    # Распределение баллов по возрастным категориям
    age_categories_stats = []
    age_categories = AgeCategory.objects.filter(
        performance__competition=competition
    ).distinct()
    
    for age_cat in age_categories:
        cat_performances = performances.filter(ages_category=age_cat, mark__isnull=False)
        cat_avg = cat_performances.aggregate(avg=Avg('mark'))['avg'] or 0
        cat_count = cat_performances.count()
        
        if cat_count > 0:
            age_categories_stats.append({
                'category': str(age_cat),
                'avg_score': round(cat_avg, 2),
                'count': cat_count
            })
    
    # Сортируем по среднему баллу
    age_categories_stats.sort(key=lambda x: x['avg_score'], reverse=True)
    
    # Статистика по командам (регионам)
    teams_data = []
    teams = performances.values('participant__sity').distinct()
    
    for team in teams:
        team_name = team['participant__sity']
        if not team_name:
            continue
        
        # Выступления команды
        team_performances = performances.filter(participant__sity=team_name)
        team_performances_count = team_performances.count()
        
        # Уникальные участники команды
        team_participants = team_performances.values('participant').distinct().count()
        
        # Участники по возрастным категориям
        participants_by_age = {}
        for age_cat in age_categories:
            cat_participants = team_performances.filter(ages_category=age_cat).values('participant').distinct().count()
            if cat_participants > 0:
                participants_by_age[str(age_cat)] = cat_participants
        
        # Уникальные категории выступлений (дисциплина + возраст)
        unique_categories = team_performances.values('ages_category', 'disciplines_category').distinct().count()
        
        # Средний балл команды
        team_avg = team_performances.filter(mark__isnull=False).aggregate(avg=Avg('mark'))['avg'] or 0
        
        # Подсчет медалей (по полю place)
        gold = team_performances.filter(place=1).count()
        silver = team_performances.filter(place=2).count()
        bronze = team_performances.filter(place=3).count()
        total_medals = gold + silver + bronze
        
        # Соотношение выступлений к медалям
        if total_medals > 0:
            ratio = round(team_performances_count / total_medals, 2)
            efficiency = round((total_medals / team_performances_count) * 100, 1)
        else:
            ratio = 0
            efficiency = 0
        
        teams_data.append({
            'name': team_name,
            'participants': team_participants,
            'participants_by_age': participants_by_age,
            'performances': team_performances_count,
            'unique_categories': unique_categories,
            'avg_score': round(team_avg, 2),
            'gold': gold,
            'silver': silver,
            'bronze': bronze,
            'total_medals': total_medals,
            'ratio': ratio,
            'efficiency': efficiency
        })
    
    # Сортируем команды по количеству медалей
    teams_data.sort(key=lambda x: (x['total_medals'], x['gold'], x['silver']), reverse=True)
    
    # Данные для графика распределения баллов по возрастным категориям
    chart_labels = [cat['category'] for cat in age_categories_stats]
    chart_data = [cat['avg_score'] for cat in age_categories_stats]
    chart_counts = [cat['count'] for cat in age_categories_stats]
    
    # Данные для графика по командам (топ-10)
    top_teams = teams_data[:10]
    teams_chart_labels = [t['name'][:20] for t in top_teams]
    teams_chart_scores = [t['avg_score'] for t in top_teams]
    teams_chart_medals = [t['total_medals'] for t in top_teams]
    
    # Список всех возрастных категорий для заголовков таблицы
    all_age_categories = [str(cat) for cat in age_categories]
    
    context = {
        'competition': competition,
        'total_performances': total_performances,
        'total_participants': total_participants,
        'avg_score': round(avg_score, 2),
        'age_categories_stats': age_categories_stats,
        'teams_data': teams_data,
        'all_age_categories': all_age_categories,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'chart_counts': json.dumps(chart_counts),
        'teams_chart_labels': json.dumps(teams_chart_labels),
        'teams_chart_scores': json.dumps(teams_chart_scores),
        'teams_chart_medals': json.dumps(teams_chart_medals),
    }
    
    return render(request, "competition_analytics.html", context)


# ============== Custom Admin Panel ==============

def admin_users(request):
    """Страница управления пользователями - только для администраторов"""
    from django.contrib.auth.models import User
    from .models import Participant, Coach
    from django.http import HttpResponseForbidden
    
    # Проверка доступа: только суперпользователи
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещён. Только для администраторов.")
    
    # Получаем всех пользователей
    users = User.objects.all().order_by('-date_joined')
    
    users_data = []
    for user in users:
        is_coach = hasattr(user, 'coach_profile')
        teams = user.coach_profile.teams if is_coach else ''
        teams_list = user.coach_profile.get_teams_list() if is_coach else []
        
        users_data.append({
            'user': user,
            'is_coach': is_coach,
            'teams': teams,
            'teams_list': ','.join(teams_list),
        })
    
    # Получаем список всех команд для чекбоксов
    teams = list(Participant.objects.values_list('sity', flat=True).distinct().order_by('sity'))
    
    context = {
        'users': users_data,
        'teams': teams,
    }
    
    return render(request, "admin_users.html", context)


def admin_add_user(request):
    """Добавление нового пользователя"""
    from django.contrib.auth.models import User
    from .models import Coach
    from django.http import JsonResponse, HttpResponseForbidden
    from django.shortcuts import redirect
    from django.contrib import messages
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещён.")
    
    if request.method != 'POST':
        return redirect('admin_users')
    
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    password_confirm = request.POST.get('password_confirm', '')
    role = request.POST.get('role', 'user')
    teams = request.POST.getlist('teams')
    
    # Валидация
    if not username:
        messages.error(request, 'Имя пользователя обязательно')
        return redirect('admin_users')
    
    if password != password_confirm:
        messages.error(request, 'Пароли не совпадают')
        return redirect('admin_users')
    
    if User.objects.filter(username=username).exists():
        messages.error(request, 'Пользователь с таким именем уже существует')
        return redirect('admin_users')
    
    # Создаем пользователя
    user = User.objects.create_user(username=username, email=email, password=password)
    
    # Если роль - тренер, создаем профиль тренера
    if role == 'coach':
        Coach.objects.create(user=user, teams=', '.join(teams) if teams else '')
    
    messages.success(request, f'Пользователь {username} успешно создан')
    return redirect('admin_users')


def admin_edit_user(request):
    """Редактирование пользователя"""
    from django.contrib.auth.models import User
    from .models import Coach
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещён.")
    
    if request.method != 'POST':
        return redirect('admin_users')
    
    user_id = request.POST.get('user_id')
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    role = request.POST.get('role', 'user')
    teams = request.POST.getlist('teams')
    
    user = get_object_or_404(User, id=user_id)
    
    # Не позволяем редактировать суперпользователей
    if user.is_superuser:
        messages.error(request, 'Нельзя редактировать администратора')
        return redirect('admin_users')
    
    # Обновляем данные
    user.username = username
    user.email = email
    if password:
        user.set_password(password)
    user.save()
    
    # Обновляем профиль тренера
    if role == 'coach':
        coach, created = Coach.objects.get_or_create(user=user)
        coach.teams = ', '.join(teams) if teams else ''
        coach.save()
    else:
        # Удаляем профиль тренера, если роль изменена
        if hasattr(user, 'coach_profile'):
            user.coach_profile.delete()
    
    messages.success(request, f'Пользователь {username} успешно обновлён')
    return redirect('admin_users')


def admin_delete_user(request):
    """Удаление пользователя"""
    from django.contrib.auth.models import User
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещён.")
    
    if request.method != 'POST':
        return redirect('admin_users')
    
    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)
    
    # Не позволяем удалять суперпользователей
    if user.is_superuser:
        messages.error(request, 'Нельзя удалить администратора')
        return redirect('admin_users')
    
    # Не позволяем удалять себя
    if user == request.user:
        messages.error(request, 'Нельзя удалить самого себя')
        return redirect('admin_users')
    
    username = user.username
    user.delete()
    
    messages.success(request, f'Пользователь {username} успешно удалён')
    return redirect('admin_users')


def telegram_auth_view(request):
    """Аутентификация через ссылку от Telegram бота"""
    bot_context = get_telegram_bot_context()
    token_value = request.GET.get('token') or request.POST.get('token')

    if request.user.is_authenticated and not token_value:
        return redirect('dashboard')

    if not token_value:
        return render(request, 'telegram_auth.html', bot_context)

    login_token = TelegramLoginToken.objects.filter(token=token_value).first()
    if not login_token:
        messages.error(request, 'Ссылка недействительна. Получите новую в Telegram боте.')
        return render(request, 'telegram_auth.html', bot_context)

    if login_token.expires_at < timezone.now():
        login_token.delete()
        messages.error(request, 'Ссылка истекла. Получите новую в Telegram боте.')
        return render(request, 'telegram_auth.html', bot_context)

    if request.user.is_authenticated:
        if UserProfile.objects.filter(telegram_id=login_token.telegram_id).exclude(user=request.user).exists():
            messages.error(request, 'Этот Telegram уже привязан к другому аккаунту.')
            return render(request, 'telegram_auth.html', bot_context)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user = request.user
    else:
        profile = UserProfile.objects.filter(telegram_id=login_token.telegram_id).select_related('user').first()
        if profile:
            user = profile.user
        else:
            base_username = login_token.telegram_username or f"tg_{login_token.telegram_id}"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}_{suffix}"
            user = User.objects.create_user(
                username=username,
                email=f"telegram_{login_token.telegram_id}@wushu.local",
                password=User.objects.make_random_password()
            )
            profile = UserProfile.objects.create(user=user)

    profile.telegram_id = login_token.telegram_id
    profile.telegram_username = login_token.telegram_username
    profile.telegram_first_name = login_token.telegram_first_name
    profile.telegram_last_name = login_token.telegram_last_name
    profile.telegram_chat_id = login_token.telegram_chat_id
    profile.is_telegram_verified = True
    profile.save()

    login_token.delete()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Вы успешно вошли через Telegram!')
    return redirect('profile')


def register_view(request):
    """Регистрация отключена: направляем на Telegram вход"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    messages.info(request, 'Регистрация через email отключена. Войдите через Telegram.')
    return redirect('telegram_auth')


@login_required
def profile_view(request):
    """Страница профиля пользователя"""
    try:
        profile = request.user.user_profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    subscriptions = profile.subscriptions.filter(is_active=True)
    
    context = {
        'profile': profile,
        'subscriptions': subscriptions,
        **get_telegram_bot_context(),
    }
    return render(request, 'profile.html', context)


@login_required
@require_POST
@csrf_exempt
def unsubscribe_notification(request):
    """Отписка от уведомлений"""
    try:
        import json
        data = json.loads(request.body)
        subscription_id = data.get('subscription_id')
        
        profile = request.user.user_profile
        subscription = profile.subscriptions.get(id=subscription_id)
        subscription.is_active = False
        subscription.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def toggle_subscription(request):
    """Переключение подписки на уведомления"""
    try:
        import json
        data = json.loads(request.body)
        
        subscription_type = data.get('subscription_type')
        competition_id = data.get('competition_id')
        participant_id = data.get('participant_id')
        region_name = data.get('region_name')
        category_identifier = data.get('category_identifier')
        
        profile = request.user.user_profile
        
        # Ищем существующую подписку
        subscription = profile.subscriptions.filter(
            subscription_type=subscription_type,
            competition_id=competition_id,
            participant_id=participant_id,
            region_name=region_name,
            category_identifier=category_identifier
        ).first()
        
        if subscription:
            # Если подписка существует, деактивируем её
            subscription.is_active = not subscription.is_active
            subscription.save()
            is_subscribed = subscription.is_active
        else:
            # Создаем новую подписку
            subscription = NotificationSubscription.objects.create(
                user_profile=profile,
                subscription_type=subscription_type,
                competition_id=competition_id,
                participant_id=participant_id,
                region_name=region_name,
                category_identifier=category_identifier,
                is_active=True
            )
            is_subscribed = True
        
        return JsonResponse({
            'success': True,
            'is_subscribed': is_subscribed
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
