from datetime import datetime, timedelta, timezone
from django.db import models
from apps.core import utils




class DELManager(models.Manager):
    use_in_migrations = True
    
    def get_mobileuserlog(self, request):
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(request.GET)
        dt  = datetime.now(tz = timezone.utc) - timedelta(days = 10)
        qset = self.filter(
            bu_id = request.session['bu_id'],
            cdtz__gte = dt
        ).select_related('people', 'bu').values(*fields).order_by(dir)
        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset
            

    