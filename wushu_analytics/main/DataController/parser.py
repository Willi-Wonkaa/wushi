import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import ssl
from dataWriter import write_competitions

# Константы
BASE_URL = "https://wushujudges.ru"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 3
SLEEP_TIME = 0.5


# Отключаем проверку SSL сертификатов (только для разработки)
ssl._create_default_https_context = ssl._create_unverified_context


def fetch_page(url):
    print('fetching page: ', url)    
    write_competitions(parse_competitions())
    print('Writing done')
    return response.text

# Убираем выполнение кода при импорте
# response = requests.get(BASE_URL)
# print(response.text)


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
        start_date = cells[2].text.strip()
        end_date = cells[3].text.strip()
        
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


def parse_competition_results(start_id, end_id):
    """Парсит результаты соревнований в заданном диапазоне ID"""
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