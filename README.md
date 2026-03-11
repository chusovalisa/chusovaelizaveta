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
```
## Задание 2: Токенизация и лемматизация

- Из сохранённых HTML-страниц извлекаются токены: уникальные слова без дубликатов, союзов, предлогов, чисел и «мусорных» слов (содержащих одновременно буквы и цифры, обрывки разметки и т.д.)
- Токены группируются по леммам с помощью библиотеки `pymorphy2`
- Результаты сохраняются в два файла:
  - `output/text/tokens.txt` — список токенов, по одному на строку
  - `output/text/lemmas.txt` — список лемм с соответствующими токенами: `<лемма> <токен1> <токен2> ...`

### Запуск токенизации и лемматизации
```bash
python -m crawler tokens-pages --pages output/pages --out output/text --limit 102
```

## Задание 3: Инвертированный индекс и булев поиск

### 1. Построение инвертированного индекса
```bash
./.venv/bin/python -m crawler build-inverted --lemmas output/text/lemmas --out output/inverted_index.txt
```

Формат файла `output/inverted_index.txt`:
- `<термин><TAB><doc_id_1> <doc_id_2> ...`

### 2. Булев поиск (`AND`, `OR`, `NOT`, скобки)
```bash
./.venv/bin/python -m crawler boolean-search \
  --index output/inverted_index.txt \
  --query "(Клеопатра AND Цезарь) OR (Антоний AND Цицерон) OR Помпей" \
  --doc-index output/index.txt
```

Запрос передаётся строкой через `--query`, без хардкода в коде.
