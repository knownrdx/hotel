import aioodbc
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MSSQLService:
    def __init__(self, hotel):
        self.hotel = hotel
        self.conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={hotel.mssql_host},{hotel.mssql_port};"
            f"DATABASE={hotel.mssql_database};"
            f"UID={hotel.mssql_username};"
            f"PWD={hotel.mssql_password};"
            f"TrustServerCertificate=yes;"
        )

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def get_confirmed_bookings(self) -> List[Dict[str, Any]]:
        h = self.hotel
        query = f"""
            SELECT 
                [{h.mssql_col_booking_id}] as booking_id,
                [{h.mssql_col_guest_name}] as guest_name,
                [{h.mssql_col_guest_phone}] as guest_phone,
                [{h.mssql_col_room_number}] as room_number,
                [{h.mssql_col_checkin}] as check_in,
                [{h.mssql_col_checkout}] as check_out,
                [{h.mssql_col_status}] as status
            FROM [{h.mssql_table_booking}]
            WHERE [{h.mssql_col_status}] = ?
            AND [{h.mssql_col_checkout}] >= GETDATE()
        """
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, h.mssql_col_status_confirmed)
                    columns = [col[0] for col in cursor.description]
                    rows = await cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"MSSQL error for hotel {self.hotel.name}: {e}")
            raise

    async def get_all_bookings(self, limit: int = 100) -> List[Dict[str, Any]]:
        h = self.hotel
        query = f"""
            SELECT TOP {limit}
                [{h.mssql_col_booking_id}] as booking_id,
                [{h.mssql_col_guest_name}] as guest_name,
                [{h.mssql_col_guest_phone}] as guest_phone,
                [{h.mssql_col_room_number}] as room_number,
                [{h.mssql_col_checkin}] as check_in,
                [{h.mssql_col_checkout}] as check_out,
                [{h.mssql_col_status}] as status
            FROM [{h.mssql_table_booking}]
            ORDER BY [{h.mssql_col_checkin}] DESC
        """
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    columns = [col[0] for col in cursor.description]
                    rows = await cursor.fetchall()
                    result = []
                    for row in rows:
                        d = dict(zip(columns, row))
                        # Convert datetime objects to string
                        for k, v in d.items():
                            if isinstance(v, datetime):
                                d[k] = v.isoformat()
                        result.append(d)
                    return result
        except Exception as e:
            logger.error(f"MSSQL error: {e}")
            raise

    async def get_tables(self) -> List[str]:
        """List all tables in the database for configuration help"""
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"MSSQL get_tables error: {e}")
            raise

    async def get_columns(self, table_name: str) -> List[str]:
        """List columns in a table"""
        query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, table_name)
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"MSSQL get_columns error: {e}")
            raise
