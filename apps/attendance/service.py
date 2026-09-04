from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Union

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
from apps.attendance.query import (
    get_or_create_device,
    get_attendance_records
)
from apps.base.exception import HTTPException
from apps.user.models import Employee


class ZKDeviceService:

    @staticmethod
    def _connect(device: Device):
        if not device.is_active:
            return {"success": False, "message": f"ZKTeco device '{device.name}' is inactive"}

        zk = ZK(device.ip_address, port=device.port, timeout=5)
        try:
            connection = zk.connect()
            return {"success": True, "device": zk, "connection": connection}
        except ZKErrorConnection as e:
            return {
                "success": False,
                "message": f"Cannot connect to attendance device '{device.name}' ({device.ip_address}:{device.port}): {e}",
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to connect to device '{device.name}': {e}"}

    @staticmethod
    def test_connection(device: Device):
        return ZKDeviceService._connect(device)

    @staticmethod
    def sync_employee_to_device(
        user: Employee,
        devices: Optional[Union[Device, List[Device]]] = None,
    ):
        """Register / sync employee to a specific device, list of devices, or all active devices."""
        if devices is None:
            target_devices = list(Device.objects.filter(is_active=True))
        elif isinstance(devices, list):
            target_devices = devices
        else:
            target_devices = [devices]

        if not target_devices:
            return {
                "success": False,
                "message": "No active attendance devices configured",
                "synced_devices": [],
                "failed_devices": [],
            }

        synced_device_names = []
        failed_devices = []

        for dev in target_devices:
            result = ZKDeviceService._connect(dev)
            if not result["success"]:
                failed_devices.append({"device": dev.name, "serial": dev.serial, "error": result["message"]})
                continue

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
                failed_devices.append({"device": dev.name, "serial": dev.serial, "error": f"ZK error: {e}"})
            except Exception as e:
                failed_devices.append({"device": dev.name, "serial": dev.serial, "error": str(e)})
            finally:
                try:
                    connection.enable_device()
                    connection.disconnect()
                except Exception:
                    pass

        if not synced_device_names:
            error_details = "; ".join([f"{f['device']}: {f['error']}" for f in failed_devices])
            return {
                "success": False,
                "message": f"Failed to sync to device(s): {error_details}",
                "synced_devices": [],
                "failed_devices": failed_devices,
            }

        return {
            "success": True,
            "message": (
                f"Employee {user.username} synced to device(s)"
                if not failed_devices
                else f"Employee {user.username} partially synced ({len(synced_device_names)} succeeded, {len(failed_devices)} failed)"
            ),
            "synced_devices": synced_device_names,
            "failed_devices": failed_devices,
        }

    @staticmethod
    def _pull_attendance_from_device(device: Device):
        """Pull raw attendance logs from a specific ZK device."""
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
                "records_pulled": len(new_attendance),
                "device_serial": device_serial,
                "device_name": device.name,
            }
        except ZKErrorResponse as e:
            raise HTTPException(detail=f"Device '{device.name}' error: {e}", status_code=status.HTTP_400_BAD_REQUEST)
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

    @staticmethod
    def pull_attendance_from_device(device: Device):
        return ZKDeviceService._pull_attendance_from_device(device)

    @staticmethod
    def pull_attendance_from_all_active_devices():
        results = []
        for dev in Device.objects.filter(is_active=True):
            try:
                results.append({"device": dev.name, "serial": dev.serial, "result": ZKDeviceService.pull_attendance_from_device(dev)})
            except Exception as e:
                results.append({"device": dev.name, "serial": dev.serial, "success": False, "error": str(e)})
        return results


