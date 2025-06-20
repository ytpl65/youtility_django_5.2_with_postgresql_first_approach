from django.apps import AppConfig

class ActivityConfig(AppConfig):
    name = 'apps.activity'
    
    def ready(self) -> None:
        from .import signals
