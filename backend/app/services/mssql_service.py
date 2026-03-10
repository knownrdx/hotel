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
            f"Connection Timeout=30;"
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

    async def get_table_columns(self, table_name: str) -> List[Dict[str, str]]:
        """Get columns of a specific table with data types"""
        try:
            schema, tname = table_name.split('.', 1) if '.' in table_name else ('dbo', table_name)
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                        ORDER BY ORDINAL_POSITION
                    """, schema, tname)
                    rows = await cur.fetchall()
                    return [
                        {"name": r[0], "type": r[1], "max_length": r[2], "nullable": r[3]}
                        for r in rows
                    ]
        except Exception as e:
            logger.error(f"get_table_columns error: {e}")
            return []

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample rows from a table to help identify correct columns"""
        try:
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"SELECT TOP {limit} * FROM {table_name}")
                    columns = [desc[0] for desc in cur.description]
                    rows = await cur.fetchall()
                    return [
                        {col: (str(val)[:200] if val is not None else None) for col, val in zip(columns, row)}
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"get_table_sample error: {e}")
            return []

    async def scan_all_tables(self) -> List[Dict[str, Any]]:
        """Get ALL tables with their columns in ONE single query — fast!"""
        try:
            async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT
                            t.TABLE_SCHEMA + '.' + t.TABLE_NAME AS full_table,
                            STRING_AGG(c.COLUMN_NAME, ',') WITHIN GROUP (ORDER BY c.ORDINAL_POSITION) AS columns,
                            COUNT(c.COLUMN_NAME) AS col_count
                        FROM INFORMATION_SCHEMA.TABLES t
                        JOIN INFORMATION_SCHEMA.COLUMNS c
                            ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                        WHERE t.TABLE_TYPE = 'BASE TABLE'
                        GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
                        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME
                    """)
                    rows = await cur.fetchall()
                    return [
                        {
                            "table": row[0],
                            "columns": row[1].split(',') if row[1] else [],
                            "column_count": row[2]
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"scan_all_tables error: {e}")
            # Fallback: if STRING_AGG not supported (older SQL Server)
            try:
                async with await aioodbc.connect(dsn=self._conn_str(), autocommit=True) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("""
                            SELECT
                                t.TABLE_SCHEMA + '.' + t.TABLE_NAME AS full_table,
                                c.COLUMN_NAME
                            FROM INFORMATION_SCHEMA.TABLES t
                            JOIN INFORMATION_SCHEMA.COLUMNS c
                                ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                            WHERE t.TABLE_TYPE = 'BASE TABLE'
                            ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
                        """)
                        rows = await cur.fetchall()
                        tables_dict = {}
                        for row in rows:
                            tbl = row[0]
                            if tbl not in tables_dict:
                                tables_dict[tbl] = []
                            tables_dict[tbl].append(row[1])
                        return [
                            {"table": tbl, "columns": cols, "column_count": len(cols)}
                            for tbl, cols in tables_dict.items()
                        ]
            except Exception as e2:
                logger.error(f"scan_all_tables fallback error: {e2}")
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
