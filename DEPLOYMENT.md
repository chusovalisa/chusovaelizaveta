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

### 3.4 Токенизация и лемматизация страниц
```bash
python -m crawler tokens-pages --pages output/pages --out output/text --limit 102
```

Результат после выполнения:
- `output/text/tokens.txt` — список уникальных токенов (по одному на строку), очищенных от союзов, предлогов, чисел и мусора
- `output/text/lemmas.txt` — список лемм с токенами в формате: `<лемма> <токен1> <токен2> ...`

### 3.5 Построение инвертированного индекса 
```bash
python -m crawler build-inverted --lemmas output/text/lemmas --out output/inverted_index.txt
```

Результат после выполнения:
- `output/inverted_index.txt` — инвертированный индекс в формате `<термин><TAB><doc_id_1> <doc_id_2> ...`

### 3.6 Булев поиск по индексу 
```bash
python -m crawler boolean-search \
  --index output/inverted_index.txt \
  --query "рим AND империя" \
  --doc-index output/index.txt
```

Поддерживаются операторы:
- `AND`
- `OR`
- `NOT`
- скобки для сложных запросов
