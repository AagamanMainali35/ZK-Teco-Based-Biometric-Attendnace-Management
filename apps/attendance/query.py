from typing import Optional

from apps.attendance.models import (
    DailyAttendanceLog,
    Device,
    DeviceAttendanceLog,
    SyncState,
)


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


def get_device_sync_state(device_serial: str) -> Optional[SyncState]:
    try:
        return SyncState.objects.get(device_serial=device_serial)
    except SyncState.DoesNotExist:
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


def get_devices_with_sync_state(serial: Optional[str] = None):
    devices = Device.objects.all()
    if serial:
        devices = devices.filter(serial=serial)

    device_serials = [d.serial for d in devices]
    sync_states = {s.device_serial: s for s in SyncState.objects.filter(device_serial__in=device_serials)}

    results = []
    for device in devices:
        sync = sync_states.get(device.serial)
        results.append(
            {
                "serial": device.serial,
                "name": device.name,
                "ip_address": device.ip_address,
                "port": device.port,
                "is_active": device.is_active,
                "last_synced_at": sync.last_synced_at if sync else None,
                "last_run_at": sync.last_run_at if sync else None,
            }
        )
    return results
