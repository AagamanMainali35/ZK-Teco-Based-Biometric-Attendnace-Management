from decouple import config
from rest_framework import status
from zk import ZK
from zk.exception import ZKErrorConnection, ZKErrorResponse

from apps.base.exception import HTTPException

DEVICE_IP = config("ZK_DEVICE_IP", default="192.168.1.201")
DEVICE_PORT = config("ZK_DEVICE_PORT", default=4370, cast=int)
ZK_DEVICE_ENABLED = config("ZK_DEVICE_ENABLED", default=False, cast=bool)
LATE_THRESHOLD_HOUR = 9
LATE_THRESHOLD_MINUTE = 15


class ZKDeviceService:

    @staticmethod
    def _connect():
        if not ZK_DEVICE_ENABLED:
            return {
                "success": False,
                "message": "ZKTeco device sync disabled",
            }

        device = ZK(
            DEVICE_IP,
            port=DEVICE_PORT,
            timeout=5,
        )

        try:
            connection = device.connect()

            return {
                "success": True,
                "device": device,
                "connection": connection,
            }

        except ZKErrorConnection as e:
            return {
                "success": False,
                "message": f"Cannot connect to attendance device: {e}",
            }

    @staticmethod
    def sync_employee_to_device(user):
        result = ZKDeviceService._connect()

        if not result["success"]:
            return result

        connection = result["connection"]

        try:
            connection.disable_device()

            connection.set_user(
                uid=user.employee_id,
                name=user.username,
                privilege=0,
                password="",
                group_id="",
                user_id=str(user.employee_id),
            )

            user.zk_device_user_id = str(user.employee_id)
            user.save(update_fields=["zk_device_user_id"])

            return {
                "success": True,
                "message": f"Employee {user.username} synced to device",
            }

        except ZKErrorResponse as e:
            raise HTTPException(
                detail=f"Device error: {e}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            raise HTTPException(
                detail=f"Sync failed: {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            try:
                connection.enable_device()
            except Exception:
                ...

            try:
                connection.disconnect()
            except Exception:
                pass

    @staticmethod
    def pull_attendance():
        result = ZKDeviceService._connect()

        if not result["success"]:
            return result

        connection = result["connection"]

        try:
            attendances = connection.get_attendance()

            return {
                "success": True,
                "data": attendances,
            }

        except ZKErrorResponse as e:
            raise HTTPException(
                detail=f"Device error: {e}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            raise HTTPException(
                detail=f"Failed to pull attendance: {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            try:
                connection.disconnect()
            except Exception:
                pass
