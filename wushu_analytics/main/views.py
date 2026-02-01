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
    """Страница списка регионов/команд"""
    from .models import Participant, Performance, Competition
    from django.db.models import Count, Avg, Q
    from datetime import date, timedelta
    
    # Дата 2 года назад для расчета среднего балла
    two_years_ago = date.today() - timedelta(days=730)
    
    # Получаем список уникальных регионов с агрегированной статистикой
    regions_data = []
    regions_list = Participant.objects.values_list('sity', flat=True).distinct().order_by('sity')
    
    for region in regions_list:
        # Участники региона
        participants = Participant.objects.filter(sity=region)
        participants_count = participants.count()
        
        # Количество соревнований, в которых участвовал регион
        competitions_count = Performance.objects.filter(
            participant__sity=region
        ).values('competition').distinct().count()
        
        # Средний балл за последние 2 года
        avg_score = Performance.objects.filter(
            participant__sity=region,
            competition__start_date__gte=two_years_ago,
            mark__isnull=False
        ).aggregate(avg=Avg('mark'))['avg'] or 0
        
        # Подсчет медалей (по местам в категориях)
        gold_count = 0
        silver_count = 0
        bronze_count = 0
        
        # Получаем все выступления региона
        region_performances = Performance.objects.filter(
            participant__sity=region,
            mark__isnull=False
        ).select_related('competition', 'ages_category', 'disciplines_category', 'participant')
        
        for perf in region_performances:
            # Определяем место в категории
            better_count = Performance.objects.filter(
                competition=perf.competition,
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category,
                mark__gt=perf.mark
            ).count()
            
            place = better_count + 1
            if place == 1:
                gold_count += 1
            elif place == 2:
                silver_count += 1
            elif place == 3:
                bronze_count += 1
        
        regions_data.append({
            'name': region,
            'participants_count': participants_count,
            'competitions_count': competitions_count,
            'avg_score': round(avg_score, 2) if avg_score else 0,
            'gold_count': gold_count,
            'silver_count': silver_count,
            'bronze_count': bronze_count,
            'total_medals': gold_count + silver_count + bronze_count,
        })
    
    # Сортируем по количеству участников
    regions_data.sort(key=lambda x: x['participants_count'], reverse=True)
    
    # Общая статистика
    total_regions = len(regions_data)
    total_participants = Participant.objects.count()
    
    context = {
        'regions': regions_data,
        'total_regions': total_regions,
        'total_participants': total_participants,
    }
    
    return render(request, "regions.html", context)


def region_detail(request, region_name):
    """Детальная страница региона/команды"""
    from .models import Participant, Performance, Competition
    from django.db.models import Count, Avg, Q
    from datetime import date, timedelta
    from urllib.parse import unquote
    import json
    
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
        
        # Медали
        gold = silver = bronze = 0
        for perf in performances.filter(mark__isnull=False):
            better_count = Performance.objects.filter(
                competition=perf.competition,
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category,
                mark__gt=perf.mark
            ).count()
            place = better_count + 1
            if place == 1:
                gold += 1
            elif place == 2:
                silver += 1
            elif place == 3:
                bronze += 1
        
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
        
        # Медали команды на соревновании
        gold = silver = bronze = 0
        for perf in team_performances.filter(mark__isnull=False):
            better_count = Performance.objects.filter(
                competition=competition,
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category,
                mark__gt=perf.mark
            ).count()
            place = better_count + 1
            if place == 1:
                gold += 1
            elif place == 2:
                silver += 1
            elif place == 3:
                bronze += 1
        
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
    
    context = {
        'region_name': region_name,
        'participants': participants_data,
        'participants_count': len(participants_data),
        'competitions_data': competitions_data,
        'competitions_count': len(competitions_data),
        'total_gold': total_gold,
        'total_silver': total_silver,
        'total_bronze': total_bronze,
        'overall_avg': round(overall_avg, 2) if overall_avg else 0,
    }
    
    return render(request, "region_detail.html", context)

