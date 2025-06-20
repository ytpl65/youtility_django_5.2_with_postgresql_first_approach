from django.apps import AppConfig


class WorkOrderManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.work_order_management'

    def ready(self) -> None:
        from .import signals