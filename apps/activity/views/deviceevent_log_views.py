from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import response as rp
from apps.activity.models.deviceevent_log_model import DeviceEventlog
from django.shortcuts import render
from django.views.generic.base import View
from apps.activity.utils import serialize_obj

class MobileUserLog(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/mobileuserlog.html',
        'model':DeviceEventlog,
        'related':['bu', 'people'],
        'fields':['cdtz', 'bu__buname', 'startlocation', 'endlocation', 'signalstrength',
                  'availintmemory', 'availextmemory', 'signalbandwidth', 'ctzoffset',
                  'people__peoplename', 'gpslocation', 'eventvalue', 'batterylevel']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])



        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_mobileuserlog(request)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':[serialize_obj(o) for o in objs],
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
            
            

class MobileUserDetails(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/mobileuserlog.html',
        'model':DeviceEventlog,
        'related':['bu', 'people'],
        'fields':['cdtz', 'bu__buname', 'signalstrength',
                  'availintmemory', 'availextmemory', 'signalbandwidth', 'ctzoffset',
                  'people__peoplename', 'gpslocation', 'eventvalue', 'batterylevel']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_mobileuserlog(request)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
            