def athletes(request):
    """Страница списка спортсменов"""
    from .models import Participant, Performance, Competition
    from django.db.models import Count, Q, Max
    
    # Получаем всех спортсменов с агрегированной информацией
    participants = Participant.objects.annotate(
        competitions_count=Count('performance__competition', distinct=True),
        performances_count=Count('performance'),
        gold_count=Count('performance', filter=Q(performance__mark__isnull=False) & Q(performance__mark__gte=9.0)),
        silver_count=Count('performance', filter=Q(performance__mark__isnull=False) & Q(performance__mark__gte=8.5) & Q(performance__mark__lt=9.0)),
        bronze_count=Count('performance', filter=Q(performance__mark__isnull=False) & Q(performance__mark__gte=8.0) & Q(performance__mark__lt=8.5)),
    ).order_by('name')
    
    # Получаем статистику
    total_athletes = Participant.objects.count()
    regions = list(Participant.objects.values_list('sity', flat=True).distinct().order_by('sity'))
    total_regions = len(regions)
    
    # Заглушки для званий (пока нет данных о званиях в БД)
    kms_count = 0  # КМС
    ms_count = 0   # МС
    msmk_count = 0 # МСМК
    razryadniki_count = 0  # Разрядники
    
    context = {
        'participants': participants,
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
    """Детальная страница спортсмена"""
    from .models import Participant, Performance, Competition, AgeCategory
    from django.db.models import Count, Avg, Max, Min
    from django.shortcuts import get_object_or_404
    import json
    
    participant = get_object_or_404(Participant, id=athlete_id)
    
    # Получаем все выступления спортсмена
    performances = Performance.objects.filter(participant=participant).select_related(
        'competition', 'ages_category', 'disciplines_category'
    ).order_by('-competition__start_date', 'est_start_datetime')
    
    # Количество соревнований
    competitions_count = performances.values('competition').distinct().count()
    
    # Текущая возрастная категория (из последнего выступления)
    latest_performance = performances.first()
    current_age_category = latest_performance.ages_category if latest_performance else None
    
    # Подсчет медалей (на основе места в категории)
    gold_count = 0
    silver_count = 0
    bronze_count = 0
    
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
            # Получаем всех участников в той же категории с учетом пола
            # Дополнительная проверка, чтобы в категории были только участники одного пола
            category_performances = Performance.objects.filter(
                competition=competition,
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category
            ).select_related('participant', 'ages_category').order_by('-mark')
            
            # Фильтруем по полу, если возрастная категория имеет пол
            if perf.ages_category and perf.ages_category.sex:
                # Дополнительная проверка - убеждаемся что все участники в категории имеют тот же пол
                category_performances = category_performances.filter(
                    ages_category__sex=perf.ages_category.sex
                )
                print(f"Category: {perf.origin_title}, Sex: {perf.ages_category.sex}, Participants: {category_performances.count()}")
            
            # Определяем место спортсмена
            place = 1
            for idx, cat_perf in enumerate(category_performances, 1):
                if cat_perf.participant.id == participant.id:
                    place = idx
                    break
            
            # Подсчитываем медали
            if place == 1 and perf.mark:
                gold_count += 1
            elif place == 2 and perf.mark:
                silver_count += 1
            elif place == 3 and perf.mark:
                bronze_count += 1
            
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
    
    context = {
        'participant': participant,
        'competitions_count': competitions_count,
        'performances_count': performances.count(),
        'current_age_category': current_age_category,
        'gold_count': gold_count,
        'silver_count': silver_count,
        'bronze_count': bronze_count,
        'competitions_data': competitions_data,
        'score_timeline': json.dumps(score_timeline),
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
    pass


def check_categories(request):
    """Выгружает все таблицы в CSV файлы"""
    import csv
    import io
    from django.http import HttpResponse
    from .models import Competition, Participant, DisciplineCategory, AgeCategory, Performance
    
    print("=== ВЫГРУЗКА ТАБЛИЦ В CSV ===")
    
    # Создаем ZIP архив со всеми CSV файлами
    import zipfile
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        # 1. Выгрузка соревнований
        competitions = Competition.objects.all()
        print(f"Выгрузка соревнований: {competitions.count()} записей")
        
        comp_buffer = io.StringIO()
        comp_writer = csv.writer(comp_buffer)
        comp_writer.writerow(['id', 'name', 'sity', 'start_date', 'end_date', 'link'])
        for comp in competitions:
            comp_writer.writerow([comp.id, comp.name, comp.sity, comp.start_date, comp.end_date, comp.link])
        
        zip_file.writestr('competitions.csv', comp_buffer.getvalue())
        comp_buffer.close()
        
        # 2. Выгрузка участников
        participants = Participant.objects.all()
        print(f"Выгрузка участников: {participants.count()} записей")
        
        part_buffer = io.StringIO()
        part_writer = csv.writer(part_buffer)
        part_writer.writerow(['id', 'name', 'sity'])
        for part in participants:
            part_writer.writerow([part.id, part.name, part.sity])
        
        zip_file.writestr('participants.csv', part_buffer.getvalue())
        part_buffer.close()
        
        # 3. Выгрузка дисциплин
        disciplines = DisciplineCategory.objects.all()
        print(f"Выгрузка дисциплин: {disciplines.count()} записей")
        
        disc_buffer = io.StringIO()
        disc_writer = csv.writer(disc_buffer)
        disc_writer.writerow(['id', 'name'])
        for disc in disciplines:
            disc_writer.writerow([disc.id, disc.name])
        
        zip_file.writestr('disciplines.csv', disc_buffer.getvalue())
        disc_buffer.close()
        
        # 4. Выгрузка возрастных категорий
        age_categories = AgeCategory.objects.all()
        print(f"Выгрузка возрастных категорий: {age_categories.count()} записей")
        
        age_buffer = io.StringIO()
        age_writer = csv.writer(age_buffer)
        age_writer.writerow(['id', 'min_ages', 'max_ages', 'sex'])
        for age_cat in age_categories:
            age_writer.writerow([age_cat.id, age_cat.min_ages, age_cat.max_ages, age_cat.sex])
        
        zip_file.writestr('age_categories.csv', age_buffer.getvalue())
        age_buffer.close()
        
        # 5. Выгрузка выступлений
        performances = Performance.objects.select_related(
            'competition', 'participant', 'ages_category', 'disciplines_category'
        ).all()
        print(f"Выгрузка выступлений: {performances.count()} записей")
        
        perf_buffer = io.StringIO()
        perf_writer = csv.writer(perf_buffer)
        perf_writer.writerow([
            'id', 'carpet', 'origin_title', 'competition_id', 'competition_name',
            'participant_id', 'participant_name', 'participant_sity',
            'ages_category_id', 'ages_category_str',
            'disciplines_category_id', 'disciplines_category_name',
            'est_start_datetime', 'real_start_datetime', 'real_end_datetime', 'mark'
        ])
        
        for perf in performances:
            perf_writer.writerow([
                perf.id,
                perf.carpet,
                perf.origin_title,
                perf.competition.id,
                perf.competition.name,
                perf.participant.id,
                perf.participant.name,
                perf.participant.sity,
                perf.ages_category.id if perf.ages_category else '',
                str(perf.ages_category) if perf.ages_category else '',
                perf.disciplines_category.id if perf.disciplines_category else '',
                perf.disciplines_category.name if perf.disciplines_category else '',
                perf.est_start_datetime,
                perf.real_start_datetime,
                perf.real_end_datetime,
                perf.mark
            ])
        
        zip_file.writestr('performances.csv', perf_buffer.getvalue())
        perf_buffer.close()
    
    zip_buffer.seek(0)
    
    print("=== ВЫГРУЗКА ЗАВЕРШЕНА ===")
    
    # Создаем HTTP ответ с ZIP архивом
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="wushu_database_export.zip"'
    
    return response


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
    """Аналитика по конкретному соревнованию"""
    from .models import Competition, Performance, Participant, AgeCategory
    from django.db.models import Count, Avg, Q
    import json
    
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
        
        # Подсчет медалей
        gold = 0
        silver = 0
        bronze = 0
        
        for perf in team_performances.filter(mark__isnull=False):
            # Получаем всех участников в той же категории
            category_perfs = performances.filter(
                ages_category=perf.ages_category,
                disciplines_category=perf.disciplines_category,
                mark__isnull=False
            )
            
            if perf.ages_category and perf.ages_category.sex:
                category_perfs = category_perfs.filter(ages_category__sex=perf.ages_category.sex)
            
            # Считаем сколько лучших результатов
            better_count = category_perfs.filter(mark__gt=perf.mark).count()
            place = better_count + 1
            
            if place == 1:
                gold += 1
            elif place == 2:
                silver += 1
            elif place == 3:
                bronze += 1
        
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
