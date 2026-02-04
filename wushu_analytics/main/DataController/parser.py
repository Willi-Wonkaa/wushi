import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import ssl
from datetime import datetime
from .dataWriter import (
    # Individual write functions
    write_competition_level,
    write_discipline_category,
    write_age_category,
    write_region,
    write_participant,
    write_competition,
    write_performance_carpet,
    write_performance_category_block,
    write_performance,
    write_user_profile,
    write_coach,
    write_tracked_participants,
    write_tracked_competition,
    write_tracked_region,
    write_tracked_category_block,
    write_tracked_carpet,
    
    # Update functions
    update_region_statistics,
    update_participant_statistics,
    update_competition_statistics,
    increment_region_stats,
    increment_participant_stats,
    increment_competition_stats,
    recalculate_region_statistics,
    recalculate_participant_statistics
) 


 
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
 
 

def write_competitions(competitions):
    for comp in competitions:
        competition_obj, created = write_competition(
            link=comp.get('link', ''),
            name=comp['name'],
            city=comp['city'],
            start_date=comp['start_date'],
            end_date=comp['end_date']
        )
        
        action = "Создано" if created else "Обновлено"
        print(f"{action} соревнование: {competition_obj.name}")
               

 


 

def parse_competition_detail(competition_url):
    """Парсит детальную информацию о соревновании с коврами и категориями"""
    print(f'Parsing competition detail from: {competition_url}')
    
    html = fetch_page(competition_url)
    if not html:
        print("Failed to fetch competition page")
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    print(soup)
    
    # # Получаем название соревнования
    # title_tag = soup.find("h1") or soup.find("title")
    # competition_name = title_tag.text.strip().split(" | ")[-1] if title_tag else "Unknown"
    
    # # Структура для хранения данных
    # competition_data = {
    #     "name": competition_name,
    #     "carpets": []  # Список ковров с категориями и выступлениями
    # }
    
    # # Ищем все заголовки ковров (h3 с id="carpet-X")
    # carpet_headers = soup.find_all("h3", id=lambda x: x and x.startswith("carpet-"))
    
    # for carpet_header in carpet_headers:
    #     # Извлекаем номер ковра
    #     carpet_id = carpet_header.get("id", "")
    #     carpet_number = extract_carpet_number_from_id(carpet_id)
        
    #     if not carpet_number:
    #         continue
            
    #     # Получаем текст заголовка (например, "Ковер 1")
    #     carpet_text = carpet_header.text.strip()
        
    #     # Инициализируем данные ковра
    #     carpet_data = {
    #         "carpet_number": carpet_number,
    #         "carpet_text": carpet_text,
    #         "category_blocks": []
    #     }
        
    #     # Ищем следующий блок с категориями после заголовка ковра
    #     current_element = carpet_header.find_next_sibling()
        
    #     while current_element:
    #         # Если мы встретили следующий ковер, выходим из цикла
    #         if current_element.name == "h3" and current_element.get("id", "").startswith("carpet-"):
    #             break
                
    #         # Ищем блоки категорий (div с d-flex классом)
    #         if current_element.name == "div" and "d-flex" in current_element.get("class", []):
    #             category_block = parse_category_block(current_element, carpet_number)
    #             if category_block:
    #                 carpet_data["category_blocks"].append(category_block)
            
    #         current_element = current_element.find_next_sibling()
        
    #     competition_data["carpets"].append(carpet_data)
    
    # print(f"Found {len(competition_data['carpets'])} carpets")
    # for carpet in competition_data["carpets"]:
    #     print(f"  Carpet {carpet['carpet_number']}: {len(carpet['category_blocks'])} category blocks")
    
    # return competition_data



def extract_carpet_number_from_id(carpet_id):
    """Извлекает номер ковра из id (например, 'carpet-1' -> 1)"""
    import re
    match = re.search(r'carpet-(\d+)', carpet_id)
    if match:
        return int(match.group(1))
    return None




