from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import Hotel, Booking, HotspotUser, SyncLog, HotspotUserStatus, SyncStatus
from app.services.mssql_service import MSSQLService
from app.services.mikrotik_service import MikrotikService, generate_password
from app.services.radius_service import RADIUSService

logger = logging.getLogger(__name__)

# IDS Next RSVSTS status codes
IDS_STATUS_RESERVED   = 'R'
IDS_STATUS_CHECKED_IN = 'I'
IDS_STATUS_CHECKED_OUT = 'O'
IDS_STATUS_CANCELLED  = 'C'

ACTIVE_STATUSES = {IDS_STATUS_RESERVED, IDS_STATUS_CHECKED_IN}


def make_username(room_number: str, guest_name: str, booking_id: str, hotel_code: str = "") -> str:
    """
    Generate hotspot username: GUESTNAME@ROOMNO_HOTELCODE
    Example: SHEIKH@316_almanarDub
    """
    name_parts = str(guest_name).strip().split()
    if len(name_parts) >= 2:
        name = name_parts[-1].upper()   # use last name
    elif name_parts:
        name = name_parts[0].upper()
    else:
        name = "GUEST"
    name = ''.join(c for c in name if c.isalnum())[:20]
    room = ''.join(c for c in str(room_number).strip() if c.isalnum())
    code = ''.join(c for c in str(hotel_code).strip() if c.isalnum())
    if code:
        return f"{name}@{room}_{code}"
    return f"{name}@{room}"


class SyncEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_hotel(self, hotel: Hotel) -> Dict[str, Any]:
        log = SyncLog(hotel_id=hotel.id, status=SyncStatus.pending)
        self.db.add(log)
        await self.db.flush()

        created = 0
        deleted = 0
        found = 0

        try:
            # 1. Fetch confirmed/checked-in bookings from MSSQL (IDS Next)
            mssql = MSSQLService(hotel)
            bookings_data = await mssql.get_confirmed_bookings()
            found = len(bookings_data)

            # Track which booking IDs are still active (for cleanup later)
            active_ext_ids = set()

            # 2. Upsert bookings into local DB
            for bd in bookings_data:
                ext_id = str(bd.get("booking_id", "")).strip()
                if not ext_id:
                    continue

                active_ext_ids.add(ext_id)

                result = await self.db.execute(
                    select(Booking).where(
                        and_(
                            Booking.hotel_id == hotel.id,
                            Booking.external_booking_id == ext_id
                        )
                    )
                )
                booking = result.scalar_one_or_none()

                check_in_str = bd.get("check_in")
                check_out_str = bd.get("check_out")
                check_in = datetime.fromisoformat(check_in_str) if check_in_str else None
                check_out = datetime.fromisoformat(check_out_str) if check_out_str else None

                if not booking:
                    booking = Booking(
                        hotel_id=hotel.id,
                        external_booking_id=ext_id,
                        guest_name=bd.get("guest_name", ""),
                        guest_phone=bd.get("guest_phone", ""),
                        room_number=str(bd.get("room_number", "")),
                        check_in=check_in,
                        check_out=check_out,
                        status=bd.get("status", ""),
                        raw_data={k: str(v) for k, v in bd.items()}
                    )
                    self.db.add(booking)
                    await self.db.flush()
                else:
                    booking.check_out = check_out
                    booking.check_in = check_in
                    booking.status = bd.get("status", "")
                    booking.room_number = str(bd.get("room_number", ""))

                # 3. Create hotspot user if not exists
                if not booking.hotspot_user:
                    username = make_username(
                        booking.room_number,
                        booking.guest_name,
                        ext_id,
                        hotel_code=hotel.hotspot_code or ""
                    )
                    password = generate_password()

                    mikrotik = MikrotikService(hotel)
                    import asyncio
                    result_mt = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda u=username, p=password, eid=ext_id: mikrotik.create_hotspot_user(
                            username=u,
                            password=p,
                            comment=f"Booking {eid} | {booking.guest_name} | Room {booking.room_number}"
                        )
                    )

                    radius_ok = False
                    if hotel.use_radius and hotel.radius_host:
                        radius = RADIUSService(hotel)
                        r_result = radius.add_user(username, password)
                        radius_ok = r_result.get("success", False)

                    hu = HotspotUser(
                        hotel_id=hotel.id,
                        booking_id=booking.id,
                        username=username,
                        password=password,
                        status=HotspotUserStatus.active,
                        mikrotik_created=result_mt.get("success", False),
                        radius_created=radius_ok,
                        extra_info={
                            "mikrotik_result": result_mt,
                            "room": booking.room_number,
                            "guest": booking.guest_name,
                            "ids_status": bd.get("status", "")
                        }
                    )
                    self.db.add(hu)
                    if result_mt.get("success"):
                        created += 1

            # 4. Delete users for bookings no longer active (checkout / cancelled)
            now = datetime.now(timezone.utc)
            grace = timedelta(minutes=hotel.checkout_grace_minutes or 0)

            result = await self.db.execute(
                select(HotspotUser).where(
                    and_(
                        HotspotUser.hotel_id == hotel.id,
                        HotspotUser.status == HotspotUserStatus.active
                    )
                )
            )
            active_users = result.scalars().all()

            for hu in active_users:
                should_delete = False

                # Case A: booking's ext_id no longer in active list from PMS
                if hu.booking and hu.booking.external_booking_id not in active_ext_ids:
                    should_delete = True

                # Case B: checkout time has passed (with grace)
                if hu.booking and hu.booking.check_out:
                    co = hu.booking.check_out
                    if co.tzinfo is None:
                        co = co.replace(tzinfo=timezone.utc)
                    if now > (co + grace):
                        should_delete = True

                if should_delete:
                    import asyncio
                    mikrotik = MikrotikService(hotel)
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda u=hu.username: mikrotik.delete_hotspot_user(u)
                    )
                    hu.status = HotspotUserStatus.deleted
                    hu.deleted_at = now
                    deleted += 1

            await self.db.commit()

            log.status = SyncStatus.success
            log.message = f"IDS Next sync OK: {found} bookings, +{created} users, -{deleted} deleted"
            log.bookings_found = found
            log.users_created = created
            log.users_deleted = deleted
            await self.db.commit()

            return {
                "success": True,
                "bookings_found": found,
                "users_created": created,
                "users_deleted": deleted
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Sync error for hotel {hotel.name}: {e}", exc_info=True)
            try:
                log.status = SyncStatus.failed
                log.message = str(e)
                await self.db.commit()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    async def sync_all_hotels(self):
        result = await self.db.execute(
            select(Hotel).where(
                and_(Hotel.is_active == True, Hotel.auto_sync_enabled == True)
            )
        )
        hotels = result.scalars().all()
        results = {}
        for hotel in hotels:
            results[hotel.id] = await self.sync_hotel(hotel)
        return results
