from ..models import (
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




# ============== INDIVIDUAL WRITE FUNCTIONS FOR EACH TABLE ==============

def write_competition_level(competition_level, level_description):
    """Записывает уровень соревнования"""
    obj, created = CompetitionLevel.objects.get_or_create(
        competition_level=competition_level,
        defaults={'level_description': level_description}
    )
    return obj, created

def write_discipline_category(name):
    """Записывает категорию дисциплины"""
    obj, created = DisciplineCategory.objects.get_or_create(name=name)
    return obj, created

def write_age_category(original_text, min_ages, max_ages, sex):
    """Записывает возрастную категорию"""
    obj, created = AgeCategory.objects.get_or_create(
        min_ages=min_ages,
        max_ages=max_ages,
        sex=sex,
        defaults={'original_text': original_text}
    )
    return obj, created

def write_region(region_name, participants_count=0, competitions_count=0, 
                performances_count=0, gold_count=0, silver_count=0, bronze_count=0):
    """Записывает регион"""
    obj, created = Regions.objects.get_or_create(
        region=region_name,
        defaults={
            'participants_count': participants_count,
            'competitions_count': competitions_count,
            'performances_count': performances_count,
            'gold_count': gold_count,
            'silver_count': silver_count,
            'bronze_count': bronze_count
        }
    )
    return obj, created

def write_participant(name, region_obj, competitions_count=0, performances_count=0,
                     gold_count=0, silver_count=0, bronze_count=0):
    """Записывает участника"""
    obj, created = Participant.objects.get_or_create(
        name=name,
        region=region_obj,
        defaults={
            'competitions_count': competitions_count,
            'performances_count': performances_count,
            'gold_count': gold_count,
            'silver_count': silver_count,
            'bronze_count': bronze_count
        }
    )
    return obj, created

def write_competition(link, name, city, start_date, end_date, competiton_active_status='unknown',
                     competition_level_obj=None, regions_count=0, participants_count=0,
                     performances_count=0, gold_count=0, silver_count=0, bronze_count=0):
    """Записывает соревнование"""
    obj, created = Competition.objects.get_or_create(
        name=name,
        city=city,
        start_date=start_date,
        end_date=end_date,
        defaults={
            'link': link,
            'competiton_active_status': competiton_active_status,
            'competition_level': competition_level_obj,
            'regions_count': regions_count,
            'participants_count': participants_count,
            'performances_count': performances_count,
            'gold_count': gold_count,
            'silver_count': silver_count,
            'bronze_count': bronze_count
        }
    )
    return obj, created

def write_performance_carpet(competition_obj, carpet=1):
    """Записывает ковер выступлений"""
    obj, created = PerformanceCarpet.objects.get_or_create(
        competition=competition_obj,
        carpet=carpet
    )
    return obj, created

def write_performance_category_block(performance_carpet_obj, age_category_obj=None,
                                   discipline_category_obj=None, participants_count=0,
                                   number_at_carpet=0, status='unknown'):
    """Записывает блок категорий выступлений"""
    obj, created = PerformanceCategoryBlock.objects.get_or_create(
        performance_category_carpet=performance_carpet_obj,
        age_category=age_category_obj,
        discipline_category=discipline_category_obj,
        defaults={
            'participants_count': participants_count,
            'number_at_carpet': number_at_carpet,
            'status': status
        }
    )
    return obj, created

def write_performance(origin_title, participant_obj, performance_category_block_obj=None,
                      est_start_datetime=None, real_start_datetime=None, mark=None,
                      place=None, number_at_block=0):
    """Записывает выступление"""
    obj, created = Performance.objects.get_or_create(
        participant=participant_obj,
        performance_category_block=performance_category_block_obj,
        defaults={
            'origin_title': origin_title,
            'est_start_datetime': est_start_datetime,
            'real_start_datetime': real_start_datetime,
            'mark': mark,
            'place': place,
            'number_at_block': number_at_block
        }
    )
    return obj, created

def write_user_profile(user_obj, telegram_id=None, telegram_username=None,
                       telegram_chat_id=None):
    """Записывает профиль пользователя"""
    obj, created = UserProfile.objects.get_or_create(
        user=user_obj,
        defaults={
            'telegram_id': telegram_id,
            'telegram_username': telegram_username,
            'telegram_chat_id': telegram_chat_id
        }
    )
    return obj, created

def write_coach(user_obj, teams='', telergam_profile_obj=None):
    """Записывает тренера"""
    obj, created = Coach.objects.get_or_create(
        user=user_obj,
        defaults={
            'teams': teams,
            'telergam_profile': telergam_profile_obj
        }
    )
    return obj, created

def write_tracked_participants(user_profile_obj, tracked_participant_obj):
    """Записывает отслеживаемого участника"""
    obj, created = TrackedParticipants.objects.get_or_create(
        user_profile=user_profile_obj,
        tracked_participant=tracked_participant_obj
    )
    return obj, created

def write_tracked_competition(user_profile_obj, tracked_competition_obj):
    """Записывает отслеживаемое соревнование"""
    obj, created = TrackedCompetition.objects.get_or_create(
        user_profile=user_profile_obj,
        tracked_competition=tracked_competition_obj
    )
    return obj, created

def write_tracked_region(user_profile_obj, tracked_region_obj):
    """Записывает отслеживаемый регион"""
    obj, created = TrackedRegion.objects.get_or_create(
        user_profile=user_profile_obj,
        tracked_region=tracked_region_obj
    )
    return obj, created

def write_tracked_category_block(user_profile_obj, tracked_category_block_obj):
    """Записывает отслеживаемый блок категорий"""
    obj, created = TrackedCategoryBlock.objects.get_or_create(
        user_profile=user_profile_obj,
        tracked_category_block=tracked_category_block_obj
    )
    return obj, created

def write_tracked_carpet(user_profile_obj, tracked_carpet_obj):
    """Записывает отслеживаемый ковер"""
    obj, created = TrackedCarpet.objects.get_or_create(
        user_profile=user_profile_obj,
        tracked_carpet=tracked_carpet_obj
    )
    return obj, created







# ============== UPDATE FUNCTIONS FOR TIME-VARYING DATA ==============

def update_region_statistics(region_name, participants_count=None, competitions_count=None,
                           performances_count=None, gold_count=None, silver_count=None, bronze_count=None):
    """Обновляет статистику региона - только изменяет указанные поля"""
    try:
        region = Regions.objects.get(region=region_name)
        
        # Обновляем только переданные поля
        if participants_count is not None:
            region.participants_count = participants_count
        if competitions_count is not None:
            region.competitions_count = competitions_count
        if performances_count is not None:
            region.performances_count = performances_count
        if gold_count is not None:
            region.gold_count = gold_count
        if silver_count is not None:
            region.silver_count = silver_count
        if bronze_count is not None:
            region.bronze_count = bronze_count
        
        region.save()
        return True, region
    except Regions.DoesNotExist:
        return False, f"Region '{region_name}' not found"

def update_participant_statistics(participant_name, region_obj=None, competitions_count=None,
                                performances_count=None, gold_count=None, silver_count=None, bronze_count=None):
    """Обновляет статистику участника - только изменяет указанные поля"""
    try:
        participant = Participant.objects.get(name=participant_name, region=region_obj)
        
        # Обновляем только переданные поля
        if competitions_count is not None:
            participant.competitions_count = competitions_count
        if performances_count is not None:
            participant.performances_count = performances_count
        if gold_count is not None:
            participant.gold_count = gold_count
        if silver_count is not None:
            participant.silver_count = silver_count
        if bronze_count is not None:
            participant.bronze_count = bronze_count
        
        participant.save()
        return True, participant
    except Participant.DoesNotExist:
        return False, f"Participant '{participant_name}' not found"

def update_competition_statistics(competition_id, regions_count=None, participants_count=None,
                                performances_count=None, gold_count=None, silver_count=None, bronze_count=None,
                                competiton_active_status=None):
    """Обновляет статистику соревнования - только изменяет указанные поля"""
    try:
        competition = Competition.objects.get(id=competition_id)
        
        # Обновляем только переданные поля
        if regions_count is not None:
            competition.regions_count = regions_count
        if participants_count is not None:
            competition.participants_count = participants_count
        if performances_count is not None:
            competition.performances_count = performances_count
        if gold_count is not None:
            competition.gold_count = gold_count
        if silver_count is not None:
            competition.silver_count = silver_count
        if bronze_count is not None:
            competition.bronze_count = bronze_count
        if competiton_active_status is not None:
            competition.competiton_active_status = competiton_active_status
        
        competition.save()
        return True, competition
    except Competition.DoesNotExist:
        return False, f"Competition with id '{competition_id}' not found"

def increment_region_stats(region_name, participants_increment=0, competitions_increment=0,
                         performances_increment=0, gold_increment=0, silver_increment=0, bronze_increment=0):
    """Увеличивает статистику региона на указанные значения"""
    try:
        region = Regions.objects.get(region=region_name)
        
        region.participants_count += participants_increment
        region.competitions_count += competitions_increment
        region.performances_count += performances_increment
        region.gold_count += gold_increment
        region.silver_count += silver_increment
        region.bronze_count += bronze_increment
        
        region.save()
        return True, region
    except Regions.DoesNotExist:
        return False, f"Region '{region_name}' not found"

def increment_participant_stats(participant_name, region_obj, competitions_increment=0,
                              performances_increment=0, gold_increment=0, silver_increment=0, bronze_increment=0):
    """Увеличивает статистику участника на указанные значения"""
    try:
        participant = Participant.objects.get(name=participant_name, region=region_obj)
        
        participant.competitions_count += competitions_increment
        participant.performances_count += performances_increment
        participant.gold_count += gold_increment
        participant.silver_count += silver_increment
        participant.bronze_count += bronze_increment
        
        participant.save()
        return True, participant
    except Participant.DoesNotExist:
        return False, f"Participant '{participant_name}' not found"

def increment_competition_stats(competition_id, regions_increment=0, participants_increment=0,
                              performances_increment=0, gold_increment=0, silver_increment=0, bronze_increment=0):
    """Увеличивает статистику соревнования на указанные значения"""
    try:
        competition = Competition.objects.get(id=competition_id)
        
        competition.regions_count += regions_increment
        competition.participants_count += participants_increment
        competition.performances_count += performances_increment
        competition.gold_count += gold_increment
        competition.silver_count += silver_increment
        competition.bronze_count += bronze_increment
        
        competition.save()
        return True, competition
    except Competition.DoesNotExist:
        return False, f"Competition with id '{competition_id}' not found"

def recalculate_region_statistics(region_name):
    """Пересчитывает всю статистику региона с нуля на основе данных выступлений"""
    from django.db.models import Count, Q, Avg
    
    try:
        region = Regions.objects.get(region=region_name)
        
        # Получаем все выступления региона
        performances = Performance.objects.filter(participant__region=region)
        
        # Уникальные участники
        participants_count = performances.values('participant').distinct().count()
        
        # Уникальные соревнования
        competitions_count = performances.values(
            'performance_category_block__performance_category_carpet__competition'
        ).distinct().count()
        
        # Всего выступлений
        performances_count = performances.count()
        
        # Медали
        gold_count = performances.filter(place=1).count()
        silver_count = performances.filter(place=2).count()
        bronze_count = performances.filter(place=3).count()
        
        # Обновляем все поля
        region.participants_count = participants_count
        region.competitions_count = competitions_count
        region.performances_count = performances_count
        region.gold_count = gold_count
        region.silver_count = silver_count
        region.bronze_count = bronze_count
        region.save()
        
        return True, region
    except Regions.DoesNotExist:
        return False, f"Region '{region_name}' not found"

def recalculate_participant_statistics(participant_name, region_obj):
    """Пересчитывает всю статистику участника с нуля на основе данных выступлений"""
    from django.db.models import Count, Q
    
    try:
        participant = Participant.objects.get(name=participant_name, region=region_obj)
        
        # Получаем все выступления участника
        performances = Performance.objects.filter(participant=participant)
        
        # Уникальные соревнования
        competitions_count = performances.values(
            'performance_category_block__performance_category_carpet__competition'
        ).distinct().count()
        
        # Всего выступлений
        performances_count = performances.count()
        
        # Медали
        gold_count = performances.filter(place=1).count()
        silver_count = performances.filter(place=2).count()
        bronze_count = performances.filter(place=3).count()
        
        # Обновляем все поля
        participant.competitions_count = competitions_count
        participant.performances_count = performances_count
        participant.gold_count = gold_count
        participant.silver_count = silver_count
        participant.bronze_count = bronze_count
        participant.save()
        
        return True, participant
    except Participant.DoesNotExist:
        return False, f"Participant '{participant_name}' not found"