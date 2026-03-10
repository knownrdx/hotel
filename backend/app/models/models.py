from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"


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
    hotspot_code = Column(String(50), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # MSSQL — using 'mssql_server' consistently everywhere
    mssql_server = Column(String(255))
    mssql_port = Column(Integer, default=1433)
    mssql_database = Column(String(255))
    mssql_username = Column(String(255))
    mssql_password = Column(String(255))
    mssql_table_booking = Column(String(255), default="PMS.RRVDATBL")
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

    # Hotspot settings
    hotspot_password_length = Column(Integer, default=8)
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=5)
    checkout_grace_minutes = Column(Integer, default=60)

    bookings = relationship("Booking", back_populates="hotel", cascade="all, delete-orphan")
    hotspot_users = relationship("HotspotUser", back_populates="hotel", cascade="all, delete-orphan")
    logs = relationship("SyncLog", back_populates="hotel", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    booking_id = Column(String(255))
    guest_name = Column(String(255))
    guest_phone = Column(String(100))
    room_number = Column(String(50))
    checkin_date = Column(DateTime(timezone=True))
    checkout_date = Column(DateTime(timezone=True))
    status = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hotel = relationship("Hotel", back_populates="bookings")


class HotspotUser(Base):
    __tablename__ = "hotspot_users"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    booking_id = Column(String(255))
    username = Column(String(255), nullable=False)
    password = Column(String(255))
    room_number = Column(String(50))
    guest_name = Column(String(255))
    status = Column(SAEnum(HotspotUserStatus), default=HotspotUserStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    hotel = relationship("Hotel", back_populates="hotspot_users")


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    status = Column(String(50), default="pending")
    message = Column(Text)
    bookings_synced = Column(Integer, default=0)
    users_created = Column(Integer, default=0)
    users_deleted = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hotel = relationship("Hotel", back_populates="logs")
