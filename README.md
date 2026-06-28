# Like at Home Backend

Backend для сайта кафе Like at Home. Обрабатывает заказы и интегрируется с VKURSE Pay.

## API Endpoints

### Заказы
- `POST /api/orders` - Создать новый заказ
- `GET /api/orders/{order_id}` - Получить статус заказа
- `GET /api/orders` - Список заказов (для админки)

### Webhook'и
- `POST /webhook/payment` - Уведомление об оплате от бота
- `GET /webhook/health` - Проверка здоровья

## Локальный запуск

```bash
# 1. Копируем .env
cp .env.example .env

# 2. Редактируем .env и добавляем BOT_TOKEN и BOT_CHAT_ID

# 3. Запускаем через Docker Compose
docker-compose up

# 4. API доступен на http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Деплой на Digital Ocean

```bash
# 1. SSH на DO сервер
ssh root@167.172.77.17

# 2. Клонируем репо
git clone https://github.com/[ваш репо] like-at-home-backend
cd like-at-home-backend

# 3. Создаём .env с реальными данными
nano .env

# 4. Запускаем через Docker
docker build -t like-at-home-backend .
docker run -d \
  --name like-at-home-api \
  --env-file .env \
  -p 8001:8000 \
  --restart always \
  like-at-home-backend

# 5. Настраиваем Nginx
```

### Nginx конфиг для DO (добавить в `/etc/nginx/sites-available/like-at-home`)

```nginx
server {
    listen 80;
    server_name 167.172.77.17;

    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhook/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Перезагружаем Nginx
systemctl reload nginx
```

## Деплой на Render

### 1. Создать PostgreSQL на Render

1. Перейти на https://render.com
2. Нажать "Create" → "PostgreSQL"
3. Выбрать:
   - Region: Singapore (близко к DO)
   - Name: `like-at-home-db`
4. Скопировать `External Database URL` (понадобится)

### 2. Создать Backend Service на Render

1. "Create" → "Web Service"
2. Выбрать GitHub репо с backend'ом
3. Настройки:
   - **Name**: `like-at-home-api`
   - **Region**: Singapore
   - **Branch**: main
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Добавить Environment Variables:
   ```
   DATABASE_URL=postgresql://[из шага 1]
   BOT_TOKEN=[твой бот токен]
   BOT_CHAT_ID=[твой ID]
   ```
5. Нажать "Deploy"

Render автоматически:
- Создаст HTTPS URL
- Будет автоматически редеплоить при push в GitHub
- Масштабировать при нагрузке

## Frontend Integration

В `web/index.html` и `miniapp/index.html` обновить:

```javascript
// На веб-сайте
const API_URL = "https://[do-ip-или-render-url]";

// При клике "Оплатить рублями"
const response = await fetch(`${API_URL}/api/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        items: cart items,
        total_baht: sum,
        total_rub: rub,
        order_type: "dinein" | "delivery",
        context: {table: "5"} | {name, phone, address, comment}
    })
});

const data = await response.json();
const orderId = data.id;

// Polling статуса
const pollStatus = setInterval(async () => {
    const status = await fetch(`${API_URL}/api/orders/${orderId}`).then(r => r.json());
    if (status.status === "paid") {
        clearInterval(pollStatus);
        // Показать спасибо
    }
}, 2000);
```

## Монитор Логи

### DO
```bash
docker logs -f like-at-home-api
```

### Render
В панели управления → Logs

## БД Миграции

```bash
# Локально создаются автоматически при первом запуске
# Для ручного создания таблиц:

docker-compose exec backend python -c "
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
"
```

## Troubleshooting

**БД не подключается**
- Проверь `DATABASE_URL` в `.env`
- Проверь что БД доступна из сервера (firewall)

**Бот не отправляет сообщения**
- Проверь `BOT_TOKEN` и `BOT_CHAT_ID`
- Убедись что бот добавлен в группу/чат

**Webhook не срабатывает**
- Проверь логи бота
- Убедись что URL доступен: `curl https://[url]/webhook/health`

---

**Questions?** Спросить Дамиана 😄
