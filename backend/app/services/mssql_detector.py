"""
Smart MSSQL Schema Detector
Automatically finds reservation tables and columns by scanning the database
"""
import logging
import aioodbc
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Keywords to identify reservation/booking tables
BOOKING_TABLE_HINTS = [
    'RESERV', 'BOOKING', 'RRVDA', 'RRVDB', 'FOLIO', 'STAY',
    'CHECKIN', 'ARRIVAL', 'GUEST', 'ROOM', 'RSVN', 'RRSV'
]

# Keywords to identify specific columns
COLUMN_HINTS = {
    "booking_id":   ['RESNUB', 'RESNO', 'BOOKING_ID', 'RESERV_NO', 'FOLIO', 'CONFNO', 'CONF_NO', 'RSVNNO'],
    "guest_name":   ['GSTNAM', 'GUEST_NAME', 'GUESTNAME', 'FULLNAME', 'NAME', 'CUSTNAME', 'CUST_NAME'],
    "guest_phone":  ['MBLNUB', 'MOBILE', 'PHONE', 'TEL', 'CONTACT', 'CELLNO', 'PHONENO'],
    "room_number":  ['ROOMNO', 'ROOM_NO', 'ROOM', 'ROOMNUM', 'ROOM_NUMBER', 'RMNO'],
    "checkin":      ['ARRIVL', 'ARRIVAL', 'CHECKIN', 'CHECK_IN', 'ARRDATE', 'ARR_DATE', 'CHECKINDATE'],
    "checkout":     ['DEPDAT', 'DEPARTURE', 'CHECKOUT', 'CHECK_OUT', 'DEPDATE', 'DEP_DATE', 'CHECKOUTDATE'],
    "status":       ['RSVSTS', 'STATUS', 'RESSTATUS', 'RES_STATUS', 'STATE', 'BOOKINGSTATUS'],
}

STATUS_VALUE_HINTS = {
    "reserved":    ['R', 'RES', 'RESERVED', 'CONFIRM', 'C', '1'],
    "checkedin":   ['I', 'IN', 'INHOUSE', 'CHECKEDIN', 'CI', '2'],
    "checkedout":  ['O', 'OUT', 'CO', 'CHECKOUT', 'DEPARTED', '3'],
    "cancelled":   ['X', 'CAN', 'CANCELLED', 'CANCELED', 'N', '4'],
}


def score_table(table_name: str) -> int:
    upper = table_name.upper()
    for hint in BOOKING_TABLE_HINTS:
        if hint in upper:
            return 10
    return 0


def score_column(col_name: str, hints: List[str]) -> int:
    upper = col_name.upper()
    for i, hint in enumerate(hints):
        if upper == hint:
            return 100 - i  # exact match scores highest
        if hint in upper:
            return 50 - i
    return 0


class MSSQLDetector:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    async def detect(self) -> Dict[str, Any]:
        """Full auto-detection — returns suggested config"""
        try:
            async with await aioodbc.connect(dsn=self.conn_str, autocommit=True) as conn:
                tables = await self._get_tables(conn)
                if not tables:
                    return {"success": False, "error": "No tables found in database"}

                # Find best booking table
                scored = [(score_table(t), t) for t in tables]
                scored.sort(reverse=True)
                top_tables = [t for s, t in scored if s > 0]

                if not top_tables:
                    # No clear winner — return all tables for manual selection
                    return {
                        "success": False,
                        "error": "Could not auto-detect booking table",
                        "all_tables": tables[:50],
                        "suggestion": "Please select the reservation table manually"
                    }

                # Try each top table to find columns + sample data
                for table in top_tables[:3]:
                    result = await self._analyze_table(conn, table)
                    if result and result.get("booking_id"):
                        # Found a good table
                        status_values = await self._detect_status_values(
                            conn, table, result.get("status", "STATUS")
                        )
                        return {
                            "success": True,
                            "table": table,
                            "columns": result,
                            "status_values": status_values,
                            "active_statuses": self._guess_active_statuses(status_values),
                            "all_tables": top_tables,
                            "message": f"Auto-detected from table: {table}"
                        }

                return {
                    "success": False,
                    "error": "Found candidate tables but could not map columns",
                    "all_tables": top_tables,
                    "suggestion": "Please configure columns manually"
                }

        except Exception as e:
            logger.error(f"Auto-detect error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_tables(self, conn) -> List[str]:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT TABLE_SCHEMA + '.' + TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    async def _analyze_table(self, conn, table: str) -> Dict[str, str] | None:
        """Get columns and map them to known fields"""
        try:
            schema, tname = table.split('.', 1) if '.' in table else ('dbo', table)
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """, schema, tname)
                cols = await cur.fetchall()
                col_names = [r[0] for r in cols]

            if not col_names:
                return None

            # Map each field to best matching column
            mapping = {}
            for field, hints in COLUMN_HINTS.items():
                best_score = 0
                best_col = None
                for col in col_names:
                    s = score_column(col, hints)
                    if s > best_score:
                        best_score = s
                        best_col = col
                if best_col and best_score > 0:
                    mapping[field] = best_col

            return mapping if mapping else None

        except Exception as e:
            logger.warning(f"analyze_table {table} error: {e}")
            return None

    async def _detect_status_values(self, conn, table: str, status_col: str) -> List[str]:
        """Get distinct values in status column"""
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT DISTINCT TOP 20 {status_col} FROM {table} WHERE {status_col} IS NOT NULL")
                rows = await cur.fetchall()
                return [str(r[0]).strip() for r in rows if r[0] is not None]
        except Exception:
            return []

    def _guess_active_statuses(self, values: List[str]) -> str:
        """Guess which status values mean 'active/confirmed'"""
        active = []
        for v in values:
            upper = v.upper()
            for status_type in ["reserved", "checkedin"]:
                if upper in [h.upper() for h in STATUS_VALUE_HINTS[status_type]]:
                    active.append(v)
                    break
        return ",".join(active) if active else ",".join(values[:2])
