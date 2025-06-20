from django.apps import AppConfig


class YHelpdeskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.y_helpdesk'

    def ready(self) -> None:
        from .import signals