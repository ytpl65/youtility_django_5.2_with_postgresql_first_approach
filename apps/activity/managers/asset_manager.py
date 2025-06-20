import logging
from datetime import datetime, date, timedelta
from django.contrib.gis.db.models.functions import AsGeoJSON, AsWKT
from django.db import models
from django.db.models import Count,F,Q
from django.db.models import Value as V
from django.db.models.functions import Concat
from apps.core import utils

from apps.core.json_utils import safe_json_parse



class AssetManager(models.Manager):
    use_in_migrations = True
    related = ['category', 'client', 'cuser', 'muser', 'parent', 'subcategory', 'tenant', 'type', 'unit', 'brand', 'bu', 'servprov']
    fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'assetcode', 'assetname', 'enable', 'iscritical', 'gpslocation', 'identifier', 'runningstatus', 'capacity', 'brand_id', 'bu_id',
              'category_id', 'client_id', 'cuser_id', 'muser_id', 'parent_id', 'servprov_id', 'subcategory_id', 'tenant_id', 'type_id', 'unit_id']

    def get_assetdetails(self, mdtz, site_id):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(
            Q(id=1) | 
            ~Q(identifier = 'NEA'),
            ~Q(runningstatus = 'SCRAPPED'),
            Q(mdtz__gte = mdtzinput),
            Q(bu_id= site_id),
        ).select_related(
            *self.related
        ).values(*self.fields) or self.none()
    
    def asset_type_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).select_related('type').values_list(
            'type_id', 'type__taname'
        ).distinct('type_id').order_by('type_id')
        return qset or self.none()
    
    def asset_category_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).select_related('category').values_list(
            'category_id', 'category__taname'
        ).distinct('category_id').order_by('category_id')
        return qset or self.none()

    def asset_choices_for_report(self,request,choices = False, sitewise= False, identifier = None):
        S = request.session
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            enable = True,
            identifier = identifier
        )
        if sitewise : 
            qset = qset.filter(bu_id = S['bu_id'])
        if choices:
            qset = qset.annotate(text = Concat(F('assetname'),V('('),F('assetcode'),V(')'))).values_list('id','text')
        return qset or self.none()
    
    def get_schedule_task_for_adhoc(self, params):
        qset = self.raw("select * from fn_get_schedule_for_adhoc")
        
    def get_peoplenearasset(self, request):
        "List View"
        qset = self.annotate(gps = AsWKT('gpslocation')).filter(
            identifier__in = ['ASSET', 'SMARTPLACE', 'CHECKPOINT'],
            bu_id = request.session['bu_id']
        ).values('id', 'assetcode', 'assetname', 'identifier', 'gps')
        return qset or self.none()
    
    def get_checkpointlistview(self, request, related, fields, id=None):
        S = request.session
        P_raw = request.GET.get('params')
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(identifier='CHECKPOINT',id=id).values(*fields)[0]
        else:
            qset = qset.filter(identifier='CHECKPOINT', bu_id=S['bu_id'], client_id = S['client_id']).values(*fields)
        
        # Safe JSON parsing
        P = safe_json_parse(P_raw)
        if P and P.get('status'):
            qset = qset.filter(runningstatus = P['status'])
        
        return qset or self.none()
    
    def get_smartplacelistview(self, request, related, fields, id=None):
        S = request.session
        P = request.GET['params']
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(enable=True, identifier='SMARTPLACE',id=id).values(*fields)[0]
        else:
            qset = qset.filter(enable=True, identifier='SMARTPLACE', bu_id = S['bu_id'], client_id = S['client_id']).values(*fields)
        return qset or self.none()
    
    def get_assetlistview(self, related, fields, request):
        
        S = request.session
        P_raw = request.GET.get('params')
        qset = self.annotate(gps = AsGeoJSON('gpslocation')).filter(
            ~Q(assetcode='NONE'),
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            identifier='ASSET'
        ).select_related(*related).values(*fields)
        
        # Safe JSON parsing
        P = safe_json_parse(P_raw)
        if P and P.get('status'):
            qset = qset.filter(runningstatus = P['status'])
        return qset or self.none()
    
    
    
    
    def get_assetchart_data(self, request):
        from apps.activity.models.location_model import Location
        S = request.session
        # Common filter for `bu` and `client`
        common_filter = Q(bu_id=S['bu_id'], client_id=S['client_id'])

        # Query for asset data grouped by `runningstatus` and `identifier`
        asset_data = (
            self.filter(common_filter)
            .values('runningstatus', 'identifier')
            .annotate(total=Count('assetcode', distinct=True))
        )
        
        # Query for location data grouped by `locstatus`
        location_data = (
            Location.objects.filter(common_filter)
            .values('locstatus')
            .annotate(total=Count('loccode', distinct=True))
        )

        # Prepare series data
        statuses = ['WORKING', 'MAINTENANCE', 'STANDBY', 'SCRAPPED']
        identifiers = ['ASSET', 'CHECKPOINT']

        series = []
        for status in statuses:
            asset_counts = [
                next(
                    (entry['total'] for entry in asset_data if entry['runningstatus'] == status and entry['identifier'] == identifier),
                    0
                )
                for identifier in identifiers
            ]
            loc_count = next(
                (entry['total'] for entry in location_data if entry['locstatus'] == status),
                0
            )
            series.append({'name': status.capitalize(), 'data': asset_counts + [loc_count]})

        # Calculate total counts across all status types
        total_data = sum(sum(entry['data']) for entry in series)
        return series, total_data
    
    def filter_for_dd_asset_field(self, request, identifiers, choices=False, sitewise=False):
        client_id = request.session.get('client_id')
        assigned_sites = request.session.get('assignedsites')
        bu_id = request.session.get('bu_id')

        base_filters = {
            "enable": True,
            "client_id": client_id,
            "bu_id__in": assigned_sites,
            "identifier__in": identifiers,
            
        }
        if sitewise and bu_id:
            base_filters["bu_id"] = bu_id

        qset = self.filter(~Q(runningstatus='SCRAPPED'), **base_filters).order_by('assetname')

        if choices:
            qset = (
                qset.annotate(
                    text=Concat(
                        F('assetname'), V(' ('), F('assetcode'), V(')')
                    )
                )
                .values_list('id', 'text')
            )

        return qset or self.none()

    
    def get_period_of_assetstatus(self, assetid, status):
        from apps.core.raw_queries import get_query
        query = get_query("asset_status_period")
        qset = utils.runrawsql(
            query, [status, status, assetid]
        )
        if not qset: return f"The Asset has not yet undergone any {status.lower()} period."
        if qset and  qset[0]['total_duration']:
            return utils.format_timedelta(qset[0]['total_duration'])
        
    
    def get_asset_checkpoints_for_tour(self, request):
        R, S = request.GET, request.session
        search_term = R.get('search')
        qset = self.filter(client_id = S['client_id'], bu_id = S['bu_id'], enable=True)
        qset = qset.filter(assetname__icontains = search_term) if search_term else qset
        qset = qset.annotate(
                text = F('assetname')).values(
                    'id', 'text')
        return qset or self.none()
    
class AssetLogManager(models.Manager):
    use_in_migrations = True
    
    def get_asset_logs(self, request):
        R, S = request.GET, request.session

        from apps.core.raw_queries import get_query
        from django.db import connection
        query = get_query('all_asset_status_duration')


        with connection.cursor() as cursor:


            # Fetch the subset of records
            cursor.execute(query % (S['client_id'], S['bu_id']))
            rows = cursor.fetchall()


        data = [
            {
                'assetname': row[1],
                'newstatus': row[2],
                'duration_seconds': row[3],
                'duration_interval':row[4]
                # add more fields as needed
            }
            for row in rows
        ]
        return {
            'data': data,
        }
        