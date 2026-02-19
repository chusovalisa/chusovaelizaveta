# HW Web Crawler Чусова Елизавета 11-209

## Требования
- Python 3.10+
- Скачивает >=100 страниц из заранее подготовленного списка `data/urls.txt`
- Сохраняет каждую страницу в отдельный файл 
- Делает `output/index.txt`: `номер_файла <TAB> ссылка`
- Обрабатывает ошибки/404/не-html/пустые страницы

## Установка
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows PowerShell

pip install -r requirements.txt
