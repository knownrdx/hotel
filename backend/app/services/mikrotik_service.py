import routeros_api
import secrets
import string
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class MikrotikService:
    def __init__(self, hotel):
        self.hotel = hotel

    def _get_connection(self):
        return routeros_api.RouterOsApiPool(
            self.hotel.mikrotik_host,
            username=self.hotel.mikrotik_username,
            password=self.hotel.mikrotik_password,
            port=self.hotel.mikrotik_port,
            plaintext_login=True
        )

    def test_connection(self) -> Dict[str, Any]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            conn.get_resource('/system/identity').get()
            pool.disconnect()
            return {"success": True, "message": "Mikrotik connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def create_hotspot_user(
        self,
        username: str,
        password: Optional[str] = None,
        profile: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        if not password:
            password = generate_password()
        if not profile:
            profile = self.hotel.mikrotik_hotspot_profile or "default"

        try:
            pool = self._get_connection()
            conn = pool.get_api()
            hotspot_users = conn.get_resource('/ip/hotspot/user')

            # Check if user already exists
            existing = hotspot_users.get(name=username)
            if existing:
                pool.disconnect()
                return {
                    "success": True,
                    "message": "User already exists",
                    "username": username,
                    "password": password,
                    "existed": True
                }

            hotspot_users.add(
                name=username,
                password=password,
                profile=profile,
                comment=comment or f"Hotel guest - {username}"
            )
            pool.disconnect()
            logger.info(f"Mikrotik user created: {username}")
            return {
                "success": True,
                "message": "User created",
                "username": username,
                "password": password,
                "existed": False
            }
        except Exception as e:
            logger.error(f"Mikrotik create user error: {e}")
            return {"success": False, "message": str(e)}

    def delete_hotspot_user(self, username: str) -> Dict[str, Any]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            hotspot_users = conn.get_resource('/ip/hotspot/user')

            users = hotspot_users.get(name=username)
            if not users:
                pool.disconnect()
                return {"success": True, "message": "User not found (already deleted)"}

            for user in users:
                hotspot_users.remove(id=user['id'])

            pool.disconnect()
            logger.info(f"Mikrotik user deleted: {username}")
            return {"success": True, "message": "User deleted"}
        except Exception as e:
            logger.error(f"Mikrotik delete user error: {e}")
            return {"success": False, "message": str(e)}

    def disable_hotspot_user(self, username: str) -> Dict[str, Any]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            hotspot_users = conn.get_resource('/ip/hotspot/user')

            users = hotspot_users.get(name=username)
            if not users:
                pool.disconnect()
                return {"success": False, "message": "User not found"}

            for user in users:
                hotspot_users.set(id=user['id'], disabled='yes')

            pool.disconnect()
            return {"success": True, "message": "User disabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_hotspot_users(self) -> List[Dict[str, Any]]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            hotspot_users = conn.get_resource('/ip/hotspot/user')
            users = hotspot_users.get()
            pool.disconnect()
            return users
        except Exception as e:
            logger.error(f"Mikrotik list users error: {e}")
            return []

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            active = conn.get_resource('/ip/hotspot/active')
            sessions = active.get()
            pool.disconnect()
            return sessions
        except Exception as e:
            logger.error(f"Mikrotik active sessions error: {e}")
            return []

    def get_profiles(self) -> List[str]:
        try:
            pool = self._get_connection()
            conn = pool.get_api()
            profiles = conn.get_resource('/ip/hotspot/user/profile').get()
            pool.disconnect()
            return [p.get('name', '') for p in profiles]
        except Exception as e:
            return []
