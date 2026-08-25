from decouple import config
from rest_framework import status
from zk import ZK
from zk.exception import ZKErrorConnection, ZKErrorResponse

from apps.base.exception import HTTPException

DEVICE_IP = config("ZK_DEVICE_IP", default="192.168.1.201")
DEVICE_PORT = config("ZK_DEVICE_PORT", default=4370)

LATE_THRESHOLD_HOUR = 9
LATE_THRESHOLD_MINUTE = 15


class ZKDeviceService:

    @staticmethod
    def sync_employee_to_device(user):
        """
        Sync a single employee to the ZKTeco device.

        Creates user record on the device.
        """
        device = ZK("192.168.1.201", port=4370, timeout=5)

        try:
            conn = device.connect()
            print("Connected to device at 192.168.1.201")

            try:
                conn.disable_device()
                conn.set_user(
                    uid=user.employee_id,
                    name=user.username,
                    privilege=0,
                    password="",
                    group_id="",
                    user_id=str(user.employee_id),
                )
                print(f"User {user.username} added to device")
                user.zk_device_user_id = str(user.employee_id)
                print(f"Local database updated for {user.username}")

                return {"success": True, "message": f"Employee {user.username} synced to device"}

            except ZKErrorResponse as e:
                # Handle device-specific errors
                raise HTTPException(
                    detail=f"Device error: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                # Handle unexpected errors
                raise HTTPException(
                    detail=f"Sync failed: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            finally:
                # 6. ALWAYS re-enable device
                try:
                    conn.enable_device()
                    print("Device re-enabled")
                except Exception:
                    print("Warning: Could not re-enable device")

        except ZKErrorConnection as e:
            raise HTTPException(
                detail=f"Cannot connect to attendance device: {str(e)}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        finally:
            try:
                conn.disconnect()
                print("Disconnected from device")
            except Exception:
                print("Warning: Could not disconnect properly")
