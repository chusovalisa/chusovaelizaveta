# Deployment Manual

Инструкция по запуску проекта 

## 1) Требования
- Python 3.10+ (желательно 3.11)
- pip
- доступ в интернет

## 2) Установка и подготовка окружения

### 2.1 Клонирование репозитория
```bash
git clone <ССЫЛКА_НА_РЕПОЗИТОРИЙ>
cd web-crawler
```

### 2.2 Виртуальное окружение

macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.3 Установка зависимостей
```bash
pip install -r requirements.txt
```

## 3) Запуск

### 3.1 Подготовка списка URL
Файл с ссылками: `data/urls.txt` 

### 3.2 Скачивание страниц и генерация index.txt
```bash
python -m crawler crawl --urls data/urls.txt --out output --limit 150 --delay 1.0 --respect-robots
```

Результат после выполнения:
- `output/pages/` — скачанные страницы (HTML)
- `output/index.txt` — соответствие `номер -> url`

### 3.3 Упаковка результата в архив
```bash
python zip_output.py --out ./output
```