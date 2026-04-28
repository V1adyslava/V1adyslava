# GHL CRM Integration

Сервис-каркас на FastAPI, который собирает лиды из **Calendly**, **Typeform** и **форм с сайтов**, кладёт их в **GoHighLevel (GHL)** как Contacts + Opportunities, двигает по стадиям воронки и умеет выгружать данные в **Excel**.

## Архитектура

```
Calendly  ─┐
Typeform  ─┼─►  /webhooks/...  ─►  Stage automation  ─►  GHL API
Сайты     ─┘                                            (Contact + Opportunity)
                                                              │
                                          /export/excel  ◄────┘
                                                  │
                                                  ▼
                                            crm-export-*.xlsx
```

## Структура проекта

```
app/
├── config.py              # настройки через .env (pydantic-settings)
├── main.py                # FastAPI: подключает все вебхуки + endpoint экспорта
├── ghl/
│   ├── client.py          # GHL API v2 клиент (httpx)
│   └── models.py          # унифицированная модель Lead
├── webhooks/
│   ├── calendly.py        # POST /webhooks/calendly  (HMAC-SHA256 подпись)
│   ├── typeform.py        # POST /webhooks/typeform  (HMAC-SHA256 в base64)
│   └── site.py            # POST /webhooks/site      (X-Site-Token)
├── automations/
│   └── stages.py          # маппинг событие -> стадия GHL, ingest_lead()
└── export/
    └── excel.py           # выгрузка opportunities + сводка по стадиям
scripts/
└── export_to_excel.py     # CLI: python -m scripts.export_to_excel
```

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# заполните токены (см. ниже)

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Открыть `http://localhost:8000/docs` — Swagger со всеми endpoints.

## Настройка GHL

1. **Private Integration token** — Settings → Integrations → Private Integrations → создать с правами `contacts.write`, `opportunities.write`, `opportunities.readonly`, `locations.readonly`. Положить в `GHL_API_TOKEN`.
2. **Location ID** — URL вашего sub-account (`/v2/location/<ID>/...`). В `GHL_LOCATION_ID`.
3. **Pipeline** — создайте воронку, скопируйте её ID и ID каждой стадии в `GHL_PIPELINE_ID` и `GHL_STAGE_*`.

Узнать список pipelines/стадий можно через скрипт:
```python
import asyncio
from app.ghl.client import GHLClient
print(asyncio.run(GHLClient().list_pipelines()))
```

## Подключение источников

### Calendly
- Webhook Subscription через [API](https://developer.calendly.com/api-docs/webhook-subscriptions): URL `https://<your-host>/webhooks/calendly`, события `invitee.created`, `invitee.canceled`.
- Signing key из ответа API → `CALENDLY_WEBHOOK_SIGNING_KEY`.

### Typeform
- В форме → Connect → Webhooks → URL `https://<your-host>/webhooks/typeform`.
- Установите Secret → `TYPEFORM_WEBHOOK_SECRET`.

### Сайты (Tilda / WP / кастом)
- Form action / fetch на `https://<your-host>/webhooks/site`.
- Заголовок `X-Site-Token: <SITE_FORM_TOKEN>`.
- Поля: `email`, `name` (или `first_name`/`last_name`), `phone`, `source` (название лендинга), любые дополнительные — попадут в `customFields` GHL.

Пример из браузера:
```js
await fetch("https://your-host/webhooks/site", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Site-Token": "..." },
  body: JSON.stringify({ email: "x@y.com", name: "Иван", source: "landing_a" }),
});
```

## Автоматизация стадий

Маппинг событие → стадия задан в `app/automations/stages.py::EVENT_TO_STAGE`:

| Событие                       | Ключ стадии (env)        |
|-------------------------------|--------------------------|
| `calendly.invitee.created`    | `GHL_STAGE_BOOKED`       |
| `calendly.invitee.canceled`   | `GHL_STAGE_NO_SHOW`      |
| `typeform.form_response`      | `GHL_STAGE_QUALIFIED`    |
| `site.form_submitted`         | `GHL_STAGE_NEW`          |

Логика:
1. **Upsert контакта** в GHL (дедуп по email/phone).
2. **Поиск существующей opportunity** для этого контакта в нашей воронке.
3. Если есть — двигаем в новую стадию; если нет — создаём.

Меняйте таблицу `EVENT_TO_STAGE` под свою воронку — код вебхуков трогать не нужно.

## Выгрузка в Excel

**Разово из CLI:**
```bash
python -m scripts.export_to_excel --out exports/today.xlsx
```

**По HTTP (скачивание файла):**
```
POST /export/excel
```

В `.xlsx` два листа:
- **Opportunities** — все сделки с контактом, стадией, суммой, датами.
- **By Stage** — сводка количества сделок по стадиям.

**По расписанию (cron, каждый день в 8:00):**
```
0 8 * * *  cd /opt/ghl-crm && /opt/ghl-crm/.venv/bin/python -m scripts.export_to_excel
```

## Безопасность

- Все вебхуки валидируют подпись/токен. Если соответствующий env пуст — проверка отключается (только для dev).
- `.env` в `.gitignore`. Токены коммитить нельзя.
- Используйте HTTPS-прокси (Caddy, nginx, ngrok для dev) перед FastAPI — Calendly и Typeform не подпишут http://.

## Что осталось (прежний quiz-бот)

В корне ещё лежат файлы Telegram quiz-бота с предыдущей итерации (`bot.py`, `questions.py`, `chart.py`, `results.py`, `level_descriptions.py`, `assets/`). Они никак не связаны с CRM-сервисом и работают независимо. Если они больше не нужны — скажите, удалю отдельным коммитом.
