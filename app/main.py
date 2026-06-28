from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import engine, Base
from .routes import orders, webhooks
from .config import DEBUG, HOST, PORT

# Создаём таблицы при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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

# Подключаем routes
app.include_router(orders.router)
app.include_router(webhooks.router)

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
