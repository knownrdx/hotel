from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging
import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import Hotel, Booking, HotspotUser, SyncLog, HotspotUserStatus, SyncStatus
from app.services.mssql_service import MSSQLService
from app.services.mikrotik_service import MikrotikService, generate_password
from app.services.radius_service import RADIUSService

logger = logging.getLogger(__name__)


def make_username(room_number: str, guest_name: str, booking_id: str) -> str:
    """Generate a clean hotspot username"""
    room = str(room_number).strip().replace(" ", "").lower()
    name_parts = str(guest_name).strip().split()
    name = name_parts[0].lower() if name_parts else "guest"
    # Remove special chars
    name = ''.join(c for c in name if c.isalnum())
    return f"room{room}_{name}"


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
            # 1. Fetch confirmed bookings from MSSQL
            mssql = MSSQLService(hotel)
            bookings_data = await mssql.get_confirmed_bookings()
            found = len(bookings_data)

            # 2. Upsert bookings into local DB
            for bd in bookings_data:
                ext_id = str(bd.get("booking_id", ""))
                result = await self.db.execute(
                    select(Booking).where(
                        and_(
                            Booking.hotel_id == hotel.id,
                            Booking.external_booking_id == ext_id
                        )
                    )
                )
                booking = result.scalar_one_or_none()

                check_in = bd.get("check_in")
                check_out = bd.get("check_out")
                if isinstance(check_in, str):
                    check_in = datetime.fromisoformat(check_in)
                if isinstance(check_out, str):
                    check_out = datetime.fromisoformat(check_out)

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
                        raw_data=bd
                    )
                    self.db.add(booking)
                    await self.db.flush()
                else:
                    booking.check_out = check_out
                    booking.check_in = check_in
                    booking.status = bd.get("status", "")

                # 3. Create hotspot user if not exists
                if not booking.hotspot_user:
                    username = make_username(
                        booking.room_number,
                        booking.guest_name,
                        ext_id
                    )
                    password = generate_password()

                    mikrotik = MikrotikService(hotel)
                    result_mt = mikrotik.create_hotspot_user(
                        username=username,
                        password=password,
                        comment=f"Booking {ext_id} - {booking.guest_name} - Room {booking.room_number}"
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
                            "guest": booking.guest_name
                        }
                    )
                    self.db.add(hu)
                    if result_mt.get("success"):
                        created += 1

            # 4. Delete/disable users for checked-out guests
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
                if hu.booking and hu.booking.check_out:
                    checkout_with_grace = hu.booking.check_out.replace(tzinfo=timezone.utc) + grace
                    if now > checkout_with_grace:
                        mikrotik = MikrotikService(hotel)
                        mikrotik.delete_hotspot_user(hu.username)
                        hu.status = HotspotUserStatus.deleted
                        hu.deleted_at = now
                        deleted += 1

            await self.db.commit()

            log.status = SyncStatus.success
            log.message = f"Sync completed: {found} bookings, {created} users created, {deleted} users deleted"
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
            logger.error(f"Sync error for hotel {hotel.name}: {e}")
            log.status = SyncStatus.failed
            log.message = str(e)
            try:
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
