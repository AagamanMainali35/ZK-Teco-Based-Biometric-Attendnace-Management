                    Device table
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       Device 1       Device 2       Device 3
       enabled        enabled        disabled
          │              │
          ↓              ↓
       Connect         Connect
          │              │
          ↓              ↓
    get_attendance()  get_attendance()
          │              │
          └───────┬──────┘
                  ↓
           Raw attendance
                  ↓
          Process new logs
                  ↓
        DailyAttendance
