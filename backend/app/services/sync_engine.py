import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.models import Hotel, Booking, HotspotUser, SyncLog, HotspotUserStatus
from app.services.mssql_service import MSSQLService
from app.services.mikrotik_service import MikrotikService

logger = logging.getLogger(__name__)


class SyncEngine:

    async def sync_all_hotels(self):
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Hotel).where(Hotel.is_active == True, Hotel.sync_enabled == True)
            )
            hotels = result.scalars().all()

        results = {}
        for hotel in hotels:
            try:
                results[hotel.id] = await self.sync_hotel_by_id(hotel.id)
            except Exception as e:
                logger.error(f"Sync error for hotel id={hotel.id}: {e}", exc_info=True)
                results[hotel.id] = {"status": "error", "error": str(e)}
        return results

    async def sync_hotel_by_id(self, hotel_id: int):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
            hotel = result.scalar_one_or_none()
            if not hotel:
                return {"status": "error", "error": "Hotel not found"}

            # Copy all needed fields before closing session
            hotel_data = {
                "id": hotel.id,
                "name": hotel.name,
                "hotspot_code": hotel.hotspot_code,
                "mssql_server": hotel.mssql_server,
                "mssql_port": hotel.mssql_port,
                "mssql_database": hotel.mssql_database,
                "mssql_username": hotel.mssql_username,
                "mssql_password": hotel.mssql_password,
                "mssql_table_booking": hotel.mssql_table_booking,
                "mssql_col_booking_id": hotel.mssql_col_booking_id,
                "mssql_col_guest_name": hotel.mssql_col_guest_name,
                "mssql_col_guest_phone": hotel.mssql_col_guest_phone,
                "mssql_col_room_number": hotel.mssql_col_room_number,
                "mssql_col_checkin": hotel.mssql_col_checkin,
                "mssql_col_checkout": hotel.mssql_col_checkout,
                "mssql_col_status": hotel.mssql_col_status,
                "mssql_col_status_confirmed": hotel.mssql_col_status_confirmed,
                "mikrotik_host": hotel.mikrotik_host,
                "mikrotik_port": hotel.mikrotik_port,
                "mikrotik_username": hotel.mikrotik_username,
                "mikrotik_password": hotel.mikrotik_password,
                "mikrotik_hotspot_server": hotel.mikrotik_hotspot_server,
                "hotspot_password_length": hotel.hotspot_password_length,
                "checkout_grace_minutes": hotel.checkout_grace_minutes,
            }

        return await self._do_sync(hotel_data)

    async def sync_hotel(self, hotel):
        """Called with a hotel ORM object — copy data first to avoid greenlet issues"""
        return await self.sync_hotel_by_id(hotel.id)

    async def _do_sync(self, h: dict):
        created = 0
        deleted = 0
        errors = 0
        log_messages = []

        try:
            # 1. Fetch active bookings from MSSQL
            mssql = MSSQLService(h)
            bookings = await mssql.get_active_bookings()
            log_messages.append(f"Fetched {len(bookings)} active bookings from PMS")

            # 2. Upsert bookings into local DB
            async with AsyncSessionLocal() as db:
                for b in bookings:
                    existing = await db.execute(
                        select(Booking).where(
                            and_(Booking.hotel_id == h["id"],
                                 Booking.booking_id == str(b["booking_id"]))
                        )
                    )
                    existing = existing.scalar_one_or_none()
                    if existing:
                        existing.guest_name = b.get("guest_name", "")
                        existing.room_number = str(b.get("room_number", ""))
                        existing.status = str(b.get("status", ""))
                        existing.checkin_date = b.get("checkin_date")
                        existing.checkout_date = b.get("checkout_date")
                    else:
                        db.add(Booking(
                            hotel_id=h["id"],
                            booking_id=str(b["booking_id"]),
                            guest_name=b.get("guest_name", ""),
                            guest_phone=b.get("guest_phone", ""),
                            room_number=str(b.get("room_number", "")),
                            status=str(b.get("status", "")),
                            checkin_date=b.get("checkin_date"),
                            checkout_date=b.get("checkout_date"),
                        ))
                await db.commit()

            # 3. Create hotspot users for active bookings
            mikrotik = MikrotikService(h)
            active_booking_ids = set()

            for b in bookings:
                bid = str(b["booking_id"])
                active_booking_ids.add(bid)

                async with AsyncSessionLocal() as db:
                    exists = await db.execute(
                        select(HotspotUser).where(
                            and_(HotspotUser.hotel_id == h["id"],
                                 HotspotUser.booking_id == bid)
                        )
                    )
                    exists = exists.scalar_one_or_none()

                if not exists:
                    try:
                        username, password = await mikrotik.create_user(
                            room_number=str(b.get("room_number", "")),
                            guest_name=b.get("guest_name", ""),
                            booking_id=bid,
                            hotel_code=h["hotspot_code"],
                        )
                        async with AsyncSessionLocal() as db:
                            db.add(HotspotUser(
                                hotel_id=h["id"],
                                booking_id=bid,
                                username=username,
                                password=password,
                                room_number=str(b.get("room_number", "")),
                                guest_name=b.get("guest_name", ""),
                                status=HotspotUserStatus.active,
                            ))
                            await db.commit()
                        created += 1
                        log_messages.append(f"Created hotspot user: {username}")
                    except Exception as e:
                        errors += 1
                        log_messages.append(f"Failed to create user for booking {bid}: {e}")

            # 4. Delete users whose bookings are no longer active
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(HotspotUser).where(
                        and_(HotspotUser.hotel_id == h["id"],
                             HotspotUser.status == HotspotUserStatus.active)
                    )
                )
                active_users = result.scalars().all()
                users_to_delete = [
                    {"id": u.id, "username": u.username, "booking_id": u.booking_id}
                    for u in active_users
                    if u.booking_id not in active_booking_ids
                ]

            for u in users_to_delete:
                try:
                    await mikrotik.delete_user(u["username"])
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(HotspotUser).where(HotspotUser.id == u["id"]))
                        user = result.scalar_one_or_none()
                        if user:
                            user.status = HotspotUserStatus.deleted
                            await db.commit()
                    deleted += 1
                    log_messages.append(f"Deleted hotspot user: {u['username']}")
                except Exception as e:
                    errors += 1
                    log_messages.append(f"Failed to delete user {u['username']}: {e}")

        except Exception as e:
            logger.error(f"Sync failed for hotel {h['name']}: {e}", exc_info=True)
            errors += 1
            log_messages.append(f"Sync error: {e}")

        # 5. Save sync log
        async with AsyncSessionLocal() as db:
            db.add(SyncLog(
                hotel_id=h["id"],
                status="success" if errors == 0 else "partial" if (created + deleted) > 0 else "error",
                bookings_synced=len(bookings) if 'bookings' in dir() else 0,
                users_created=created,
                users_deleted=deleted,
                errors=errors,
                message="\n".join(log_messages[-20:]),
            ))
            await db.commit()

        return {
            "status": "success" if errors == 0 else "error",
            "created": created,
            "deleted": deleted,
            "errors": errors,
        }


sync_engine = SyncEngine()
