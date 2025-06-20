# from django.core.management.base import BaseCommand
# from django.db import transaction
# from django.db.utils import IntegrityError
# from apps.core import utils
# from apps.core import exceptions as excp
# from pprint import pformat
# import logging
# from intelliwiz_config.settings import SUPERADMIN_PASSWORD
# log = logging.getLogger('__main__')



# def create_dummy_client_site_and_superadmin(self):
#     from apps.onboarding.models import Bt, TypeAssist
#     from apps.peoples.models import People
#     try:
#         clienttype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='CLIENT')
#         sitetype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='SITE')

#         client, _ = Bt.objects.get_or_create(
#             bucode='SPS', buname = "Security Personnel Services",
#             enable = True, 
#             defaults={
#                 'butype_id':1, 'identifier':clienttype
#             }
#         )
#         site, _ = Bt.objects.get_or_create(
#             bucode='YTPL', buname = "Youtility Technologies Pvt Ltd",
#             enable = True,
#             defaults={
#                 'butype_id':1, 'identifier':sitetype
#             }
#         )
#         SU, _ = People.objects.get_or_create(
#             is_superuser = True, isadmin = True, isverified = True,
#             peoplecode='SUPERADMIN', is_staff = True, loginid = 'superadmin',
#             defaults={
#                 'peoplename': 'Superadmin', 'email': 'superadmin@youtility.in',
#                 'dateofjoin': '1111-11-11', 'dateofbirth': '1111-11-11',
#                 'client':client, 'bu':site
#             }
#         )
#         SU.set_password(SUPERADMIN_PASSWORD)
#         SU.save()
#         log.debug(f"Dummy client: 'SPS' and site: 'YTPL' created successfully...{pformat(utils.ok(self))}")
#         log.debug(f"Superuser with this loginid: 'SUPERADMIN' and password: 'superadmin@@2022@@' created successfully...{pformat(utils.ok(self))}")
#     except Exception as e:
#         if type(e) != IntegrityError:
#             log.error("Failed create_dummy_clientandsite", exc_info= True)
#         raise



# def insert_default_entries_in_typeassist(db, self):
#     """
#     Inserts Default rows in TypeAssist Table
#     """
#     from apps.onboarding.models import TypeAssist
#     from django.conf import settings
#     from tablib import Dataset
#     from apps.onboarding.admin import TaResource
#     BASEDIR = settings.BASE_DIR

#     try:
#         if TypeAssist.objects.filter(tacode='PEOPLETYPE').exists(): return
#         filepath = f'{BASEDIR}/docs/default_types.xlsx'
#         with open(filepath, 'rb') as f:
#             utils.set_db_for_router(db)
#             default_types = Dataset().load(f)
#             res = TaResource(is_superuser = True)
#             # TODO in production set raise_errors = False
#             res = res.import_data(dataset = default_types, dry_run = False, raise_errors = True, collect_failed_rows = True, use_transactions = True)
#             log.debug(f"Default Entries in table TypeAssist created successfully...{pformat(utils.ok(self))}")
#     except Exception as e:
#         if type(e) != IntegrityError:
#             log.error('FAILED insert_default_entries', exc_info = True)
#         raise


# def execute_tasks(db, self):
#     with transaction.atomic(using = db):
#         utils.create_none_entries(self)

#     # insert default entries for TypeAssist
#     insert_default_entries_in_typeassist(db, self)

#     with transaction.atomic(using = db):
#         # create dummy client: SPS and site: YTPL
#         create_dummy_client_site_and_superadmin(self)



# class Command(BaseCommand):
#     help = 'creates none entries in the followning tables:\n\
#     People, Capability, QuestionSet, Job, Asset, Jobneed, Bt, Typeassist Asset'


#     def add_arguments(self, parser) -> None:
#         parser.add_argument('db', nargs = 1, type = str)

#     def handle(self, *args, **options):
#         max_tries = 6
#         for _ in range(max_tries):
#             try:
#                 db = options['db'][0]
#                 utils.set_db_for_router(db)
#                 execute_tasks(db, self)
#                 break
#             except excp.NoDbError as e:
#                 self.stdout.write(self.style.ERROR("Database with this alias '%s' not exist operation can't be performed" % db))
#                 break
#             except excp.RecordsAlreadyExist as e:
#                 self.stdout.write(self.style.WARNING('Database with this alias "%s" is not empty so cannot create -1 extries operation terminated!' % db))
#                 break
#             except IntegrityError as e:
#                 continue
#             except Exception as e:
#                 if type(e) != IntegrityError:
#                     self.stdout.write(self.style.ERROR("something went wrong...!"))
#                     log.error('FAILED init_intelliwiz', exc_info = True)


