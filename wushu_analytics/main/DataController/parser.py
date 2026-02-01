import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import ssl
from datetime import datetime
from .dataWriter import write_competitions
 
# Константы
BASE_URL = "https://wushujudges.ru"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 3
SLEEP_TIME = 0.5
 
 
# Отключаем проверку SSL сертификатов (только для разработки)
ssl._create_default_https_context = ssl._create_unverified_context
 
 
def fetch_page(url):
    print('fetching page: ', url)    
    response = requests.get(url, headers=HEADERS, verify=False)
    print('Page fetched')
    return response.text


def convert_date(date_str):
    """Конвертирует дату из DD.MM.YYYY в YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        return None
 
 
def parse_competitions():
    """Парсит список соревнований с главной страницы"""
    url = BASE_URL
    print(f'Parsing competitions from: {url}')
 
    html = fetch_page(url)
    if not html:
        print("Failed to fetch page")
        return []
 
    soup = BeautifulSoup(html, "html.parser")
    competitions = []
 
    # Находим таблицу с соревнованиями
    table = soup.find("table", class_="table")
    if not table:
        print("Table not found")
        return []
 
    # Получаем все строки tbody
    tbody = table.find("tbody")
    if not tbody:
        print("Tbody not found")
        return []
 
    rows = tbody.find_all("tr")
 
    for row in rows:
        # Пропускаем пустую строку
        if "datatable__empty" in row.get("class", []):
            continue
 
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
 
        # Извлекаем данные
        name_cell = cells[0].find("a")
        if not name_cell:
            continue
 
        name = name_cell.text.strip()
        link = name_cell.get("href", "")
        full_link = BASE_URL + link if link else ""
 
        city = cells[1].text.strip()
        start_date = convert_date(cells[2].text.strip())
        end_date = convert_date(cells[3].text.strip())
        
        # Пропускаем если даты не сконвертировались
        if not start_date or not end_date:
            continue
 
        competitions.append({
            "name": name,
            "city": city,
            "start_date": start_date,
            "end_date": end_date,
            "link": full_link
        })
 
    print(f"Found {len(competitions)} competitions:")
    for comp in competitions:
        print(f"- {comp['name']} ({comp['city']}) {comp['start_date']}-{comp['end_date']}")
 
    return competitions
 
 
def parse_competition_detail(competition_url):
    """Парсит детальную информацию о соревновании"""
    print(f'Parsing competition detail from: {competition_url}')
    
    html = fetch_page(competition_url)
    if not html:
        print("Failed to fetch competition page")
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Получаем название соревнования
    title_tag = soup.find("h1") or soup.find("title")
    competition_name = title_tag.text.strip().split(" | ")[-1] if title_tag else "Unknown"
    
    # Ищем регламент
    regulation = ""
    regulation_block = soup.find("div", class_="regulation") or soup.find("div", {"id": "regulation"})
    if regulation_block:
        regulation = regulation_block.get_text(strip=True)
    
    # Парсим категории по коврам
    categories = []
    current_time = datetime.now()
    
    # Ищем все блоки с категориями и сначала собираем их без статусов
    temp_categories = []
    
    # Ищем все блоки с категориями
    for category_block in soup.find_all("div", class_="d-flex"):
        category_name_tag = category_block.find("h3")
        if not category_name_tag:
            continue
        
        raw_category = category_name_tag.text.strip().replace("\n", " ")
        time_range = category_block.find("p").text.strip() if category_block.find("p") else ""
        
        # Сначала получаем участников
        table = category_block.find_next("table")
        if not table:
            continue
        
        headers = [th.text.strip() for th in table.find_all("th")]
        rows = [[td.text.strip() for td in tr.find_all("td")] for tr in table.find_all("tr") if tr.find_all("td")]
        
        participants = []
        if "#" in headers and "Имя" in headers:
            for row in rows:
                if len(row) < 5 or not row[1] or not row[2]:
                    continue
                if row[0] == competition_name:
                    continue
                
                participants.append({
                    "place": row[0],
                    "name": row[1],
                    "region": row[2],
                    "start_time": row[3],
                    "score": row[4] if len(row) > 4 else ""
                })
        
        temp_categories.append({
            "name": raw_category,
            "time_range": time_range,
            "participants": participants
        })
    
    # Теперь определяем статусы для всех категорий
    for temp_cat in temp_categories:
        status = determine_category_status(
            temp_cat["time_range"], 
            current_time, 
            temp_cat["participants"], 
            temp_cat["name"], 
            temp_categories
        )
        
        categories.append({
            "name": temp_cat["name"],
            "time_range": temp_cat["time_range"],
            "status": status,
            "participants": temp_cat["participants"]
        })
    
    return {
        "name": competition_name,
        "regulation": regulation,
        "categories": categories
    }


def determine_category_status(time_range, current_time, participants, category_name, all_categories):
    """Определяет статус категории на основе реального времени и последовательности"""
    if not participants:
        return "future"  # Нет участников - категория еще не началась
    
    # Проверяем есть ли начавшиеся выступления (оценка "-" означает что еще не прошло)
    participants_started = [p for p in participants 
                           if p.get("score") 
                           and p.get("score").strip() != "" 
                           and p.get("score").strip() != "-"]
    
    # Проверяем все ли участники получили оценки
    participants_with_mark = [p for p in participants 
                             if p.get("score") 
                             and p.get("score").strip() != "" 
                             and p.get("score").strip() != "-"]
    
    if len(participants_with_mark) == len(participants):
        return "past"  # Все получили оценки - категория завершена
    
    # Если есть хотя бы одно начавшееся выступление - категория идет
    if participants_started:
        return "current"
    
    # Извлекаем номер ковра из названия категории
    carpet_number = extract_carpet_number(category_name)
    
    if carpet_number:
        # Ищем предыдущие категории на этом же ковре
        previous_categories = [cat for cat in all_categories 
                              if extract_carpet_number(cat.get("name", "")) == carpet_number 
                              and cat.get("name", "") != category_name]
        
        # Проверяем завершена ли предыдущая категория
        previous_completed = True
        for prev_cat in previous_categories:
            prev_participants = prev_cat.get("participants", [])
            prev_with_marks = [p for p in prev_participants 
                              if p.get("score") 
                              and p.get("score").strip() != "" 
                              and p.get("score").strip() != "-"]
            if len(prev_with_marks) < len(prev_participants):
                previous_completed = False
                break
        
        if not previous_completed:
            return "future"  # Предыдущая категория еще не завершена
        
        # Если предыдущая категория завершена, эта скоро начнется
        return "next"
    
    # Если не удалось определить номер ковра, используем старую логику
    if participants_started:
        return "current"  # Есть начавшиеся выступления
    else:
        return "future"   # Нет начавшихся выступлений


def extract_carpet_number(category_name):
    """Извлекает номер ковра из названия категории"""
    import re
    # Ищем паттерны типа "Ковер 1", "Ковер 2", "К1", "К2" и т.д.
    patterns = [
        r'Ковер\s*(\d+)',
        r'К(\d+)',
        r'Carpet\s*(\d+)',
        r'C(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, category_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def split_category_name(raw_name):
    """Разделяет название категории на ковер и название категории"""
    parts = raw_name.split("Ковер")
    if len(parts) > 1:
        mat = parts[0].strip() + "Ковер"
        category_name = parts[1].strip()
        return mat, category_name
    return "", raw_name


def parse_competition_results(start_id, end_id):
    results = []
 
    for comp_id in range(start_id, end_id + 1):
        url = f"{BASE_URL}{comp_id}"
        print(f"🔍 Обработка: {url}")
        html = fetch_page(url)
        if not html:
            continue
 
        soup = BeautifulSoup(html, "html.parser")
        competition_name = soup.find("title").text.strip().split(" | ")[-1] if soup.find("title") else f"comp_{comp_id}"
 
        for category_block in soup.find_all("div", class_="d-flex"):
            category_name_tag = category_block.find("h3")
            if not category_name_tag:
                continue
 
            raw_category = category_name_tag.text.strip().replace("\n", " ")
            mat, category_name = split_category_name(raw_category)
            time_range = category_block.find("p").text.strip() if category_block.find("p") else ""
 
            table = category_block.find_next("table")
            if not table:
                continue
 
            headers = [th.text.strip() for th in table.find_all("th")]
            rows = [[td.text.strip() for td in tr.find_all("td")] for tr in table.find_all("tr") if tr.find_all("td")]
 
            if "#" in headers and "Имя" in headers:
                for row in rows:
                    if len(row) < 5 or not row[1] or not row[2]:
                        continue
 
                    if row[0] == competition_name:
                        continue
 
                    results.append({
                        "competition id": comp_id,
                        "competition name": competition_name,
                        "mat": mat,
                        "category name": category_name,
                        "place": row[0] if row else "",
                        "name": row[1] if len(row) > 1 else "",
                        "region": row[2] if len(row) > 2 else "",
                        "start time": row[3] if len(row) > 3 else "",
                        "score": row[4] if len(row) > 4 else "",
                    })
        time.sleep(SLEEP_TIME)
 
    df = pd.DataFrame(results)
    return df
 
 
 
 
def sync_all_data(request):
    """Синхронизирует все данные: список соревнований и детальную информацию"""
    print("=== Начало синхронизации данных ===")
    
    # 1. Получаем и сохраняем список соревнований
    print("1. Парсинг списка соревнований...")
    competitions = parse_competitions()
    write_competitions(competitions)
    print(f"Список соревнований обновлен: {len(competitions)} соревнований")
    
    # 2. Скачиваем детальную информацию о каждом соревновании
    print("2. Скачивание детальной информации о соревнованиях...")
    from ..models import Competition
    
    all_db_competitions = Competition.objects.all()
    details_count = 0
    
    for comp in all_db_competitions:
        if comp.link:
            print(f"  - Скачивание детальной информации: {comp.name}")
            detail_data = parse_competition_detail(comp.link)
            if detail_data:
                # Здесь можно сохранить детальную информацию в БД
                # Например, в отдельной модели или как JSON поле
                details_count += 1
                print(f"    ✓ Детальная информация получена")
            else:
                print(f"    ✗ Не удалось получить детальную информацию")
        else:
            print(f"  - Пропуск (нет ссылки): {comp.name}")
    
    print(f"Детальная информация скачана для {details_count} соревнований")
    print("=== Синхронизация завершена ===")
    print("Competitions written")


def parse_category_name(raw_category):
    """
    Парсит название категории и извлекает:
    - номер ковра
    - возрастную категорию (пол, мин возраст, макс возраст)
    - дисциплину
    
    Примеры входных данных:
    "Ковер 1 Мальчики (9-11 лет) Чанцюань"
    "Ковер 2 Девушки (12-14 лет) Наньцюань"
    """
    result = {
        'carpet': 1,
        'sex': None,
        'min_age': None,
        'max_age': None,
        'discipline': None
    }
    
    # Извлекаем номер ковра
    carpet_match = re.search(r'Ковер\s*(\d+)', raw_category, re.IGNORECASE)
    if carpet_match:
        result['carpet'] = int(carpet_match.group(1))
    
    # Извлекаем пол
    sex_patterns = [
        (r'Мальчики', 'М'),
        (r'Девочки', 'Ж'),
        (r'Юноши', 'М'),
        (r'Девушки', 'Ж'),
        (r'Мужчины', 'М'),
        (r'Женщины', 'Ж'),
        (r'Юниоры', 'М'),
        (r'Юниорки', 'Ж'),
    ]
    
    for pattern, sex in sex_patterns:
        if re.search(pattern, raw_category, re.IGNORECASE):
            result['sex'] = sex
            break
    
    # Извлекаем возрастной диапазон (9-11 лет) или (12-14)
    age_match = re.search(r'\((\d+)\s*[-–]\s*(\d+)\s*(?:лет|года|год)?\)', raw_category)
    if age_match:
        result['min_age'] = int(age_match.group(1))
        result['max_age'] = int(age_match.group(2))
    else:
        # Попробуем найти просто возраст (18+) или (до 12)
        age_single = re.search(r'\((\d+)\+?\)', raw_category)
        if age_single:
            result['min_age'] = int(age_single.group(1))
            result['max_age'] = 99
    
    # Извлекаем дисциплину - обычно последнее слово или словосочетание после возраста
    # Убираем ковер, пол и возраст из строки
    discipline_str = raw_category
    discipline_str = re.sub(r'Ковер\s*\d+', '', discipline_str, flags=re.IGNORECASE)
    discipline_str = re.sub(r'(Мальчики|Девочки|Юноши|Девушки|Мужчины|Женщины|Юниоры|Юниорки)', '', discipline_str, flags=re.IGNORECASE)
    discipline_str = re.sub(r'\(\d+\s*[-–]\s*\d+\s*(?:лет|года|год)?\)', '', discipline_str)
    discipline_str = re.sub(r'\(\d+\+?\)', '', discipline_str)
    discipline_str = discipline_str.strip()
    
    if discipline_str:
        result['discipline'] = discipline_str
    
    return result


def full_sync_all_data():
    """
    Полная синхронизация всех данных:
    1. Скачивает все соревнования
    2. Для каждого соревнования скачивает все выступления
    3. Сохраняет участников, категории и выступления в БД
    """
    from ..models import Competition, Participant, DisciplineCategory, AgeCategory, Performance
    from .dataWriter import write_competitions
    
    print("=" * 60)
    print("=== ПОЛНАЯ СИНХРОНИЗАЦИЯ ДАННЫХ ===")
    print("=" * 60)
    
    # 1. Получаем и сохраняем список соревнований
    print("\n[1/3] Парсинг списка соревнований...")
    competitions = parse_competitions()
    write_competitions(competitions)
    print(f"✓ Список соревнований обновлен: {len(competitions)} соревнований")
    
    # 2. Получаем все соревнования из БД
    all_db_competitions = Competition.objects.all()
    total_competitions = all_db_competitions.count()
    
    print(f"\n[2/3] Скачивание выступлений для {total_competitions} соревнований...")
    
    total_performances = 0
    total_participants = 0
    
    for idx, comp in enumerate(all_db_competitions, 1):
        print(f"\n--- [{idx}/{total_competitions}] {comp.name} ---")
        
        if not comp.link:
            print("  ⚠ Пропуск (нет ссылки)")
            continue
        
        try:
            detail_data = parse_competition_detail(comp.link)
            if not detail_data or not detail_data.get('categories'):
                print("  ⚠ Нет данных о категориях")
                continue
            
            categories = detail_data['categories']
            print(f"  Найдено категорий: {len(categories)}")
            
            for category in categories:
                category_name = category.get('name', '')
                participants = category.get('participants', [])
                
                if not participants:
                    continue
                
                # Парсим название категории
                parsed = parse_category_name(category_name)
                
                # Получаем или создаем дисциплину
                discipline_obj = None
                if parsed['discipline']:
                    discipline_obj, _ = DisciplineCategory.objects.get_or_create(
                        name=parsed['discipline']
                    )
                
                # Получаем или создаем возрастную категорию
                age_category_obj = None
                if parsed['sex'] and parsed['min_age'] and parsed['max_age']:
                    age_category_obj, _ = AgeCategory.objects.get_or_create(
                        min_ages=parsed['min_age'],
                        max_ages=parsed['max_age'],
                        sex=parsed['sex']
                    )
                
                # Обрабатываем каждого участника
                for participant in participants:
                    participant_name = participant.get('name', '').strip()
                    participant_region = participant.get('region', '').strip()
                    start_time = participant.get('start_time', '')
                    score = participant.get('score', '')
                    
                    if not participant_name or not participant_region:
                        continue
                    
                    # Получаем или создаем участника
                    participant_obj, created = Participant.objects.get_or_create(
                        name=participant_name,
                        sity=participant_region
                    )
                    if created:
                        total_participants += 1
                    
                    # Парсим время начала
                    est_start = None
                    if start_time:
                        try:
                            time_parts = start_time.split(':')
                            if len(time_parts) >= 2:
                                from datetime import datetime, timedelta
                                est_start = datetime.combine(
                                    comp.start_date,
                                    datetime.strptime(start_time, '%H:%M').time()
                                )
                        except:
                            est_start = datetime.combine(comp.start_date, datetime.min.time())
                    else:
                        from datetime import datetime
                        est_start = datetime.combine(comp.start_date, datetime.min.time())
                    
                    # Парсим оценку
                    mark = None
                    if score and score.strip() and score.strip() != '-':
                        try:
                            mark = float(score.replace(',', '.'))
                        except:
                            mark = None
                    
                    # Парсим место
                    place_value = None
                    place_str = participant.get('place', '')
                    if place_str and place_str.strip():
                        try:
                            place_value = int(place_str.strip())
                        except:
                            place_value = None
                    
                    # Создаем или обновляем выступление
                    try:
                        perf_obj, created = Performance.objects.update_or_create(
                            competition=comp,
                            participant=participant_obj,
                            ages_category=age_category_obj,
                            disciplines_category=discipline_obj,
                            defaults={
                                'carpet': parsed['carpet'],
                                'origin_title': category_name,
                                'est_start_datetime': est_start,
                                'mark': mark,
                                'place': place_value
                            }
                        )
                        if created:
                            total_performances += 1
                    except Exception as e:
                        print(f"    ⚠ Ошибка при создании выступления: {e}")
                        continue
            
            print(f"  ✓ Обработано")
            
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
            continue
        
        # Небольшая задержка между соревнованиями
        time.sleep(SLEEP_TIME)
    
    # Обновляем сводную статистику после синхронизации
    print("\n--- Обновление сводной статистики ---")
    try:
        from main.models import RegionStatistics, AthleteStatistics
        from django.db.models import Count, Avg
        
        # Обновляем статистику регионов
        regions = Participant.objects.values_list('sity', flat=True).distinct()
        for region in regions:
            if not region:
                continue
            
            region_performances = Performance.objects.filter(
                participant__sity=region,
                mark__isnull=False
            ).exclude(mark=0)
            
            participants_count = Participant.objects.filter(sity=region).count()
            competitions_count = region_performances.values('competition').distinct().count()
            performances_count = region_performances.count()
            gold_count = region_performances.filter(place=1).count()
            silver_count = region_performances.filter(place=2).count()
            bronze_count = region_performances.filter(place=3).count()
            avg_score = region_performances.aggregate(avg=Avg('mark'))['avg'] or 0
            
            RegionStatistics.objects.update_or_create(
                region=region,
                defaults={
                    'participants_count': participants_count,
                    'competitions_count': competitions_count,
                    'performances_count': performances_count,
                    'gold_count': gold_count,
                    'silver_count': silver_count,
                    'bronze_count': bronze_count,
                    'avg_score': round(avg_score, 2) if avg_score else 0,
                }
            )
        
        # Обновляем статистику спортсменов
        participants = Participant.objects.all()
        for participant in participants:
            performances = Performance.objects.filter(
                participant=participant,
                mark__isnull=False
            ).exclude(mark=0)
            
            competitions_count = performances.values('competition').distinct().count()
            performances_count = performances.count()
            gold_count = performances.filter(place=1).count()
            silver_count = performances.filter(place=2).count()
            bronze_count = performances.filter(place=3).count()
            avg_score = performances.aggregate(avg=Avg('mark'))['avg'] or 0
            
            AthleteStatistics.objects.update_or_create(
                participant=participant,
                defaults={
                    'competitions_count': competitions_count,
                    'performances_count': performances_count,
                    'gold_count': gold_count,
                    'silver_count': silver_count,
                    'bronze_count': bronze_count,
                    'avg_score': round(avg_score, 2) if avg_score else 0,
                }
            )
        
        print("✓ Статистика обновлена")
        
    except Exception as e:
        print(f"✗ Ошибка обновления статистики: {e}")
    
    print("\n" + "=" * 60)
    print("=== СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА ===")
    print(f"Соревнований: {total_competitions}")
    print(f"Новых участников: {total_participants}")
    print(f"Новых выступлений: {total_performances}")
    print("=" * 60)
    
    return {
        'competitions': total_competitions,
        'participants': total_participants,
        'performances': total_performances
    }