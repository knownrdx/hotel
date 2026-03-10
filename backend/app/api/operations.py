from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from app.db.database import get_db
from app.models.models import (
    Hotel, Booking, HotspotUser, SyncLog,
    HotspotUserStatus, AppUser
)
from app.api.deps import get_current_user
from app.services.sync_engine import SyncEngine
from app.services.mikrotik_service import MikrotikService, generate_password
from app.services.mssql_service import MSSQLService

router = APIRouter(tags=["operations"])


# ==================== BOOKINGS ====================

@router.get("/bookings")
async def list_bookings(
    hotel_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    q = select(Booking).order_by(desc(Booking.check_in))
    if hotel_id:
        q = q.where(Booking.hotel_id == hotel_id)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    bookings = result.scalars().all()
    return [_booking_dict(b) for b in bookings]


@router.get("/bookings/live")
async def live_bookings(
    hotel_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    """Get bookings from MSSQL directly (live data)"""
    hotels_q = select(Hotel).where(Hotel.is_active == True)
    if hotel_id:
        hotels_q = hotels_q.where(Hotel.id == hotel_id)
    result = await db.execute(hotels_q)
    hotels = result.scalars().all()

    all_bookings = []
    for hotel in hotels:
        if hotel.mssql_host:
            try:
                svc = MSSQLService(hotel)
                bookings = await svc.get_all_bookings(limit=50)
                for b in bookings:
                    b["hotel_name"] = hotel.name
                    b["hotel_id"] = hotel.id
                all_bookings.extend(bookings)
            except Exception as e:
                all_bookings.append({"hotel_name": hotel.name, "error": str(e)})
    return all_bookings


# ==================== HOTSPOT USERS ====================

@router.get("/hotspot-users")
async def list_hotspot_users(
    hotel_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    q = select(HotspotUser).order_by(desc(HotspotUser.created_at))
    if hotel_id:
        q = q.where(HotspotUser.hotel_id == hotel_id)
    if status:
        q = q.where(HotspotUser.status == status)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()
    return [_user_dict(u) for u in users]


class ManualUserCreate(BaseModel):
    hotel_id: int
    username: str
    password: Optional[str] = None
    profile: Optional[str] = None
    comment: Optional[str] = None


@router.post("/hotspot-users")
async def create_hotspot_user_manual(
    data: ManualUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    result = await db.execute(select(Hotel).where(Hotel.id == data.hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    password = data.password or generate_password()
    mt = MikrotikService(hotel)
    mt_result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: mt.create_hotspot_user(
            username=data.username,
            password=password,
            profile=data.profile,
            comment=data.comment
        )
    )

    hu = HotspotUser(
        hotel_id=hotel.id,
        username=data.username,
        password=password,
        status=HotspotUserStatus.active,
        mikrotik_created=mt_result.get("success", False),
        extra_info={"manual": True, "mikrotik_result": mt_result}
    )
    db.add(hu)
    await db.commit()
    await db.refresh(hu)
    return {**_user_dict(hu), "password": password, "mikrotik_result": mt_result}


@router.delete("/hotspot-users/{user_id}")
async def delete_hotspot_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    result = await db.execute(
        select(HotspotUser).where(HotspotUser.id == user_id)
    )
    hu = result.scalar_one_or_none()
    if not hu:
        raise HTTPException(status_code=404, detail="User not found")

    result2 = await db.execute(select(Hotel).where(Hotel.id == hu.hotel_id))
    hotel = result2.scalar_one_or_none()

    mt_result = {}
    if hotel:
        mt = MikrotikService(hotel)
        mt_result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: mt.delete_hotspot_user(hu.username)
        )

    from datetime import datetime, timezone
    hu.status = HotspotUserStatus.deleted
    hu.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "User deleted", "mikrotik_result": mt_result}


@router.get("/hotspot-users/mikrotik/{hotel_id}")
async def get_mikrotik_live_users(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    mt = MikrotikService(hotel)
    users = await asyncio.get_event_loop().run_in_executor(None, mt.list_hotspot_users)
    sessions = await asyncio.get_event_loop().run_in_executor(None, mt.get_active_sessions)
    return {"users": users, "active_sessions": sessions}


# ==================== SYNC ====================

@router.post("/sync/{hotel_id}")
async def trigger_sync(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    engine = SyncEngine(db)
    result = await engine.sync_hotel(hotel)
    return result


@router.post("/sync/all")
async def trigger_sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    engine = SyncEngine(db)
    results = await engine.sync_all_hotels()
    return results


# ==================== LOGS ====================

@router.get("/logs")
async def get_logs(
    hotel_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    q = select(SyncLog).order_by(desc(SyncLog.created_at))
    if hotel_id:
        q = q.where(SyncLog.hotel_id == hotel_id)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [_log_dict(l) for l in logs]


# ==================== DASHBOARD STATS ====================

@router.get("/dashboard/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    total_hotels = await db.scalar(select(func.count(Hotel.id)).where(Hotel.is_active == True))
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    active_users = await db.scalar(
        select(func.count(HotspotUser.id)).where(HotspotUser.status == HotspotUserStatus.active)
    )
    total_syncs = await db.scalar(select(func.count(SyncLog.id)))

    # Recent logs
    recent_logs_q = select(SyncLog).order_by(desc(SyncLog.created_at)).limit(5)
    recent_result = await db.execute(recent_logs_q)
    recent_logs = [_log_dict(l) for l in recent_result.scalars().all()]

    return {
        "total_hotels": total_hotels or 0,
        "total_bookings": total_bookings or 0,
        "active_hotspot_users": active_users or 0,
        "total_syncs": total_syncs or 0,
        "recent_logs": recent_logs,
    }


def _booking_dict(b: Booking) -> dict:
    return {
        "id": b.id, "hotel_id": b.hotel_id,
        "external_booking_id": b.external_booking_id,
        "guest_name": b.guest_name, "guest_phone": b.guest_phone,
        "room_number": b.room_number,
        "check_in": b.check_in.isoformat() if b.check_in else None,
        "check_out": b.check_out.isoformat() if b.check_out else None,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _user_dict(u: HotspotUser) -> dict:
    return {
        "id": u.id, "hotel_id": u.hotel_id, "booking_id": u.booking_id,
        "username": u.username,
        "status": u.status,
        "mikrotik_created": u.mikrotik_created,
        "radius_created": u.radius_created,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
        "extra_info": u.extra_info,
    }


def _log_dict(l: SyncLog) -> dict:
    return {
        "id": l.id, "hotel_id": l.hotel_id,
        "status": l.status, "message": l.message,
        "bookings_found": l.bookings_found,
        "users_created": l.users_created,
        "users_deleted": l.users_deleted,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
