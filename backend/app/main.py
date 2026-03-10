from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import init_db, AsyncSessionLocal
from app.core.scheduler import start_scheduler, stop_scheduler
from app.api import auth, hotels, operations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await seed_admin()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


async def seed_admin():
    from sqlalchemy import select
    from app.models.models import AppUser, UserRole
    from app.core.auth import get_password_hash

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AppUser).where(AppUser.email == settings.ADMIN_EMAIL)
        )
        if not result.scalar_one_or_none():
            admin = AppUser(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="Administrator",
                role=UserRole.admin,
                is_active=True
            )
            db.add(admin)
            await db.commit()


app = FastAPI(
    title="Hotel Hotspot Manager API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(hotels.router, prefix="/api")
app.include_router(operations.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