def parse_category_block(category_element, carpet_number):
    """Парсит блок категории"""
    # Ищем название категории
    category_name_tag = category_element.find("h3")
    if not category_name_tag:
        return None
        
    category_name = category_name_tag.text.strip()
    
    # Ищем время проведения
    time_element = category_element.find("p")
    time_range = time_element.text.strip() if time_element else ""
    
    # Ищем таблицу с выступлениями
    table = category_element.find_next("table")
    if not table:
        return None
    
    # Парсим таблицу
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = [[td.text.strip() for td in tr.find_all("td")] for tr in table.find_all("tr") if tr.find_all("td")]
    
    participants = []
    if "#" in headers and "Имя" in headers:
        for row in rows:
            if len(row) < 5 or not row[1] or not row[2]:
                continue
                
            participants.append({
                "place": row[0],
                "name": row[1],
                "region": row[2],
                "start_time": row[3],
                "score": row[4] if len(row) > 4 else ""
            })
    
    # Определяем статус категории
    status = determine_category_status_new(time_range, participants)
    
    # Парсим название категории для извлечения компонентов
    parsed_category = parse_category_name(category_name)
    
    return {
        "category_name": category_name,
        "time_range": time_range,
        "status": status,
        "participants": participants,
        "parsed": parsed_category  # содержит carpet, sex, min_age, max_age, discipline
    }


def determine_category_status_new(time_range, participants):
    """Определяет статус категории на основе участников"""
    if not participants:
        return "future"  # Нет участников - категория еще не началась
    
    # Проверяем есть ли оценки у участников
    participants_with_score = [p for p in participants 
                             if p.get("score") 
                             and p.get("score").strip() != "" 
                             and p.get("score").strip() != "-"]
    
    if len(participants_with_score) == len(participants):
        return "completed"  # Все получили оценки - категория завершена
    
    if participants_with_score:
        return "current"  # Есть начавшиеся выступления
    
    return "future"  # Нет оценок - категория еще не началась


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
    from ..models import Competition
    from .dataWriter import write_competitions, write_competition_detail, update_competition_statistics, update_region_statistics, update_participant_statistics
    
    print("=" * 60)
    print("=== ПОЛНАЯ СИНХРОНИЗАЦИЯ ДАННЫХ ===")
    print("=" * 60)
    
    # 1. Получаем и сохраняем список соревнований
    print("\n[1/4] Парсинг списка соревнований...")
    competitions = parse_competitions()
    write_competitions(competitions)
    print(f"✓ Список соревнований обновлен: {len(competitions)} соревнований")
    
    # 2. Получаем все соревнования из БД
    all_db_competitions = Competition.objects.all()
    total_competitions = all_db_competitions.count()
    
    print(f"\n[2/4] Скачивание выступлений для {total_competitions} соревнований...")
    
    total_performances = 0
    total_participants = 0
    processed_competitions = 0
    
    for idx, comp in enumerate(all_db_competitions, 1):
        print(f"\n--- [{idx}/{total_competitions}] {comp.name} ---")
        
        if not comp.link:
            print("  ⚠ Пропуск (нет ссылки)")
            continue
        
        try:
            detail_data = parse_competition_detail(comp.link)
            if not detail_data or not detail_data.get('carpets'):
                print("  ⚠ Нет данных о коврах")
                continue
            
            # Записываем детальную информацию
            result = write_competition_detail(comp, detail_data)
            if result:
                total_participants += result['participants']
                total_performances += result['performances']
                processed_competitions += 1
                
            # Обновляем статистику соревнования
            update_competition_statistics(comp)
            
            print(f"  ✓ Обработано")
            
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
            continue
        
        # Небольшая задержка между соревнованиями
        time.sleep(SLEEP_TIME)
    
    # 3. Обновляем сводную статистику после синхронизации
    print(f"\n[3/4] Обновление статистики регионов...")
    try:
        update_region_statistics()
        print("✓ Статистика регионов обновлена")
    except Exception as e:
        print(f"✗ Ошибка обновления статистики регионов: {e}")
    
    print(f"\n[4/4] Обновление статистики участников...")
    try:
        update_participant_statistics()
        print("✓ Статистика участников обновлена")
    except Exception as e:
        print(f"✗ Ошибка обновления статистики участников: {e}")
    
    print("\n" + "=" * 60)
    print("=== СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА ===")
    print(f"Соревнований обработано: {processed_competitions}/{total_competitions}")
    print(f"Новых участников: {total_participants}")
    print(f"Новых выступлений: {total_performances}")
    print("=" * 60)
    
    return {
        'competitions_processed': processed_competitions,
        'competitions_total': total_competitions,
        'participants': total_participants,
        'performances': total_performances
    }



