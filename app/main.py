from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from .database import engine, Base
from .routes import orders, webhooks, sbp_routes
from .config import DEBUG, HOST, PORT
import traceback

# Создаём таблицы при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Лёгкая миграция: добавляем новые колонки, если таблица уже существовала
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_link VARCHAR(500)"
            ))
            conn.execute(text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_qr VARCHAR(500)"
            ))
            conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")
    print("✅ Database initialized")
    yield
    print("🛑 Shutdown")

app = FastAPI(
    title="Like at Home API",
    description="Backend для сайта кафе Like at Home (VKURSE Pay)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можешь ограничить на доменом потом
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Обработка всех ошибок с логированием"""
    error_detail = str(exc)
    traceback_str = traceback.format_exc()
    print(f"Error: {error_detail}\n{traceback_str}")
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail, "type": type(exc).__name__}
    )

# Подключаем routes
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(sbp_routes.router)

@app.get("/")
async def root():
    return {
        "service": "Like at Home Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)