class AttendanceService:

    @staticmethod
    def save_attendance(attendances, device_serial: str) -> List[DeviceAttendanceLog]:
        if attendances is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Attendance instance cannot be None",
            )

        sync_state, _ = SyncState.objects.get_or_create(device_serial=device_serial)

        if not attendances:
            sync_state.last_run_at = datetime.now()
            sync_state.save(update_fields=["last_run_at"])
            return []

        new_attendance = [
            DeviceAttendanceLog(
                device_serial=device_serial,
                device_user_id=str(att.user_id),
                punch_time=att.timestamp,
                status=att.status,
                punch=att.punch,
            )
            for att in attendances
            if sync_state.last_synced_at is None or att.timestamp > sync_state.last_synced_at
        ]

        with transaction.atomic():
            if new_attendance:
                DeviceAttendanceLog.objects.bulk_create(new_attendance, ignore_conflicts=True)
                AttendanceService._process_daily_attendance_save(new_attendance)
                sync_state.last_synced_at = max(att.punch_time for att in new_attendance)

            sync_state.last_run_at = datetime.now()
            sync_state.save(update_fields=["last_synced_at", "last_run_at"])

        return new_attendance

    @staticmethod
    def process_stats(log: DailyAttendanceLog, policy: Policy) -> DailyAttendanceLog:
        if not log.check_in_time:
            return log

        log.is_late = log.check_in_time > datetime.combine(log.date, policy.check_in_time) + timedelta(minutes=policy.late_threshold_minutes)
        expected_check_out = datetime.combine(log.date, policy.check_out_time)

        if not log.check_out_time or log.check_out_time <= log.check_in_time:
            log.total_hours = Decimal("0.00")
            log.is_early_leave = False
            log.early_leave_minutes = 0
            log.status = StatusChoices.ABSENT
            return log

        hours_worked = Decimal(str(round((log.check_out_time - log.check_in_time).total_seconds() / 3600, 2)))
        log.total_hours = hours_worked

        log.is_early_leave = log.check_out_time < expected_check_out
        log.early_leave_minutes = max(0, int((expected_check_out - log.check_out_time).total_seconds() // 60)) if log.is_early_leave else 0

        if hours_worked < policy.half_day_threshold_hours:
            log.status = StatusChoices.HALF_DAY
        else:
            log.status = StatusChoices.PRESENT

        return log

    @staticmethod
    def _process_daily_attendance_save(raw_attendance: List[DeviceAttendanceLog]):
        policy = Policy.objects.first()
        if not policy:
            return {"success": False, "message": "Policy for check_in and check_out not configured in DB"}

        employees = Employee.objects.filter(employee_id__in=[data.device_user_id for data in raw_attendance])
        employee_mapper = {emp.employee_id: emp for emp in employees}

        daily_attendance_logs = DailyAttendanceLog.objects.filter(
            date__in=[data.punch_time.date() for data in raw_attendance],
            employee__employee_id__in=[data.device_user_id for data in raw_attendance],
        ).select_related("employee")
        daily_attendance_mapper = {(daily.employee.employee_id, daily.date): daily for daily in daily_attendance_logs}

        grouped_attendance = defaultdict(list)
        for data in raw_attendance:
            grouped_attendance[(data.device_user_id, data.punch_time.date())].append(data)

        new_logs, updated_logs = [], []

        for (employee_id, date), punches in grouped_attendance.items():
            employee = employee_mapper.get(employee_id)
            if not employee:
                continue

            log = daily_attendance_mapper.get((employee_id, date))
            is_new = log is None

            punch_times = [p.punch_time for p in punches]

            if is_new:
                check_in = min(punch_times)
                check_out = max(punch_times) if len(punch_times) > 1 else None
                log = DailyAttendanceLog(employee=employee, date=date, check_in_time=check_in, check_out_time=check_out)
            else:
                log.check_out_time = max(filter(None, [log.check_out_time] + punch_times))

            log = AttendanceService.process_stats(log, policy)
            (new_logs if is_new else updated_logs).append(log)

        if new_logs:
            DailyAttendanceLog.objects.bulk_create(new_logs)
        if updated_logs:
            DailyAttendanceLog.objects.bulk_update(
                updated_logs,
                [
                    "check_in_time",
                    "check_out_time",
                    "total_hours",
                    "status",
                    "is_late",
                    "is_early_leave",
                    "early_leave_minutes",
                ],
            )

        return {"success": True, "new_logs": len(new_logs), "updated_logs": len(updated_logs)}

    @staticmethod
    def get_attendance(employee_id: Optional[str] = None):
        if not employee_id:
            raise HTTPException(detail="Invalid employee_id provided.", status_code=status.HTTP_400_BAD_REQUEST)
        result = get_attendance_records(employee_id)
        if result is None:
            raise HTTPException(detail=f"Employee with ID '{employee_id}' not found.", status_code=status.HTTP_404_NOT_FOUND)
        return result

    

class DeviceService:
    @staticmethod
    def register_device(device_data: dict) -> Device:
        device, create = get_or_create_device(
            serial=device_data.get("serial"),
            name=device_data.get("name"),
            ip_address=device_data.get("ip_address"),
            port=device_data.get("port", 4370),
        )

        if not create:
            raise HTTPException(detail=f"Device with serial '{device.serial}' already exists.", status_code=status.HTTP_400_BAD_REQUEST)
        return device

    @staticmethod
    def update_device(device: Device, device_data: dict) -> Device:
        for field in ["name", "ip_address", "port", "is_active"]:
            if field in device_data:
                setattr(device, field, device_data[field])
        device.save(update_fields=["name", "ip_address", "port", "is_active"])
        return device

    @staticmethod
    def deactivate_device(device: Device):
        if not device.is_active:
            raise HTTPException(detail=f"Device '{device.name}' is already inactive.", status_code=status.HTTP_400_BAD_REQUEST)
        device.is_active = False
        device.save(update_fields=["is_active"])
        return device

    @staticmethod
    def delete_device(device: Device):
        if device.is_active:
            raise HTTPException(
                detail=f"Cannot delete active device '{device.name}'. Please deactivate it first.", status_code=status.HTTP_400_BAD_REQUEST
            )
        device.delete()
        return {"success": True, "message": f"Device '{device.name}' deleted successfully."}
