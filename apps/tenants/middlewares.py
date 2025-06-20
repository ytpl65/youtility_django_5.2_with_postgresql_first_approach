from apps.core.utils import tenant_db_from_request, THREAD_LOCAL

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        db = tenant_db_from_request(request)
        setattr(THREAD_LOCAL, "DB", db)
        return self.get_response(request)



class TenantDbRouter:
    @staticmethod
    def _multi_db():
        from django.http import Http404
        from django.conf import settings
        if hasattr(THREAD_LOCAL, 'DB'):
            if THREAD_LOCAL.DB in settings.DATABASES:
                return THREAD_LOCAL.DB
            raise Http404
        return 'default'

    def db_for_read(self, model, **hints):
        return self._multi_db()

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    @staticmethod
    def allow_relation(obj1, obj2, **hints):
        return True

    @staticmethod
    def allow_migrate(db, app_label, model_name = None, **hints):
        return True
