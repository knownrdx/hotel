import aioodbc
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def decimal_date_to_datetime(val) -> Optional[datetime]:
    """Convert IDS Next DECIMAL(8,0) date format YYYYMMDD to datetime"""
    if not val or val == 0:
        return None
    try:
        s = str(int(val))
        if len(s) == 8:
            return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        pass
    return None


def decimal_time_to_str(val) -> str:
    """Convert IDS Next DECIMAL(4,2) time to HH:MM string"""
    if not val:
        return "12:00"
    try:
        hours = int(val)
        minutes = int(round((float(val) - hours) * 100))
        return f"{hours:02d}:{minutes:02d}"
    except Exception:
        return "12:00"


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
        """
        IDS Next PMS - fetch confirmed/checked-in reservations.
        
        Key tables (PMS schema):
          - PMS.RRVDATBL : Reservation header (RESNUB, ARRIVL, DEPDAT, RSVSTS, PRPCOD)
          - PMS.RRVDBTBL : Reservation detail (room, rate, guest link)
          - PMS.CMCMATBL : Guest contact (SRLNUB → guest master SRLNUB)
        
        RSVSTS values: 'R'=Reserved, 'I'=Checked-in, 'O'=Checked-out, 'C'=Cancelled
        Dates stored as DECIMAL(8,0) = YYYYMMDD
        """
        h = self.hotel

        # Use custom query if provided, else use IDS Next default
        if h.mssql_table_booking and h.mssql_table_booking.strip().upper().startswith("SELECT"):
            # Custom SQL query stored in mssql_table_booking field
            query = h.mssql_table_booking
        else:
            # Default IDS Next query — fetch Reserved + Checked-In only
            today_decimal = int(datetime.now().strftime("%Y%m%d"))
            query = f"""
                SELECT
                    A.RESNUB        AS booking_id,
                    A.PRPCOD        AS property,
                    A.ARRIVL        AS check_in_dec,
                    A.DEPDAT        AS check_out_dec,
                    A.RSVSTS        AS status,
                    A.NOSADU        AS adults,
                    A.NOSCHD        AS children,
                    B.ROOMNO        AS room_number,
                    B.ROMTYP        AS room_type,
                    B.RATCOD        AS rate_code,
                    COALESCE(C.GSTNAM, A.RESNUB) AS guest_name,
                    COALESCE(M.MBLNUB, M.TELNUB, '') AS guest_phone,
                    COALESCE(M.MAILID, '')          AS guest_email
                FROM PMS.RRVDATBL A WITH (NOLOCK)
                LEFT JOIN PMS.RRVDBTBL B WITH (NOLOCK)
                    ON A.RESNUB = B.RESNUB AND A.PRPCOD = B.PRPCOD
                LEFT JOIN PMS.CMGMSTBL C WITH (NOLOCK)
                    ON A.GSTSRL = C.SRLNUB
                LEFT JOIN PMS.CMCMATBL M WITH (NOLOCK)
                    ON C.SRLNUB = M.SRLNUB AND M.ADDTYP = 'P'
                WHERE A.RSVSTS IN ('R', 'I')
                AND A.DEPDAT >= {today_decimal}
                ORDER BY A.ARRIVL, A.RESNUB
            """

        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    columns = [col[0].lower() for col in cursor.description]
                    rows = await cursor.fetchall()
                    results = []
                    for row in rows:
                        d = dict(zip(columns, row))
                        # Convert IDS Next decimal dates to ISO strings
                        for date_col in ['check_in_dec', 'arrivl']:
                            if date_col in d:
                                dt = decimal_date_to_datetime(d[date_col])
                                d['check_in'] = dt.isoformat() if dt else None
                                del d[date_col]
                        for date_col in ['check_out_dec', 'depdat']:
                            if date_col in d:
                                dt = decimal_date_to_datetime(d[date_col])
                                d['check_out'] = dt.isoformat() if dt else None
                                del d[date_col]
                        # Normalize
                        d['booking_id'] = str(d.get('booking_id', ''))
                        d['room_number'] = str(d.get('room_number', '')).strip()
                        d['guest_name'] = str(d.get('guest_name', '')).strip()
                        d['guest_phone'] = str(d.get('guest_phone', '')).strip()
                        d['status'] = str(d.get('status', '')).strip()
                        results.append(d)
                    return results
        except Exception as e:
            logger.error(f"MSSQL confirmed bookings error for hotel {self.hotel.name}: {e}")
            raise

    async def get_all_bookings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """All recent bookings for display in UI"""
        today_decimal = int(datetime.now().strftime("%Y%m%d"))
        # Show last 30 days + future
        past_decimal = int((datetime.now().replace(day=1)).strftime("%Y%m%d"))

        query = f"""
            SELECT TOP {limit}
                A.RESNUB        AS booking_id,
                A.PRPCOD        AS property,
                A.ARRIVL        AS check_in_dec,
                A.DEPDAT        AS check_out_dec,
                A.RSVSTS        AS status,
                B.ROOMNO        AS room_number,
                B.ROMTYP        AS room_type,
                COALESCE(C.GSTNAM, CAST(A.RESNUB AS VARCHAR)) AS guest_name,
                COALESCE(M.MBLNUB, M.TELNUB, '')  AS guest_phone
            FROM PMS.RRVDATBL A WITH (NOLOCK)
            LEFT JOIN PMS.RRVDBTBL B WITH (NOLOCK)
                ON A.RESNUB = B.RESNUB AND A.PRPCOD = B.PRPCOD
            LEFT JOIN PMS.CMGMSTBL C WITH (NOLOCK)
                ON A.GSTSRL = C.SRLNUB
            LEFT JOIN PMS.CMCMATBL M WITH (NOLOCK)
                ON C.SRLNUB = M.SRLNUB AND M.ADDTYP = 'P'
            WHERE A.DEPDAT >= {past_decimal}
            ORDER BY A.ARRIVL DESC
        """
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    columns = [col[0].lower() for col in cursor.description]
                    rows = await cursor.fetchall()
                    results = []
                    for row in rows:
                        d = dict(zip(columns, row))
                        # Convert decimal dates
                        ci = decimal_date_to_datetime(d.get('check_in_dec'))
                        co = decimal_date_to_datetime(d.get('check_out_dec'))
                        d['check_in'] = ci.isoformat() if ci else None
                        d['check_out'] = co.isoformat() if co else None
                        d.pop('check_in_dec', None)
                        d.pop('check_out_dec', None)
                        # Stringify
                        for k, v in d.items():
                            if v is None:
                                d[k] = ''
                            elif not isinstance(v, str):
                                d[k] = str(v)
                        results.append(d)
                    return results
        except Exception as e:
            logger.error(f"MSSQL get_all_bookings error: {e}")
            raise

    async def get_tables(self) -> List[str]:
        """List tables in PMS schema"""
        query = """
            SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA = 'PMS'
            ORDER BY TABLE_NAME
        """
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
        """List columns in a table (supports schema.table format)"""
        parts = table_name.split('.')
        schema = parts[0] if len(parts) > 1 else 'PMS'
        tbl = parts[-1]
        query = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        try:
            async with aioodbc.connect(dsn=self.conn_str) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, schema, tbl)
                    rows = await cursor.fetchall()
                    return [f"{row[0]} ({row[1]})" for row in rows]
        except Exception as e:
            logger.error(f"MSSQL get_columns error: {e}")
            raise
