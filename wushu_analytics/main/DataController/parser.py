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
    
    # Ищем все блоки с категориями
    for category_block in soup.find_all("div", class_="d-flex"):
        category_name_tag = category_block.find("h3")
        if not category_name_tag:
            continue
        
        raw_category = category_name_tag.text.strip().replace("\n", " ")
        time_range = category_block.find("p").text.strip() if category_block.find("p") else ""
        
        # Определяем статус категории
        status = "future"  # по умолчанию "скоро"
        # TODO: добавить логику определения текущих категорий
        
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
        
        categories.append({
            "name": raw_category,
            "time_range": time_range,
            "status": status,
            "participants": participants
        })
    
    return {
        "name": competition_name,
        "regulation": regulation,
        "categories": categories
    }


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
    competitions = parse_competitions()
    write_competitions(competitions)
    print("Competitions written")