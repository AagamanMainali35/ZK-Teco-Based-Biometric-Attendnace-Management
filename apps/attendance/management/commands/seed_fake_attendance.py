import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import models, transaction

from apps.attendance.models import (
    DailyAttendanceLog,
    Device,
    DeviceAttendanceLog,
    Policy,
)
from apps.attendance.service import AttendanceService
from apps.user.models import Employee


class Command(BaseCommand):
    help = "Generate realistic fake attendance punches (70% Present, 25% Half Day, 5% Absent) and process daily logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of past days to generate attendance for (default: 30)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=True,
            help="Clear existing DeviceAttendanceLog and DailyAttendanceLog before seeding (default: True)",
        )
        parser.add_argument(
            "--device-serial",
            type=str,
            default="ZK-DEV-001",
            help="Device serial number to associate with logs (default: ZK-DEV-001)",
        )

    def handle(self, *args, **options):
        days_count = options["days"]
        clear = options["clear"]
        device_serial = options["device_serial"]

        # Ensure device exists
        device, _ = Device.objects.get_or_create(
            serial=device_serial,
            defaults={
                "name": "Main Entrance Biometric",
                "ip_address": "192.168.1.201",
                "port": 4370,
                "is_active": True,
            },
        )

        # Ensure policy exists (10:00 AM - 6:00 PM, 4.0h half-day threshold)
        policy = Policy.objects.first()
        if not policy:
            policy = Policy.objects.create(
                name="Standard 10-6 Policy",
                check_in_time="10:00:00",
                check_out_time="18:00:00",
                late_threshold_minutes=15,
                half_day_threshold_hours=Decimal("4.00"),
                full_day_hours=Decimal("8.00"),
            )
        else:
            policy.check_in_time = "10:00:00"
            policy.check_out_time = "18:00:00"
            policy.half_day_threshold_hours = Decimal("4.00")
            policy.full_day_hours = Decimal("8.00")
            policy.save()

        employees = list(Employee.objects.filter(is_active=True).exclude(employee_id=""))
        if not employees:
            self.stdout.write(self.style.ERROR("No active employees found in DB. Please run 'python manage.py seed_fake_employees' first."))
            return

        if clear:
            self.stdout.write(self.style.NOTICE("--- Clearing old attendance logs ---"))
            del_daily, _ = DailyAttendanceLog.objects.all().delete()
            del_raw, _ = DeviceAttendanceLog.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {del_raw} raw logs and {del_daily} daily logs."))

        self.stdout.write(self.style.NOTICE(f"--- Generating attendance for {len(employees)} employees over past {days_count} days ---"))

        today = datetime.now().date()
        raw_punches = []

        present_target_count = 0
        half_day_target_count = 0
        absent_target_count = 0

        for day_offset in range(days_count, 0, -1):
            log_date = today - timedelta(days=day_offset)

            # Skip weekends (Saturday=5, Sunday=6)
            if log_date.weekday() >= 5:
                continue

            for emp in employees:
                uid = emp.zk_device_user_id or str(emp.employee_id)

                # Distribution roll: 70% Present, 25% Half Day, 5% Absent
                roll = random.random() * 100

                if roll < 70:
                    # 70% PRESENT (Worked 7.5 - 8.5 hours >= 4.0h)
                    present_target_count += 1

                    # Check-in between 09:45:00 and 10:15:00
                    in_minute = random.randint(45, 75)  # 09:45 (45) to 10:15 (75)
                    in_sec = random.randint(0, 59)
                    in_dt = datetime.combine(log_date, time(9, 0)) + timedelta(minutes=in_minute, seconds=in_sec)

                    # Check-out between 17:30:00 and 18:20:00
                    out_minute = random.randint(30, 80)  # 17:30 (30) to 18:20 (80)
                    out_sec = random.randint(0, 59)
                    out_dt = datetime.combine(log_date, time(17, 0)) + timedelta(minutes=out_minute, seconds=out_sec)

                    raw_punches.append(
                        DeviceAttendanceLog(
                            device_serial=device.serial,
                            device_user_id=uid,
                            punch_time=in_dt,
                            status=0,
                            punch=0,
                        )
                    )
                    raw_punches.append(
                        DeviceAttendanceLog(
                            device_serial=device.serial,
                            device_user_id=uid,
                            punch_time=out_dt,
                            status=0,
                            punch=1,
                        )
                    )

                elif roll < 95:
                    # 25% HALF DAY (Worked 2.0 - 3.5 hours < 4.0h threshold)
                    half_day_target_count += 1

                    # Check-in between 09:50:00 and 10:10:00
                    in_minute = random.randint(50, 70)
                    in_sec = random.randint(0, 59)
                    in_dt = datetime.combine(log_date, time(9, 0)) + timedelta(minutes=in_minute, seconds=in_sec)

                    # Check-out between 12:30:00 and 13:30:00 (Worked ~2.5 - 3.5 hrs)
                    out_minute = random.randint(30, 90)  # 12:30 to 13:30
                    out_sec = random.randint(0, 59)
                    out_dt = datetime.combine(log_date, time(12, 0)) + timedelta(minutes=out_minute, seconds=out_sec)

                    raw_punches.append(
                        DeviceAttendanceLog(
                            device_serial=device.serial,
                            device_user_id=uid,
                            punch_time=in_dt,
                            status=0,
                            punch=0,
                        )
                    )
                    raw_punches.append(
                        DeviceAttendanceLog(
                            device_serial=device.serial,
                            device_user_id=uid,
                            punch_time=out_dt,
                            status=0,
                            punch=1,
                        )
                    )

                else:
                    # 5% ABSENT (Single punch / missed checkout or < 1 hr)
                    absent_target_count += 1
                    in_minute = random.randint(50, 75)
                    in_dt = datetime.combine(log_date, time(9, 0)) + timedelta(minutes=in_minute, seconds=random.randint(0, 59))
                    raw_punches.append(
                        DeviceAttendanceLog(
                            device_serial=device.serial,
                            device_user_id=uid,
                            punch_time=in_dt,
                            status=0,
                            punch=0,
                        )
                    )

        # Bulk insert raw logs
        with transaction.atomic():
            DeviceAttendanceLog.objects.bulk_create(raw_punches, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"Generated {len(raw_punches)} raw punch records!"))

        # Process into DailyAttendanceLog
        self.stdout.write(self.style.NOTICE("--- Processing Daily Attendance Records ---"))
        result = AttendanceService._process_daily_attendance_save(raw_punches)
        self.stdout.write(self.style.SUCCESS(f"Processing Result: {result}"))

        # Print final distribution report
        total_daily = DailyAttendanceLog.objects.count()
        present_count = DailyAttendanceLog.objects.filter(status="present").count()
        half_day_count = DailyAttendanceLog.objects.filter(status="half_day").count()
        absent_count = DailyAttendanceLog.objects.filter(models.Q(status__isnull=True) | models.Q(status="absent")).count()

        p_pct = (present_count / total_daily * 100) if total_daily else 0
        h_pct = (half_day_count / total_daily * 100) if total_daily else 0
        a_pct = (absent_count / total_daily * 100) if total_daily else 0

        self.stdout.write(self.style.NOTICE("\n--- Final Attendance Distribution ---"))
        self.stdout.write(self.style.SUCCESS(f"Total Working Days Logged: {total_daily}"))
        self.stdout.write(self.style.SUCCESS(f"  • Present:   {present_count:>4} ({p_pct:.1f}%) [Target ~70%]"))
        self.stdout.write(self.style.SUCCESS(f"  • Half Day:  {half_day_count:>4} ({h_pct:.1f}%) [Target ~25%]"))
        self.stdout.write(self.style.SUCCESS(f"  • Absent:    {absent_count:>4} ({a_pct:.1f}%) [Target ~5%]"))
