import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.attendance.models import DeviceAttendanceLog

EMPLOYEES = {
    "emp_1": {"name": "Aayush Shrestha", "id": 1, "device_user_id": "emp_0001"},
    "emp_2": {"name": "Bibek Sharma", "id": 2, "device_user_id": "emp_0002"},
    "emp_3": {"name": "Pratima Adhikari", "id": 3, "device_user_id": "emp_0003"},
    "emp_4": {"name": "Sujan Poudel", "id": 4, "device_user_id": "emp_0004"},
    "emp_5": {"name": "Rita Khanal", "id": 5, "device_user_id": "emp_0005"},
    "emp_6": {"name": "Kiran Thapa", "id": 6, "device_user_id": "emp_0006"},
    "emp_7": {"name": "Sita Gurung", "id": 7, "device_user_id": "emp_0007"},
    "emp_8": {"name": "Hari Rana", "id": 8, "device_user_id": "emp_0008"},
    "emp_9": {"name": "Gita Karki", "id": 9, "device_user_id": "emp_0009"},
    "emp_10": {"name": "Ramesh Bhandari", "id": 10, "device_user_id": "emp_0010"},
    "emp_11": {"name": "Sunita Tamang", "id": 11, "device_user_id": "emp_0011"},
    "emp_12": {"name": "Krishna Mahato", "id": 12, "device_user_id": "emp_0012"},
    "emp_13": {"name": "Nisha Shahi", "id": 13, "device_user_id": "emp_0013"},
    "emp_14": {"name": "Rajesh Ghimire", "id": 14, "device_user_id": "emp_0014"},
    "emp_15": {"name": "Maya Rai", "id": 15, "device_user_id": "emp_0015"},
    "emp_16": {"name": "Dipak Regmi", "id": 16, "device_user_id": "emp_0016"},
    "emp_17": {"name": "Laxmi Pandey", "id": 17, "device_user_id": "emp_0017"},
    "emp_18": {"name": "Bishal Nepal", "id": 18, "device_user_id": "emp_0018"},
    "emp_19": {"name": "Saraswati Aryal", "id": 19, "device_user_id": "emp_0019"},
    "emp_20": {"name": "Manish Bhattarai", "id": 20, "device_user_id": "emp_0020"},
    "emp_21": {"name": "Usha Dhakal", "id": 21, "device_user_id": "emp_0021"},
    "emp_22": {"name": "Prakash Oli", "id": 22, "device_user_id": "emp_0022"},
    "emp_23": {"name": "Kalpana Chhetri", "id": 23, "device_user_id": "emp_0023"},
    "emp_24": {"name": "Suresh Subedi", "id": 24, "device_user_id": "emp_0024"},
    "emp_25": {"name": "Indira Joshi", "id": 25, "device_user_id": "emp_0025"},
}


class Command(BaseCommand):
    help = "Generate raw attendance logs for development"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--device", type=str, default="K40-TEST-001")
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        days = options["days"]
        device_serial = options["device"]

        if options["clear"]:
            deleted, _ = DeviceAttendanceLog.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing raw attendance logs.")

        now = timezone.localtime()
        start_date = now.date() - timedelta(days=days - 1)

        logs = []

        for employee in EMPLOYEES.values():
            for day_offset in range(days):
                current_date = start_date + timedelta(days=day_offset)

                if current_date.weekday() >= 5:
                    continue

                attendance_type = random.choices(
                    ["normal", "late", "early_leave", "missing_checkout", "absent"],
                    weights=[75, 10, 5, 3, 7],
                    k=1,
                )[0]

                if attendance_type == "absent":
                    continue

                check_in_minutes = random.randint(-5, 10)

                if attendance_type == "late":
                    check_in_minutes = random.randint(20, 90)

                check_in = datetime.combine(
                    current_date,
                    time(9, 0),
                ) + timedelta(minutes=check_in_minutes, seconds=random.randint(0, 59))

                logs.append(
                    DeviceAttendanceLog(
                        device_serial=device_serial,
                        device_user_id=employee["device_user_id"],
                        punch_time=check_in,
                        punch=0,
                        status=1,
                    )
                )

                if attendance_type == "missing_checkout":
                    continue

                check_out_minutes = random.randint(-15, 30)

                if attendance_type == "early_leave":
                    check_out_minutes = random.randint(-120, -30)

                check_out = datetime.combine(
                    current_date,
                    time(17, 0),
                ) + timedelta(minutes=check_out_minutes, seconds=random.randint(0, 59))

                logs.append(
                    DeviceAttendanceLog(
                        device_serial=device_serial,
                        device_user_id=employee["device_user_id"],
                        punch_time=check_out,
                        punch=1,
                        status=1,
                    )
                )

        DeviceAttendanceLog.objects.bulk_create(logs, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Created {len(logs)} raw attendance logs for {len(EMPLOYEES)} employees over {days} days."))
