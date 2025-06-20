from django.apps import AppConfig

class SchedhulerConfig(AppConfig):
    name = 'apps.schedhuler'

    def ready(self):
        import apps.schedhuler.signals
