from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from app.db.database import get_db
from app.models.models import Hotel, AppUser
from app.api.deps import get_current_user
from app.services.mssql_service import MSSQLService
from app.services.mikrotik_service import MikrotikService

router = APIRouter(prefix="/hotels", tags=["hotels"])


class HotelCreate(BaseModel):
    name: str
    address: Optional[str] = None
    # MSSQL
    mssql_host: Optional[str] = None
    mssql_port: int = 1433
    mssql_database: Optional[str] = None
    mssql_username: Optional[str] = None
    mssql_password: Optional[str] = None
    mssql_table_booking: str = "Bookings"
    mssql_col_booking_id: str = "BookingID"
    mssql_col_guest_name: str = "GuestName"
    mssql_col_guest_phone: str = "Phone"
    mssql_col_room_number: str = "RoomNumber"
    mssql_col_checkin: str = "CheckInDate"
    mssql_col_checkout: str = "CheckOutDate"
    mssql_col_status: str = "Status"
    mssql_col_status_confirmed: str = "Confirmed"
    # Mikrotik
    mikrotik_host: Optional[str] = None
    mikrotik_port: int = 8728
    mikrotik_username: str = "admin"
    mikrotik_password: Optional[str] = None
    mikrotik_hotspot_server: str = "hotspot1"
    mikrotik_hotspot_profile: str = "default"
    # RADIUS
    radius_host: Optional[str] = None
    radius_port: int = 1812
    radius_secret: Optional[str] = None
    use_radius: bool = False
    # Sync
    sync_interval_minutes: int = 5
    checkout_grace_minutes: int = 0
    auto_sync_enabled: bool = True


class HotelUpdate(HotelCreate):
    name: Optional[str] = None


@router.get("/")
async def list_hotels(
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    result = await db.execute(select(Hotel).order_by(Hotel.created_at.desc()))
    hotels = result.scalars().all()
    return [_hotel_dict(h) for h in hotels]


@router.post("/")
async def create_hotel(
    data: HotelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = Hotel(**data.model_dump())
    db.add(hotel)
    await db.commit()
    await db.refresh(hotel)
    return _hotel_dict(hotel)


@router.get("/{hotel_id}")
async def get_hotel(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    return _hotel_dict(hotel)


@router.put("/{hotel_id}")
async def update_hotel(
    hotel_id: int,
    data: HotelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(hotel, k, v)
    await db.commit()
    await db.refresh(hotel)
    return _hotel_dict(hotel)


@router.delete("/{hotel_id}")
async def delete_hotel(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    hotel.is_active = False
    await db.commit()
    return {"message": "Hotel deactivated"}


@router.post("/{hotel_id}/test-mssql")
async def test_mssql(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    svc = MSSQLService(hotel)
    result = await svc.test_connection()
    return result


@router.post("/{hotel_id}/test-mikrotik")
async def test_mikrotik(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    svc = MikrotikService(hotel)
    result = await asyncio.get_event_loop().run_in_executor(None, svc.test_connection)
    return result


@router.get("/{hotel_id}/mssql-tables")
async def get_mssql_tables(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    svc = MSSQLService(hotel)
    tables = await svc.get_tables()
    return {"tables": tables}


@router.get("/{hotel_id}/mssql-columns/{table_name}")
async def get_mssql_columns(
    hotel_id: int,
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    svc = MSSQLService(hotel)
    columns = await svc.get_columns(table_name)
    return {"columns": columns}


@router.get("/{hotel_id}/mikrotik-profiles")
async def get_mikrotik_profiles(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user)
):
    hotel = await _get_or_404(db, hotel_id)
    svc = MikrotikService(hotel)
    profiles = await asyncio.get_event_loop().run_in_executor(None, svc.get_profiles)
    return {"profiles": profiles}


async def _get_or_404(db: AsyncSession, hotel_id: int) -> Hotel:
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return hotel


def _hotel_dict(h: Hotel) -> dict:
    return {
        "id": h.id, "name": h.name, "address": h.address, "is_active": h.is_active,
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "mssql_host": h.mssql_host, "mssql_port": h.mssql_port,
        "mssql_database": h.mssql_database, "mssql_username": h.mssql_username,
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
        "mikrotik_username": h.mikrotik_username,
        "mikrotik_hotspot_server": h.mikrotik_hotspot_server,
        "mikrotik_hotspot_profile": h.mikrotik_hotspot_profile,
        "radius_host": h.radius_host, "radius_port": h.radius_port,
        "use_radius": h.use_radius,
        "sync_interval_minutes": h.sync_interval_minutes,
        "checkout_grace_minutes": h.checkout_grace_minutes,
        "auto_sync_enabled": h.auto_sync_enabled,
    }
