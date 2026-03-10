import logging
import asyncio
import routeros_api

logger = logging.getLogger(__name__)


def make_username(room_number: str, guest_name: str, hotel_code: str = "") -> str:
    last_name = guest_name.strip().split()[-1].upper() if guest_name.strip() else "GUEST"
    last_name = ''.join(c for c in last_name if c.isalnum())
    if hotel_code:
        return f"{last_name}@{room_number}_{hotel_code}"
    return f"{last_name}@{room_number}"


class MikrotikService:
    def __init__(self, hotel: dict):
        self.hotel = hotel

    def _connect(self):
        return routeros_api.RouterOsApiPool(
            self.hotel['mikrotik_host'],
            username=self.hotel['mikrotik_username'],
            password=self.hotel['mikrotik_password'],
            port=int(self.hotel.get('mikrotik_port', 8728)),
            plaintext_login=True
        )

    async def test_connection(self) -> dict:
        try:
            pool = await asyncio.get_event_loop().run_in_executor(None, self._connect)
            api = pool.get_api()
            identity = api.get_resource('/system/identity').get()
            pool.disconnect()
            return {"success": True, "identity": identity[0].get('name', 'OK') if identity else 'OK'}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_user(self, room_number: str, guest_name: str, booking_id: str, hotel_code: str = "") -> tuple[str, str]:
        username = make_username(room_number, guest_name, hotel_code)
        # Password = same as username
        password = username

        def _create():
            pool = self._connect()
            api = pool.get_api()
            hotspot = api.get_resource('/ip/hotspot/user')
            # Check if user already exists
            existing = hotspot.get(name=username)
            if not existing:
                hotspot.add(
                    name=username,
                    password=password,
                    server=self.hotel.get('mikrotik_hotspot_server', 'hotspot1'),
                    comment=f"booking:{booking_id}"
                )
            pool.disconnect()
            return username, password

        return await asyncio.get_event_loop().run_in_executor(None, _create)

    async def delete_user(self, username: str) -> bool:
        def _delete():
            pool = self._connect()
            api = pool.get_api()
            hotspot = api.get_resource('/ip/hotspot/user')
            users = hotspot.get(name=username)
            for u in users:
                hotspot.remove(id=u['id'])
            pool.disconnect()
            return True

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _delete)
        except Exception as e:
            logger.error(f"Mikrotik delete user {username} error: {e}")
            return False

    async def get_users(self) -> list:
        def _get():
            pool = self._connect()
            api = pool.get_api()
            users = api.get_resource('/ip/hotspot/user').get()
            pool.disconnect()
            return users

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _get)
        except Exception as e:
            logger.error(f"Mikrotik get users error: {e}")
            return []
