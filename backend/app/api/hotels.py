from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.models.models import Hotel, AppUser
from app.api.deps import get_current_user
from app.services.mssql_service import MSSQLService
from app.services.mssql_detector import MSSQLDetector
from app.services.mikrotik_service import MikrotikService
from app.services.sync_engine import sync_engine

router = APIRouter(prefix="/hotels", tags=["hotels"])


class HotelCreate(BaseModel):
    name: str
    hotspot_code: str = ""
    mssql_server: str = ""
    mssql_port: int = 1433
    mssql_database: str = ""
    mssql_username: str = ""
    mssql_password: str = ""
    mssql_table_booking: str = "PMS.RRVDATBL"
    mssql_col_booking_id: str = "RESNUB"
    mssql_col_guest_name: str = "GSTNAM"
    mssql_col_guest_phone: str = "MBLNUB"
    mssql_col_room_number: str = "ROOMNO"
    mssql_col_checkin: str = "ARRIVL"
    mssql_col_checkout: str = "DEPDAT"
    mssql_col_status: str = "RSVSTS"
    mssql_col_status_confirmed: str = "R,I"
    mikrotik_host: str = ""
    mikrotik_port: int = 8728
    mikrotik_username: str = ""
    mikrotik_password: str = ""
    mikrotik_hotspot_server: str = "hotspot1"
    hotspot_password_length: int = 8
    checkout_grace_minutes: int = 60
    sync_enabled: bool = True
    sync_interval_minutes: int = 5


class HotelUpdate(HotelCreate):
    pass


def hotel_to_dict(h: Hotel) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "hotspot_code": h.hotspot_code,
        "mssql_server": h.mssql_server,
        "mssql_port": h.mssql_port,
        "mssql_database": h.mssql_database,
        "mssql_username": h.mssql_username,
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
        "mikrotik_host": h.mikrotik_host,
        "mikrotik_port": h.mikrotik_port,
        "mikrotik_username": h.mikrotik_username,
        "mikrotik_password": h.mikrotik_password,
        "mikrotik_hotspot_server": h.mikrotik_hotspot_server,
        "hotspot_password_length": h.hotspot_password_length,
        "checkout_grace_minutes": h.checkout_grace_minutes,
        "sync_enabled": h.sync_enabled,
        "sync_interval_minutes": h.sync_interval_minutes,
        "is_active": h.is_active,
    }


def hotel_data_dict(h: Hotel) -> dict:
    return {
        "id": h.id, "name": h.name, "hotspot_code": h.hotspot_code,
        "mssql_server": h.mssql_server, "mssql_port": h.mssql_port,
        "mssql_database": h.mssql_database, "mssql_username": h.mssql_username,
        "mssql_password": h.mssql_password, "mssql_table_booking": h.mssql_table_booking,
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


@router.get("/")
async def list_hotels(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.is_active == True))
    return [hotel_to_dict(h) for h in result.scalars().all()]


@router.post("/")
async def create_hotel(data: HotelCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    hotel = Hotel(**data.model_dump())
    db.add(hotel)
    await db.commit()
    await db.refresh(hotel)
    return hotel_to_dict(hotel)


@router.put("/{hotel_id}")
async def update_hotel(hotel_id: int, data: HotelUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    for k, v in data.model_dump().items():
        setattr(hotel, k, v)
    await db.commit()
    return hotel_to_dict(hotel)


@router.delete("/{hotel_id}")
async def delete_hotel(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    hotel.is_active = False
    await db.commit()
    return {"success": True}


@router.post("/{hotel_id}/test-mssql")
async def test_mssql(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404)
    svc = MSSQLService(hotel_data_dict(hotel))
    return await svc.test_connection()


@router.post("/{hotel_id}/auto-detect")
async def auto_detect_schema(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """
    Smart auto-detection: connects to MSSQL, scans tables and columns,
    returns suggested configuration for reservation table + columns
    """
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404)

    hd = hotel_data_dict(hotel)
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={hd['mssql_server']},{hd['mssql_port'] or 1433};"
        f"DATABASE={hd['mssql_database']};"
        f"UID={hd['mssql_username']};"
        f"PWD={hd['mssql_password']};"
        f"TrustServerCertificate=yes;"
        f"Encrypt=yes;"
    )
    detector = MSSQLDetector(conn_str)
    detection = await detector.detect()

    # If successful, auto-apply to hotel
    if detection.get("success") and detection.get("table"):
        cols = detection.get("columns", {})
        hotel.mssql_table_booking = detection["table"]
        if cols.get("booking_id"):    hotel.mssql_col_booking_id = cols["booking_id"]
        if cols.get("guest_name"):    hotel.mssql_col_guest_name = cols["guest_name"]
        if cols.get("guest_phone"):   hotel.mssql_col_guest_phone = cols["guest_phone"]
        if cols.get("room_number"):   hotel.mssql_col_room_number = cols["room_number"]
        if cols.get("checkin"):       hotel.mssql_col_checkin = cols["checkin"]
        if cols.get("checkout"):      hotel.mssql_col_checkout = cols["checkout"]
        if cols.get("status"):        hotel.mssql_col_status = cols["status"]
        if detection.get("active_statuses"):
            hotel.mssql_col_status_confirmed = detection["active_statuses"]
        await db.commit()

    return detection


@router.get("/{hotel_id}/mssql-tables")
async def list_tables(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404)
    svc = MSSQLService(hotel_data_dict(hotel))
    return {"tables": await svc.get_tables()}


@router.post("/{hotel_id}/test-mikrotik")
async def test_mikrotik(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404)
    svc = MikrotikService(hotel_data_dict(hotel))
    return await svc.test_connection()


@router.post("/{hotel_id}/sync")
async def manual_sync(hotel_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404)
    return await sync_engine.sync_hotel_by_id(hotel_id)
