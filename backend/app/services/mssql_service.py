import logging
import aioodbc
from typing import List, Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)


def decimal_date_to_datetime(val) -> datetime | None:
    if not val:
        return None
    try:
        s = str(int(val))
        if len(s) == 8:
            return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        pass
    return None


def make_username(room_number: str, guest_name: str, booking_id: str, hotel_code: str = "") -> str:
    last_name = guest_name.strip().split()[-1].upper() if guest_name.strip() else "GUEST"
    if hotel_code:
        return f"{last_name}@{room_number}_{hotel_code}"
    return f"{last_name}@{room_number}"


class MSSQLService:
    def __init__(self, hotel: dict):
        self.hotel = hotel

    def _conn_str(self) -> str:
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.hotel['mssql_server']},{self.hotel['mssql_port'] or 1433};"
            f"DATABASE={self.hotel['mssql_database']};"
            f"UID={self.hotel['mssql_username']};"
            f"PWD={self.hotel['mssql_password']};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )

    async def test_connection(self) -> dict:
        try:
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT @@VERSION")
                    row = await cur.fetchone()
                    return {"success": True, "version": str(row[0])[:100] if row else "OK"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_tables(self) -> List[str]:
        """List all tables in the database to help user find correct table name"""
        try:
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT TABLE_SCHEMA + '.' + TABLE_NAME
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_TYPE = 'BASE TABLE'
                        ORDER BY TABLE_SCHEMA, TABLE_NAME
                    """)
                    rows = await cur.fetchall()
                    return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"get_tables error: {e}")
            return []

    async def get_active_bookings(self) -> List[Dict[str, Any]]:
        h = self.hotel
        table = h.get("mssql_table_booking", "PMS.RRVDATBL")
        col_id = h.get("mssql_col_booking_id", "RESNUB")
        col_name = h.get("mssql_col_guest_name", "GSTNAM")
        col_phone = h.get("mssql_col_guest_phone", "MBLNUB")
        col_room = h.get("mssql_col_room_number", "ROOMNO")
        col_checkin = h.get("mssql_col_checkin", "ARRIVL")
        col_checkout = h.get("mssql_col_checkout", "DEPDAT")
        col_status = h.get("mssql_col_status", "RSVSTS")
        statuses = [s.strip() for s in h.get("mssql_col_status_confirmed", "R,I").split(",")]
        status_list = ",".join(f"'{s}'" for s in statuses)

        query = f"""
            SELECT
                {col_id}, {col_name}, {col_phone},
                {col_room}, {col_checkin}, {col_checkout}, {col_status}
            FROM {table}
            WHERE {col_status} IN ({status_list})
        """
        try:
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    rows = await cur.fetchall()
                    results = []
                    for row in rows:
                        results.append({
                            "booking_id": row[0],
                            "guest_name": str(row[1] or "").strip(),
                            "guest_phone": str(row[2] or "").strip(),
                            "room_number": str(row[3] or "").strip(),
                            "checkin_date": decimal_date_to_datetime(row[4]),
                            "checkout_date": decimal_date_to_datetime(row[5]),
                            "status": str(row[6] or "").strip(),
                        })
                    return results
        except Exception as e:
            logger.error(f"MSSQL get_active_bookings error: {e}")
            raise

    async def get_all_bookings(self) -> List[Dict[str, Any]]:
        """For live preview — returns all bookings"""
        return await self.get_active_bookings()
