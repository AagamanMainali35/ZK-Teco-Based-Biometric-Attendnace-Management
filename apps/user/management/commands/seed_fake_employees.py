from django.core.management.base import BaseCommand
from django.db import transaction

from apps.attendance.models import DailyAttendanceLog, DeviceAttendanceLog
from apps.attendance.service import AttendanceService
from apps.user.models import Employee

SAMPLE_EMPLOYEES = [
    ("Aarav", "Sharma"),
    ("Diya", "Patel"),
    ("Rohan", "Verma"),
    ("Ananya", "Iyer"),
    ("Kabir", "Mehta"),
    ("Pooja", "Joshi"),
    ("Vikram", "Singh"),
    ("Sneha", "Kulkarni"),
    ("Arjun", "Nair"),
    ("Neha", "Reddy"),
    ("Rahul", "Gupta"),
    ("Priya", "Choudhury"),
    ("Aditya", "Rao"),
    ("Ishita", "Bose"),
    ("Karan", "Malhotra"),
    ("Meera", "Menon"),
    ("Siddharth", "Das"),
    ("Tanvi", "Saxena"),
    ("Varun", "Kapoor"),
    ("Rhea", "Sen"),
    ("Manish", "Pandey"),
    ("Kavita", "Deshmukh"),
    ("Nikhil", "Bhatia"),
    ("Shruti", "Mishra"),
    ("Gaurav", "Thakur"),
]


class Command(BaseCommand):
    help = "Seed fake employees matching DeviceAttendanceLog device_user_ids and process daily attendance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=25,
            help="Number of employees to seed if no raw logs are found",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="Password@123",
            help="Default password for seeded employees",
        )
        parser.add_argument(
            "--no-attendance-process",
            action="store_true",
            help="Skip processing DailyAttendanceLog after seeding employees",
        )

    def handle(self, *args, **options):
        password = options["password"]
        skip_process = options["no_attendance_process"]

        # Discover all unique device_user_ids from raw attendance logs
        raw_user_ids = list(DeviceAttendanceLog.objects.values_list("device_user_id", flat=True).distinct().order_by("device_user_id"))

        if not raw_user_ids:
            count = options["count"]
            raw_user_ids = [str(1001 + i) for i in range(count)]
            self.stdout.write(self.style.WARNING(f"No raw attendance logs found. Generating default IDs: {raw_user_ids[0]}..{raw_user_ids[-1]}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Found {len(raw_user_ids)} unique device user IDs in DeviceAttendanceLog: {raw_user_ids}"))

        self.stdout.write(self.style.NOTICE("--- Seeding Employees ---"))
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for idx, uid in enumerate(raw_user_ids):
                sample_idx = idx % len(SAMPLE_EMPLOYEES)
                first_name, last_name = SAMPLE_EMPLOYEES[sample_idx]
                username = f"{first_name.lower()}.{last_name.lower()}{uid}"
                email = f"{first_name.lower()}.{last_name.lower()}{uid}@company.com"

                employee = Employee.objects.filter(employee_id=uid).first()
                if not employee:
                    if Employee.objects.filter(username=username).exists():
                        username = f"emp_{uid}"
                    if Employee.objects.filter(email=email).exists():
                        email = f"emp_{uid}@lioris.ai"

                    employee = Employee.objects.create(
                        username=username,
                        employee_id=str(uid),
                        zk_device_user_id=str(uid),
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        is_active=True,
                    )
                    employee.set_password(password)
                    employee.save()
                    created_count += 1
                else:
                    employee.zk_device_user_id = str(uid)
                    if not employee.email:
                        employee.email = email
                    employee.save(update_fields=["zk_device_user_id", "email"])
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded employees! (Created: {created_count}, Updated: {updated_count}, Default Password: '{password}')"
            )
        )

        if not skip_process:
            self.stdout.write(self.style.NOTICE("--- Processing Daily Attendance Logs ---"))
            raw_logs = list(DeviceAttendanceLog.objects.all())
            if raw_logs:
                result = AttendanceService._process_daily_attendance_save(raw_logs)
                daily_count = DailyAttendanceLog.objects.count()
                self.stdout.write(self.style.SUCCESS(f"Daily attendance processed: {result} | Total DailyAttendanceLog in DB: {daily_count}"))
            else:
                self.stdout.write(self.style.WARNING("No DeviceAttendanceLog found to process."))
