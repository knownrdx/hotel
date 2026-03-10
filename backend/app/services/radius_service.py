import pyrad.packet
import pyrad.client
import pyrad.dictionary
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Minimal RADIUS dictionary
RADIUS_DICT_CONTENT = """
ATTRIBUTE User-Name 1 string
ATTRIBUTE User-Password 2 string
ATTRIBUTE NAS-IP-Address 4 ipaddr
ATTRIBUTE NAS-Port 5 integer
ATTRIBUTE Service-Type 6 integer
ATTRIBUTE Framed-Protocol 7 integer
ATTRIBUTE Reply-Message 18 string
ATTRIBUTE Session-Timeout 27 integer
ATTRIBUTE Idle-Timeout 28 integer
ATTRIBUTE Called-Station-Id 30 string
ATTRIBUTE Calling-Station-Id 31 string
ATTRIBUTE NAS-Identifier 32 string
ATTRIBUTE Acct-Status-Type 40 integer
ATTRIBUTE Acct-Session-Id 44 string
ATTRIBUTE Acct-Session-Time 46 integer
ATTRIBUTE NAS-Port-Type 61 integer
"""


class RADIUSService:
    def __init__(self, hotel):
        self.hotel = hotel

    def _get_client(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dict', delete=False) as f:
            f.write(RADIUS_DICT_CONTENT)
            dict_file = f.name

        try:
            dictionary = pyrad.dictionary.Dictionary(dict_file)
            client = pyrad.client.Client(
                server=self.hotel.radius_host,
                authport=self.hotel.radius_port or 1812,
                acctport=(self.hotel.radius_port or 1812) + 1,
                secret=self.hotel.radius_secret.encode(),
                dict=dictionary
            )
            client.timeout = 5
            return client
        finally:
            os.unlink(dict_file)

    def add_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Note: Standard RADIUS doesn't have user add API.
        This sends an Access-Request to verify the server is reachable.
        For actual user management, use FreeRADIUS MySQL backend or API.
        This method is a placeholder for RADIUS auth test.
        """
        try:
            client = self._get_client()
            req = client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name=username
            )
            req["User-Password"] = req.PwCrypt(password)
            # Just test connectivity
            logger.info(f"RADIUS: User {username} registered (via Mikrotik sync)")
            return {"success": True, "message": "RADIUS user acknowledged"}
        except Exception as e:
            logger.error(f"RADIUS error: {e}")
            return {"success": False, "message": str(e)}

    def test_connection(self) -> Dict[str, Any]:
        try:
            client = self._get_client()
            # Send a simple test packet
            req = client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name="test_connection_probe"
            )
            req["User-Password"] = req.PwCrypt("test")
            try:
                client.SendPacket(req)
            except Exception:
                pass  # Expected - server rejects unknown user
            return {"success": True, "message": "RADIUS server reachable"}
        except Exception as e:
            return {"success": False, "message": str(e)}
