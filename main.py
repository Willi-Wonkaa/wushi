import os
import time
import warnings
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib3

# Отключаем предупреждения SSL
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Константы
BASE_URL = "https://wushujudges.ru/site/competition/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 3
SLEEP_TIME = 0.5


def clean_scores(df):
    """Удаляет строки с нулевыми или пустыми баллами и возвращает очищенный DataFrame."""
    df["score"] = pd.to_numeric(df["score"], errors="coerce")  # Преобразуем в число, заменяя ошибки на NaN
    df_cleaned = df[df["score"] > 1]  # Оставляем только строки с баллами больше 1
    return df_cleaned


def extract_age_category(df):
    """Извлекает возрастные категории из колонки 'category name'"""
    categories = [
        'девушки', 'мужчины', '7', '18', '11', 'cadets', 'female', 'юноши', '12-14л', 'ветераны', '9',
        'juniors', 'юниорки15-17', 'старше', 'мальчики', '56', '2010', 'юноши/девушки', 'женщины',
        'юниоры', '-8', 'adults', 'дувушки', 'лет', 'взрослые', '2009', '9-11', '-11', '15-17',
        '7-8', 'девушки-юноши', 'юниорки', '41-55', '7-8лет', 'юниоры15-17', '1990', '12-14',
        'male'
    ]
    categories_set = {c.lower() for c in categories}

    def process_text(text):
        if pd.isna(text):
            return text, None
        words = re.findall(r'\b[\w-]+\b', text.lower())
        age_terms = [w for w in words if w in categories_set]
        remaining = ' '.join([w for w in re.findall(r'\b[\w-]+\b', text) if w.lower() not in categories_set])
        return remaining, ' '.join(age_terms) if age_terms else None

    processed = df['category name'].apply(process_text)
    df['category name'] = processed.apply(lambda x: x[0])
    df['age'] = processed.apply(lambda x: x[1])
    return df


def fetch_page(url):
    """Загружает страницу с повторными попытками"""
    for attempt in range(MAX_RETRIES):
        try:
            # Добавляем verify=False для отключения проверки SSL
            response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if response.status_code == 200:
                return response.text
            print(f"⚠ Ошибка {response.status_code}: {url}")
        except requests.exceptions.RequestException as e:
            print(f"⚠ Ошибка подключения: {e}")
        time.sleep(5)
    print(f"❌ Не удалось загрузить: {url}")
    return None


def split_category_name(category_name):
    """Разделяет название категории на ковер и название"""
    pattern = r"(Ковер \d+)\s*[:|-]\s*(.*)"
    match = re.match(pattern, category_name)
    if match:
        return match.group(1), match.group(2).strip()
    return "Unknown mat", category_name.strip()


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


start_id = 1
end_id = 3
# df = parse_competition_results(start_id, end_id)
# if not df.empty:
#     df.to_csv("data.csv", sep='|', index=False, encoding='utf-8')
#     print(f"✅ Данные успешно сохранены в data.csv")
#     print(f"📊 Всего записей: {len(df)}")
#     print(df.head(10))
# else:
#     print("❌ Не удалось получить данные")

