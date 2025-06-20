from django.db import models
from apps.peoples.models import BaseModel
from .managers import FeatureManager
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Features(BaseModel):
    '''
    Where we store all our product feature info
    along with their default price. This will be
    the master table.
    '''
    
    name         = models.CharField(max_length=100)
    defaultprice = models.IntegerField(default=0)
    description  = models.TextField(max_length=1000)
    isactive     = models.BooleanField(default=True)
    
    objects = FeatureManager()
    
    class Meta(BaseModel.Meta):
        db_table            = 'features'
        verbose_name        = 'Feature'
        verbose_name_plural = 'Features'
        constraints         = [
            models.UniqueConstraint(fields=['name'], name='unique_feature_name')
        ]
    
    def __str__(self):
        return self.name
    

class ApprovedFeature(BaseModel):
    class ApprovedChoices(models.TextChoices):
        A = ('Approved', 'Approved')
        P = ('Pending', 'Pending')
        R = ('Rejected', 'Rejected')
    feature = models.ForeignKey(Features, verbose_name=_("Feature"), on_delete=models.RESTRICT, null=True)
    comment = models.TextField(_("Comment"),null=True)
    approved = models.CharField(_("Approved"), max_length=50, choices=ApprovedChoices.choices)
    approvedon = models.DateTimeField(_("Approved On"), auto_now=False, auto_now_add=False)
    lastrequested = models.DateTimeField(_("Last Requested"), auto_now=False, auto_now_add=False, null=True)
    
    class Meta(BaseModel.Meta):
        db_table            = 'approvedfeatures'
        verbose_name        = 'Approved Feature'
        verbose_name_plural = 'Approved Features'
    
    def __str__(self):
        return self.feature.name

class Billing(BaseModel):
    '''
    Where we store the billing info which constitues 
    of features that client have opted and their newprices.
    '''
    
    client   = models.ForeignKey('onboarding.Bt', verbose_name='Client', null = True, blank = True, on_delete = models.RESTRICT)
    feature  = models.ForeignKey(Features, verbose_name='Feature', null = True, blank = True, on_delete = models.RESTRICT)
    newprice = models.IntegerField(default=0)
    currency = models.CharField(max_length=100)
    isactive = models.BooleanField(default=True)
    
    class Meta(BaseModel.Meta):
        db_table            = 'billing'
        verbose_name        = 'Billing'
        verbose_name_plural = 'Billings'
        constraints         = [
            models.UniqueConstraint(fields=['client', 'feature'], name='unique_client_feature')
        ]
    
    def __str__(self) -> str:
        return self.client.buname +'-'+ self.feature.name
    
    
    
class Discounts(BaseModel):
    '''
    Discount info if client have any with the date range.
    '''
    
    client   = models.ForeignKey('onboarding.Bt', verbose_name='Client', null = True, blank = True, on_delete =models.RESTRICT)
    discount = models.IntegerField(default=0) # In Percentage
    fromdate = models.DateField()
    uptodate = models.DateField()
    
    
    class Meta(BaseModel.Meta):
        db_table            = 'discounts'
        verbose_name        = 'Discount'
        verbose_name_plural = 'Discounts'
        constraints         = [
            models.UniqueConstraint(fields=['client', 'discount'], name='unique_client_discount')
        ]
    
    
    def __str__(self):
        return self.discount