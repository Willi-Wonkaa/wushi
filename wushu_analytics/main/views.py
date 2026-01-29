from django.shortcuts import render
from django.http import JsonResponse
import sys
import os

# Добавляем путь к папке DataController
sys.path.append(os.path.join(os.path.dirname(__file__), 'templates', 'DataController'))

try:
    from parser import fetch_page
except ImportError:
    def fetch_page(url):
        return f"Parser not available. URL: {url}"

def dashboard(request):
    return render(request, "dashboard.html")

def analytics(request):
    return render(request, "analytics.html")

def competitions(request):
    return render(request, "competitions.html")

def regions(request):
    return render(request, "regions.html")

def athletes(request):
    return render(request, "athletes.html")

def button_():
    return fetch_page("https://wushujudges.ru")

def run_parser(request):
    """Запуск парсера данных"""
    if request.method == 'POST':
        try:
            result = button_()
            return JsonResponse({
                'success': True,
                'message': 'Данные успешно обновлены',
                'data_length': len(result) if result else 0
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
