from django.apps import AppConfig

class AttendanceConfig(AppConfig):
    name = 'apps.attendance'
    def ready(self):
        import apps.attendance.signals
