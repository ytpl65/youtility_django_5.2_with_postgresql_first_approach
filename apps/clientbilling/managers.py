from django.db import models

class FeatureManager(models.Manager):
    
    def get_feature_list(self, request):
        return self.values(
            'name', 'description', 'defaultprice',
            'isactive', 'id'
        ).order_by('-mdtz')
    
    def get_approvedfeature_list(self, request):
        from .models import Approvals
        return Approvals.objects.select_related('feature').values(
            'feature__name', 'comment','approved', 'approvedon',
            'lastrequested'
        )