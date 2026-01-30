from ..models import Competition, Participant, DisciplineCategory, AgeCategory, Performance


def write_competitions(competitions):
    """Записывает или обновляет соревнования в базе данных"""
    for competition in competitions:
        print(competition)
        
        # Используем update_or_create для уникальности по name, sity, start_date, end_date
        comp_obj, created = Competition.objects.update_or_create(
            name=competition['name'],
            sity=competition['city'],
            start_date=competition['start_date'],
            end_date=competition['end_date'],
            defaults={
                'link': competition['link']
            }
        )
        
        action = "Создано" if created else "Обновлено"
        print(f"{action} соревнование: {comp_obj.name}")


def write_participants(participants):
    """Записывает или обновляет участников в базе данных"""
    for participant in participants:
        # Используем update_or_create для уникальности по name, sity
        participant_obj, created = Participant.objects.update_or_create(
            name=participant['name'],
            sity=participant['city'],
            defaults={}
        )
        
        action = "Создан" if created else "Обновлен"
        print(f"{action} участник: {participant_obj.name}")


def write_discipline_categories(disciplines):
    """Записывает или обновляет дисциплины в базе данных"""
    for discipline in disciplines:
        # Используем get_or_create для уникальности по name
        discipline_obj, created = DisciplineCategory.objects.get_or_create(
            name=discipline['name']
        )
        
        action = "Создана" if created else "Найдена"
        print(f"{action} дисциплина: {discipline_obj.name}")


def write_age_categories(age_categories):
    """Записывает или обновляет возрастные категории в базе данных"""
    for age_cat in age_categories:
        # Используем update_or_create для уникальности по min_ages, max_ages, sex
        age_obj, created = AgeCategory.objects.update_or_create(
            min_ages=age_cat['min_ages'],
            max_ages=age_cat['max_ages'],
            sex=age_cat['sex'],
            defaults={}
        )
        
        action = "Создана" if created else "Найдена"
        print(f"{action} возрастная категория: {age_obj}")


def write_performances(performances):
    """Записывает или обновляет выступления в базе данных"""
    for performance in performances:
        # Используем update_or_create для уникальности по competition, participant, ages_category, disciplines_category
        perf_obj, created = Performance.objects.update_or_create(
            competition=performance['competition'],
            participant=performance['participant'],
            ages_category=performance['ages_category'],
            disciplines_category=performance['disciplines_category'],
            defaults={
                'carpet': performance['carpet'],
                'origin_title': performance['origin_title'],
                'est_start_datetime': performance['est_start_datetime'],
                'real_start_datetime': performance.get('real_start_datetime'),
                'mark': performance.get('mark')
            }
        )
        
        action = "Создано" if created else "Обновлено"
        print(f"{action} выступление: {perf_obj.participant.name} - {perf_obj.origin_title}")