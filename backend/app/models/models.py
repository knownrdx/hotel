from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"


class SyncStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class HotspotUserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    deleted = "deleted"


class AppUser(Base):
    __tablename__ = "app_users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SAEnum(UserRole), default=UserRole.manager)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Hotel(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # MSSQL connection
    mssql_host = Column(String(255))
    mssql_port = Column(Integer, default=1433)
    mssql_database = Column(String(255))
    mssql_username = Column(String(255))
    mssql_password = Column(String(255))
    mssql_table_booking = Column(String(255), default="PMS.RRVDATBL")
    mssql_table_guest = Column(String(255), default="Guests")
    mssql_col_booking_id = Column(String(100), default="RESNUB")
    mssql_col_guest_name = Column(String(100), default="GSTNAM")
    mssql_col_guest_phone = Column(String(100), default="MBLNUB")
    mssql_col_room_number = Column(String(100), default="ROOMNO")
    mssql_col_checkin = Column(String(100), default="ARRIVL")
    mssql_col_checkout = Column(String(100), default="DEPDAT")
    mssql_col_status = Column(String(100), default="RSVSTS")
    mssql_col_status_confirmed = Column(String(100), default="R,I")

    # Mikrotik
    mikrotik_host = Column(String(255))
    mikrotik_port = Column(Integer, default=8728)
    mikrotik_username = Column(String(255), default="admin")
    mikrotik_password = Column(String(255))
    mikrotik_hotspot_server = Column(String(255), default="hotspot1")
    mikrotik_hotspot_profile = Column(String(255), default="default")

    # RADIUS
    radius_host = Column(String(255))
    radius_port = Column(Integer, default=1812)
    radius_secret = Column(String(255))
    use_radius = Column(Boolean, default=False)

    # Hotspot username code (e.g. "almanarDub" → SHEIKH@316_almanarDub)
    hotspot_code = Column(String(50), default="")

    # Sync settings
    sync_interval_minutes = Column(Integer, default=5)
    checkout_grace_minutes = Column(Integer, default=0)
    auto_sync_enabled = Column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="hotel", cascade="all, delete-orphan")
    hotspot_users = relationship("HotspotUser", back_populates="hotel", cascade="all, delete-orphan")
    logs = relationship("SyncLog", back_populates="hotel", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    external_booking_id = Column(String(255))
    guest_name = Column(String(255))
    guest_phone = Column(String(100))
    room_number = Column(String(50))
    check_in = Column(DateTime(timezone=True))
    check_out = Column(DateTime(timezone=True))
    status = Column(String(100))
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hotel = relationship("Hotel", back_populates="bookings")
    hotspot_user = relationship("HotspotUser", back_populates="booking", uselist=False)


class HotspotUser(Base):
    __tablename__ = "hotspot_users"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255))
    status = Column(SAEnum(HotspotUserStatus), default=HotspotUserStatus.active)
    mikrotik_created = Column(Boolean, default=False)
    radius_created = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    extra_info = Column(JSON)

    hotel = relationship("Hotel", back_populates="hotspot_users")
    booking = relationship("Booking", back_populates="hotspot_user")


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    status = Column(SAEnum(SyncStatus), default=SyncStatus.pending)
    message = Column(Text)
    details = Column(JSON)
    bookings_found = Column(Integer, default=0)
    users_created = Column(Integer, default=0)
    users_deleted = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hotel = relationship("Hotel", back_populates="logs")
