from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.models import Hotel, Booking, HotspotUser, SyncLog, HotspotUserStatus, AppUser
from app.api.deps import get_current_user
from app.services.sync_engine import sync_engine
from app.services.mikrotik_service import MikrotikService, make_username
from app.services.mssql_service import MSSQLService

router = APIRouter(tags=["operations"])


def hotel_dict(h: Hotel) -> dict:
    return {"id": h.id, "name": h.name, "mssql_server": h.mssql_server,
            "mssql_database": h.mssql_database, "mikrotik_host": h.mikrotik_host}


def booking_dict(b: Booking) -> dict:
    return {
        "id": b.id, "hotel_id": b.hotel_id, "booking_id": b.booking_id,
        "guest_name": b.guest_name, "guest_phone": b.guest_phone,
        "room_number": b.room_number, "status": b.status,
        "checkin_date": b.checkin_date.isoformat() if b.checkin_date else None,
        "checkout_date": b.checkout_date.isoformat() if b.checkout_date else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def user_dict(u: HotspotUser) -> dict:
    return {
        "id": u.id, "hotel_id": u.hotel_id, "booking_id": u.booking_id,
        "username": u.username, "password": u.password,
        "room_number": u.room_number, "guest_name": u.guest_name,
        "status": u.status.value if u.status else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
    }


def log_dict(l: SyncLog) -> dict:
    return {
        "id": l.id, "hotel_id": l.hotel_id, "status": l.status,
        "message": l.message, "bookings_synced": l.bookings_synced,
        "users_created": l.users_created, "users_deleted": l.users_deleted,
        "errors": l.errors,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


def hotel_data(h: Hotel) -> dict:
    return {
        "id": h.id, "name": h.name, "hotspot_code": h.hotspot_code,
        "mssql_server": h.mssql_server, "mssql_port": h.mssql_port,
        "mssql_database": h.mssql_database, "mssql_username": h.mssql_username,
        "mssql_password": h.mssql_password,
        "mssql_table_booking": h.mssql_table_booking,
        "mssql_col_booking_id": h.mssql_col_booking_id,
        "mssql_col_guest_name": h.mssql_col_guest_name,
        "mssql_col_guest_phone": h.mssql_col_guest_phone,
        "mssql_col_room_number": h.mssql_col_room_number,
        "mssql_col_checkin": h.mssql_col_checkin,
        "mssql_col_checkout": h.mssql_col_checkout,
        "mssql_col_status": h.mssql_col_status,
        "mssql_col_status_confirmed": h.mssql_col_status_confirmed,
        "mikrotik_host": h.mikrotik_host, "mikrotik_port": h.mikrotik_port,
        "mikrotik_username": h.mikrotik_username, "mikrotik_password": h.mikrotik_password,
        "mikrotik_hotspot_server": h.mikrotik_hotspot_server,
        "hotspot_password_length": h.hotspot_password_length,
        "checkout_grace_minutes": h.checkout_grace_minutes,
    }


# ==================== BOOKINGS ====================

@router.get("/bookings")
async def list_bookings(
    hotel_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    q = select(Booking).order_by(desc(Booking.created_at)).limit(limit)
    if hotel_id:
        q = q.where(Booking.hotel_id == hotel_id)
    result = await db.execute(q)
    return [booking_dict(b) for b in result.scalars().all()]


@router.get("/bookings/live")
async def live_bookings(
    hotel_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    q = select(Hotel).where(Hotel.is_active == True)
    if hotel_id:
        q = q.where(Hotel.id == hotel_id)
    result = await db.execute(q)
    hotels = result.scalars().all()

    all_bookings = []
    for h in hotels:
        if not h.mssql_server:
            continue
        try:
            svc = MSSQLService(hotel_data(h))
            bookings = await svc.get_active_bookings()
            for b in bookings:
                b["hotel_name"] = h.name
                b["hotel_id"] = h.id
                if b.get("checkin_date"):
                    b["checkin_date"] = b["checkin_date"].isoformat()
                if b.get("checkout_date"):
                    b["checkout_date"] = b["checkout_date"].isoformat()
            all_bookings.extend(bookings)
        except Exception as e:
            all_bookings.append({"hotel_name": h.name, "error": str(e)})
    return all_bookings


# ==================== HOTSPOT USERS ====================

@router.get("/hotspot-users")
async def list_hotspot_users(
    hotel_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    q = select(HotspotUser).order_by(desc(HotspotUser.created_at)).limit(limit)
    if hotel_id:
        q = q.where(HotspotUser.hotel_id == hotel_id)
    if status:
        q = q.where(HotspotUser.status == status)
    result = await db.execute(q)
    return [user_dict(u) for u in result.scalars().all()]


class ManualUserCreate(BaseModel):
    hotel_id: int
    username: str
    password: Optional[str] = None


@router.post("/hotspot-users")
async def create_hotspot_user_manual(
    data: ManualUserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    result = await db.execute(select(Hotel).where(Hotel.id == data.hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404, "Hotel not found")

    # password = username if not provided
    password = data.password or data.username
    svc = MikrotikService(hotel_data(hotel))
    try:
        await svc.create_user(
            room_number="",
            guest_name=data.username,
            booking_id="manual",
            hotel_code=""
        )
    except Exception as e:
        pass  # Save to DB even if mikrotik fails

    hu = HotspotUser(
        hotel_id=hotel.id, username=data.username, password=password,
        status=HotspotUserStatus.active,
    )
    db.add(hu)
    await db.commit()
    await db.refresh(hu)
    return user_dict(hu)


@router.delete("/hotspot-users/{user_id}")
async def delete_hotspot_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    result = await db.execute(select(HotspotUser).where(HotspotUser.id == user_id))
    hu = result.scalar_one_or_none()
    if not hu:
        raise HTTPException(404, "User not found")

    result2 = await db.execute(select(Hotel).where(Hotel.id == hu.hotel_id))
    hotel = result2.scalar_one_or_none()
    if hotel:
        svc = MikrotikService(hotel_data(hotel))
        try:
            await svc.delete_user(hu.username)
        except Exception:
            pass

    hu.status = HotspotUserStatus.deleted
    hu.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


# ==================== SYNC ====================

@router.post("/sync/{hotel_id}")
async def trigger_sync(hotel_id: int, _=Depends(get_current_user)):
    return await sync_engine.sync_hotel_by_id(hotel_id)


@router.post("/sync/all")
async def trigger_sync_all(_=Depends(get_current_user)):
    return await sync_engine.sync_all_hotels()


# ==================== LOGS ====================

@router.get("/logs")
async def get_logs(
    hotel_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    q = select(SyncLog).order_by(desc(SyncLog.created_at)).limit(limit)
    if hotel_id:
        q = q.where(SyncLog.hotel_id == hotel_id)
    result = await db.execute(q)
    return [log_dict(l) for l in result.scalars().all()]


# ==================== DASHBOARD ====================

@router.get("/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_hotels = await db.scalar(select(func.count(Hotel.id)).where(Hotel.is_active == True))
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    active_users = await db.scalar(
        select(func.count(HotspotUser.id)).where(HotspotUser.status == HotspotUserStatus.active)
    )
    total_syncs = await db.scalar(select(func.count(SyncLog.id)))

    recent_q = select(SyncLog).order_by(desc(SyncLog.created_at)).limit(5)
    recent_result = await db.execute(recent_q)
    recent_logs = [log_dict(l) for l in recent_result.scalars().all()]

    return {
        "total_hotels": total_hotels or 0,
        "total_bookings": total_bookings or 0,
        "active_hotspot_users": active_users or 0,
        "total_syncs": total_syncs or 0,
        "recent_logs": recent_logs,
    }
