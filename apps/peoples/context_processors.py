from django.conf import settings

def app_settings(request):
    return {
        'HOST': settings.HOST,
        'DEBUG': settings.DEBUG,
    }