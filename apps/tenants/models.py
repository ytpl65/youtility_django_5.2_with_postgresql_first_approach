from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Tenant(models.Model):
    tenantname = models.CharField(_("tenantname"), max_length = 50)
    subdomain_prefix = models.CharField(_("subdomain_prefix"), max_length = 50, unique = True)
    created_at = models.DateTimeField(_("created_at"), auto_now = False, auto_now_add = True)

class TenantAwareModel(models.Model):
    tenant = models.ForeignKey(Tenant,  null = True, blank = True, on_delete = models.CASCADE)

    class Meta:
        abstract = True
