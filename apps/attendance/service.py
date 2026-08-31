from collections import defaultdict
from datetime import datetime

from django.db import transaction
from rest_framework import status
from zk import ZK
from zk.exception import ZKErrorConnection, ZKErrorResponse

from apps.attendance.models import (
    DailyAttendanceLog,
    Device,
    DeviceAttendanceLog,
    Policy,
    StatusChoices,
    SyncState,
)
from apps.base.exception import HTTPException
from apps.user.models import Employee

LATE_THRESHOLD_HOUR = 9
LATE_THRESHOLD_MINUTE = 15


class ZKDeviceService:

    @staticmethod
    def _connect(device: Device):
        if not device.is_active:
            return {
                "success": False,
                "message": f"ZKTeco device '{device.name}' is inactive",
            }

        zk = ZK(
            device.ip_address,
            port=device.port,
            timeout=5,
        )

        try:
            connection = zk.connect()

            return {
                "success": True,
                "device": zk,
                "connection": connection,
            }

        except ZKErrorConnection as e:
            return {
                "success": False,
                "message": f"Cannot connect to attendance device '{device.name}' ({device.ip_address}:{device.port}): {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect to device '{device.name}': {e}",
            }

    @staticmethod
    def sync_employee_to_device(user, device: Device = None):
        """Register / sync employee to a specific device or all active devices."""
        if device is not None:
            devices = [device]
        else:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:

                return {
                    "success": False,
                    "message": "No active attendance devices configured",
                    "synced_devices": [],
                }

        synced_device_names = []

        for dev in devices:
            result = ZKDeviceService._connect(dev)

            if not result["success"]:
                return result

            connection = result["connection"]

            try:
                connection.disable_device()

                connection.set_user(
                    name=user.username,
                    privilege=0,
                    password="",
                    group_id="",
                    user_id=str(user.employee_id),
                )

                user.zk_device_user_id = str(user.employee_id)
                synced_device_names.append(dev.name)

            except ZKErrorResponse as e:
                raise HTTPException(
                    detail=f"Device '{dev.name}' error: {e}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            except Exception as e:
                raise HTTPException(
                    detail=f"Sync failed for device '{dev.name}': {e}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            finally:
                try:
                    connection.enable_device()
                except Exception:
                    pass

                try:
                    connection.disconnect()
                except Exception:
                    pass

        return {
            "success": True,
            "message": f"Employee {user.username} synced to device(s)",
            "synced_devices": synced_device_names,
        }

    @staticmethod
    def _pull_attendance_from_device(device: Device):
        result = ZKDeviceService._connect(device)

        if not result["success"]:
            return result

        connection = result["connection"]
        try:
            attendances = connection.get_attendance()
            device_serial = connection.get_serialnumber() or device.serial
            new_attendance = AttendanceService.save_attendance(attendances, device_serial)

            return {
                "success": True,
                "new_attendance": new_attendance,
                "device_serial": device_serial,
                "device_name": device.name,
            }

        except ZKErrorResponse as e:
            raise HTTPException(
                detail=f"Device '{device.name}' error: {e}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            raise HTTPException(
                detail=f"Failed to pull attendance from device '{device.name}': {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            try:
                connection.disconnect()
            except Exception:
                pass


class AttendanceService:
    @staticmethod
    def save_attendance(attendances, device_serial):
        if attendances is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Attendance instance cannot be None",
            )

        sync_state, created = SyncState.objects.get_or_create(
            device_serial=device_serial,
            defaults={"last_synced_at": None},
        )

        if not attendances:
            sync_state.last_run_at = datetime.now()
            sync_state.save(update_fields=["last_run_at"])
            return []

        new_attendance = []
        for attendance in attendances:
            if sync_state.last_synced_at is None or attendance.punch_time > sync_state.last_synced_at:
                new_attendance.append(
                    DeviceAttendanceLog(
                        device_serial=device_serial,
                        device_user_id=attendance.user_id,
                        punch_time=attendance.timestamp,
                        status=attendance.status,
                        punch=attendance.punch,
                    )
                )

        with transaction.atomic():
            if new_attendance:
                DeviceAttendanceLog.objects.bulk_create(new_attendance, ignore_conflicts=True)
                AttendanceService._process_daily_attendance_save(new_attendance)
                sync_state.last_synced_at = max(att.punch_time for att in new_attendance)

            sync_state.last_run_at = datetime.now()

            sync_state.save(update_fields=["last_synced_at", "last_run_at"])
        return new_attendance

    @staticmethod
    def _process_daily_attendance_save(attendances):

        # Get the POlicy of company for calculation check in checkout Time.
        policy = Policy.objects.first()
        if not policy:
            return {"success": False, "message": "Policy for check_in and check_out not configured in DB"}

        # Get all the employees data when new raw attendance logs has been found.
        employees = Employee.objects.filter(employee_id__in=[data.device_user_id for data in attendances])

        # Employee mapper that maps employee_id to an employee object
        employee_mapper = {emp.employee_id: emp for emp in employees}

        # DailyAttendance = DailyAttendanceLog.objects.filter(
        #     date__in=[attendances.punch_time.date()], employee_id__in=[data.device_user_id for data in attendances]
        # )
        # daily_attendance_mapper = {(daily.employee_id, daily.log_date): daily for daily in DailyAttendance}

        # Build the mapper based group aggregation between (user_id, punch date) which returns lists of attendances for specific user_id and date
        employee_att = defaultdict(list)
        for data in attendances:
            employee_att[(data.device_user_id, data.punch_time.date())].append(data)

        # Build daily attendance mapper
        # Example = {
        #     (101, date(2026, 8, 31)): daily_attendance_object_1,
        #      ....
        # }
        # daily_attendance_mapper = {}

        for (employee_id, _), attendance_list in employee_att.items():
            employee = employee_mapper.get(employee_id)

            if employee is None:
                continue

            # fetch the latest and oldest punch where oldest is assumed as  check-in and latest as check-out
            # check_in_time = min(data.punch_time for data in attendances)
            # check_out_time = max(data.punch_time for data in attendances)
            # total_hours_worked = 0
            for _ in attendance_list:
                pass
