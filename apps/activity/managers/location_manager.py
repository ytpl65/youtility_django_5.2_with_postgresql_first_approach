import json
from datetime import datetime
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.db import models
from django.db.models import CharField,F,Q
from django.db.models import Value as V
from django.db.models.functions import Concat

class LocationManager(models.Manager):
    use_in_migrations = True
    
    def get_locationlistview(self, related, fields, request):
        S = request.session
        P = request.GET['params']
        qset = self.annotate(gps=AsGeoJSON('gpslocation')).filter(
            ~Q(loccode='NONE'),
            bu_id = S['bu_id'],
            client_id = S['client_id'],
        ).select_related(*related).values(*fields)
        if(P not in ['null', None]):
            P = json.loads(P)
            qset = qset.filter(locstatus = P['status'])
        return qset or self.none()
    
    def get_locations_modified_after(self, mdtz, buid, ctzoffset):
        related = ['client', 'cuser', 'muser', 'parent',  'tenant', 'type', 'bu']
        fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'loccode', 'locname', 'enable', 'iscritical', 
               'client_id', 'cuser_id', 'muser_id', 'parent_id',  'tenant_id', 'type_id', 'uuid',
               'gpslocation', 'locstatus',  'bu_id',]
        
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*related).filter(
            Q(mdtz__gte = mdtz) & Q(bu_id__in=[buid])  & Q(enable=True)
            ).values(*fields)
        return qset or self.none()
    
    def filter_for_dd_location_field(self, request, choices=False, sitewise=False):
        S = request.session
        qset = self.filter(
            enable=True,
            client_id = S['client_id'],
            bu_id__in = S['assignedsites'],
        ).order_by('locname')
        if sitewise: qset = qset.filter(bu_id = S['bu_id'])
        if choices: qset = qset.annotate(
            text = Concat(F('locname'), V(' ('), F('loccode'), V(')'))).values_list(
                'id', 'text'
            )
        return qset or self.none()
    
    def get_assets_of_location(self, request):
        R,S = request.GET, request.session
        obj = self.filter(id = R['locationid']).first()
        qset = obj.asset_set.annotate(
            text = Concat(F('assetname'), V(' ('), F('assetcode'), V(')'), output_field=CharField())
        ).filter(bu_id = S['bu_id']).values('id', 'text')
        return qset or self.none()
    
    def location_type_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).select_related('type').values_list(
            'type_id', 'type__taname'
        ).distinct('type_id').order_by('type_id')
        return qset or self.none()

    def location_choices_for_report(self,request,choices = False, sitewise= False):
        S = request.session 
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            enable = True
        )
        if sitewise : 
            qset = qset.filter(bu_id = S['bu_id'])
        if choices: 
            qset = qset.annotate(text = Concat(F('locname'),V('('),F('loccode'),V(')'))).values_list('id','text')
        return qset or self.none()
    
    