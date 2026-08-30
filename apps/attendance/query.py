from typing import Optional

from apps.attendance.models import DailyAttendanceLog, Device, DeviceAttendanceLog


def get_all_device():
    return Device.objects.all()


def get_or_create_device(serial: str, name: str, ip_address: str, port: int = 4370) -> Device:
    device, created = Device.objects.get_or_create(
        serial=serial,
        defaults={
            "name": name,
            "ip_address": ip_address,
            "port": port,
        },
    )
    return device, created


def get_device_by_serial(serial: str) -> Optional[Device]:
    try:
        return Device.objects.get(serial=serial)
    except Device.DoesNotExist:
        return None


def get_device_attendance_log(device_serial: str, device_user_id: str, punch_time) -> Optional[DeviceAttendanceLog]:
    try:
        return DeviceAttendanceLog.objects.get(
            device_serial=device_serial,
            device_user_id=device_user_id,
            punch_time=punch_time,
        )
    except DeviceAttendanceLog.DoesNotExist:
        return None
