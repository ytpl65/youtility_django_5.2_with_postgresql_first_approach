import logging
from datetime import datetime

from django.contrib.gis.db.models.functions import AsGeoJSON
from django.db import models
from django.db.models import CharField, F,Q
from django.db.models import Value as V
from django.db.models.functions import Cast, Concat
from apps.core import utils

from django.conf import settings
log = logging.getLogger('django')

class AttachmentManager(models.Manager):
    use_in_migrations = True

    def get_people_pic(self,  ownerid, db):
        qset =  self.filter(
                attachmenttype = 'ATTACHMENT',
                owner = ownerid
                ).annotate(
            people_event_pic = Concat(V(settings.MEDIA_ROOT), V('/'),  F('filepath'),  F('filename'),
                                    output_field = CharField())).order_by('-mdtz').using(db)
        return qset[0] or self.none()

    def get_attachment_record(self, uuid, db):
        qset =  self.filter(
            ~Q(filename__endswith = '.csv'),
            ~Q(filename__endswith = '.mp4'),
            ~Q(filename__endswith = '.txt'),
            ~Q(filename__endswith = '.3gp'),
            ownername__tacode = 'PEOPLEEVENTLOG',
            attachmenttype = 'ATTACHMENT', 
            owner = uuid
            ).using(db).values('ownername_id', 'ownername__tacode')
        return qset or self.none()

    def get_att_given_owner(self, owneruuid, request=None):
        "return attachments of given jobneed uuid"
        qset = self.filter(
            attachmenttype__in = ['ATTACHMENT', 'SIGN'], owner = owneruuid).order_by('cdtz').values(
                'id', 'filepath', 'filename', 'size', 'cdtz', 'cuser__peoplename'
            )
        return qset or self.none()
    
    
    def create_att_record(self, request, filename, filepath):
        R, S = request.POST, request.session
        from apps.onboarding.models import TypeAssist
        ta = TypeAssist.objects.filter(taname = R['ownername']).first()
        size = request.FILES.get('img').size if request.FILES.get('img') else 0
        PostData = {'filepath':filepath, 'filename':filename, 'owner':R['ownerid'], 'bu_id':S['bu_id'],
                'attachmenttype':R['attachmenttype'], 'ownername_id':ta.id,
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']), 'size':size}
        try:
            qset = self.create(**PostData)
            count = self.filter(owner = R['ownerid']).count()
        except Exception:
            log.critical("Attachment record creation failed...", exc_info=True)
            return {'error':'Upload attachment Failed'}
        return {'filepath':qset.filepath, 'filename':qset.filename.name, 'id':qset.id, 'ownername':qset.ownername.tacode, 'attcount': count} if qset else self.none()

    def get_attforuuids(self, uuids):
        return self.filter(owner__in = uuids) or self.none()
    
    def get_fr_status(self,attduuid):
        from apps.attendance.models import PeopleEventlog
        from apps.peoples.models import People

        #get attachments of IN and OUT of attendance
        attqset = self.filter(owner = attduuid, attachmenttype = 'ATTACHMENT', ownername__tacode='PEOPLEEVENTLOG').values('id', 'filename', 'filepath', 'cdtz', 'cuser__peoplename').order_by('cdtz') or self.none()

        #get eventlog of IN and OUT of attendance
        eventlogqset = PeopleEventlog.objects.filter(
            uuid = attduuid, peventtype__tacode__in = ['SELF', 'MARK']).annotate(
                eventtype = F('peventtype__tacode'),
                createdby = F('cuser__peoplename'),
                site = F('bu__buname'),
                startgps = AsGeoJSON('startlocation'),
                endgps = AsGeoJSON('endlocation'),).values(
                    'peventlogextras', 'startgps', 'endgps','createdby', 'datefor', 'site', 'people_id', 'people__uuid').order_by('cdtz') or PeopleEventlog.objects.none()
        #default image of people
        defaultimgqset = People.objects.filter(
            id=eventlogqset[0]['people_id']).values(
                'id', 'peopleimg', 'cdtz', 'cuser__peoplename', 'mdtz', 'muser__peoplename', 'ctzoffset') if eventlogqset else self.none()

        return {'attachment_in_out': list(attqset), 'eventlog_in_out': list(eventlogqset), 'default_people_data': list(defaultimgqset)}
    

    def get_attachements_for_mob(self, ownerid):
        qset = self.get_att_given_owner(ownerid)
        qset = qset.annotate(
            file = Concat(V(settings.MEDIA_URL), F('filepath'), Cast('filename', output_field=models.CharField()) )
        ).values_list('file', flat=True)
        return qset or self.none()

    
   