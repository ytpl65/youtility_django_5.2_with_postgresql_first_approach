from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError
from apps.core import utils
from apps.core import exceptions as excp
from apps.onboarding.models import Bt, TypeAssist
from apps.peoples.models import People
from apps.onboarding.admin import TaResource
from apps.peoples.admin import CapabilityResource
from django.conf import settings
from tablib import Dataset
import logging
import psycopg2
from psycopg2 import sql
from intelliwiz_config.settings import SUPERADMIN_PASSWORD
log = logging.getLogger(__name__)

MAX_RETRY = 5


def create_dummy_client_and_site():
    client_type = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='CLIENT')
    site_type = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='SITE')

    client, _ = Bt.objects.get_or_create(
        bucode='SPS', 
        defaults={'buname': "Security Personnel Services", 'enable': True, 'identifier':client_type, 'parent_id':1}
    )

    site, _ = Bt.objects.get_or_create(
        bucode='YTPL', 
        defaults={'buname': 'Youtility Technologies Pvt Ltd', 'enable': True, 'identifier':site_type, 'parent_id':client.id}
    )
    return client, site

def create_sql_functions(db):
    from apps.core.raw_sql_functions import get_sqlfunctions
    sql_functions_list = get_sqlfunctions().values()
    # Connect to the database
    DBINFO = settings.DATABASES[db]
    conn = psycopg2.connect(
        database=DBINFO['NAME'],
        user=DBINFO['USER'],
        password=DBINFO['PASSWORD'],
        host=DBINFO['HOST'],
        port=DBINFO['PORT'])
    
    # Create a new cursor object
    cur = conn.cursor()
    
    for function in sql_functions_list:
        cur.execute(function)
        conn.commit()
    
    # Close the cursor and connection
    cur.close()
    conn.close()

    
    

def insert_default_entries():
    BASE_DIR = settings.BASE_DIR
    filepaths_and_resources = {
        f'{BASE_DIR}/docs/default_types.xlsx': TaResource,
        f'{BASE_DIR}/docs/caps.xlsx': CapabilityResource,
        # Add other files/resources here
    }

    for filepath, Resource in filepaths_and_resources.items():
        log.info("Importing file: %s", filepath)
        log.info("Using resource: %s", Resource.__name__)

        try:
            with open(filepath, 'rb') as f:
                dataset = Dataset().load(f.read(), format='xlsx')
                resource = Resource(is_superuser=True)
                result = resource.import_data(dataset, dry_run=False, use_transactions=True, raise_errors=True)
        except Exception as e:
            log.error("Error importing file %s using %s", filepath, Resource.__name__, exc_info=True)
            raise

def create_superuser(client, site):
    user = People.objects.create(
        peoplecode='SUPERADMIN', loginid="superadmin", peoplename='Super Admin',
        dateofbirth='1111-11-11', dateofjoin='1111-11-11',
        email='superadmin@youtility.in', isverified=True,
        is_staff=True, is_superuser=True,
        isadmin=True, client=client, bu=site
    )
    user.set_password(SUPERADMIN_PASSWORD)
    user.save()
    log.info(f"Superuser created successfully with loginid: {user.loginid} and password: {SUPERADMIN_PASSWORD}")

class Command(BaseCommand):
    help = 'This command creates None entries, a dummy Client and Site, a superuser, and inserts default entries in TypeAssist.'

    def add_arguments(self, parser) -> None:
        parser.add_argument('db', type=str)

    def handle(self, *args, **options):
        db = options['db']

        for _ in range(MAX_RETRY):
            try:
                utils.set_db_for_router(db)
                self.stdout.write(self.style.SUCCESS(f"Current DB selected is {utils.get_current_db_name()}"))

                utils.create_none_entries(self)
                self.stdout.write(self.style.SUCCESS('None Entries created successfully!'))

                insert_default_entries()
                self.stdout.write(self.style.SUCCESS('Default Entries Created..'))

                client, site = create_dummy_client_and_site()
                self.stdout.write(self.style.SUCCESS('Dummy client and site created successfully'))

                create_superuser(client, site)
                self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
                
                create_sql_functions(db=db)
                break  # operation was successful, break the loop

            except excp.RecordsAlreadyExist as ex:
                self.stdout.write(self.style.WARNING(f'Database with this alias "{db}" is not empty. Operation terminated!'))
                break

            except excp.NoDbError:
                self.stdout.write(self.style.ERROR(f"Database with alias '{db}' does not exist. Operation cannot be performed."))
                break

            except IntegrityError as e:
                # Database integrity constraint violation during initialization
                from apps.core.error_handling import ErrorHandler
                correlation_id = ErrorHandler.handle_exception(
                    e, 
                    context={'command': 'init_intelliwiz', 'database': db},
                    level='warning'
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"Data integrity constraint violated during initialization. "
                        f"This may indicate existing data conflicts. Correlation ID: {correlation_id}"
                    )
                )
                log.warning(f"IntegrityError in init_intelliwiz for db={db}: {str(e)}")
                continue  # Continue with next iteration instead of silently passing

            except Exception as e:
                log.critical('FAILED init_intelliwiz', exc_info = True)

           
