from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.database import init_db, AsyncSessionLocal
from app.core.scheduler import start_scheduler, stop_scheduler
from app.api import auth, hotels, operations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_admin()
    start_scheduler()
    yield
    stop_scheduler()


async def seed_admin():
    from sqlalchemy import select
    from app.models.models import AppUser, UserRole
    from app.core.auth import get_password_hash

    # Try env vars first, fallback to defaults
    admin_email = settings.ADMIN_EMAIL or "admin@hotel.com"
    admin_password = settings.ADMIN_PASSWORD or "admin123"

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(AppUser).where(AppUser.email == admin_email)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                admin = AppUser(
                    email=admin_email,
                    hashed_password=get_password_hash(admin_password),
                    full_name="Administrator",
                    role=UserRole.admin,
                    is_active=True
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Admin user created: {admin_email}")
            else:
                # Always update password on startup so env change takes effect
                existing.hashed_password = get_password_hash(admin_password)
                existing.is_active = True
                await db.commit()
                logger.info(f"Admin user updated: {admin_email}")

        except Exception as e:
            logger.error(f"seed_admin error: {e}")
            await db.rollback()


app = FastAPI(
    title="Hotel Hotspot Manager API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Coolify handles SSL/domain, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(hotels.router, prefix="/api")
app.include_router(operations.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "admin_email": settings.ADMIN_EMAIL or "admin@hotel.com"
    }
