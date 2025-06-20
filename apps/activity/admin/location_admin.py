import re
from math import isnan
from django.core.exceptions import ValidationError
from import_export import fields, resources
from import_export import widgets as wg
from apps.activity.models.location_model import Location
import apps.onboarding.models as om
from apps.core import utils
from apps.core.widgets import EnabledTypeAssistWidget
from apps.service.validators import clean_point_field, clean_string

def default_ta():
    return utils.get_or_create_none_typeassist()[0]





class LocationResource(resources.ModelResource):
    Client = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )
    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )

    PARENT = fields.Field(
        column_name="Belongs To",
        attribute="parent",
        widget=wg.ForeignKeyWidget(Location, "loccode"),
        saves_null_values=True,
        default=utils.get_or_create_none_location,
    )

    # django validates this field and throws error if the value is not valid
    Type = fields.Field(
        column_name="Type*",
        attribute="type",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )

    ID = fields.Field(attribute="id")
    ENABLE = fields.Field(attribute="enable", column_name="Enable", default=True)
    CODE = fields.Field(attribute="loccode", column_name="Code*")
    NAME = fields.Field(attribute="locname", column_name="Name*")
    RS = fields.Field(attribute="locstatus", column_name="Status*")
    ISCRITICAL = fields.Field(
        attribute="iscritical", column_name="Is Critical", default=False
    )
    GPS = fields.Field(attribute="gpslocation", column_name="GPS Location")

    class Meta:
        model = Location
        skip_unchanged = True
        import_id_fields = ["ID"]
        report_skipped = True
        fields = ["CODE", "NAME", "PARENT", "RS", "ISCRITICAL", "GPS", "CLIENT", "BV","Client","Type","ID","ENABLE"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def check_valid_status(self, row):
        status = row.get("Status*")
        valid_status = ["MAINTENANCE", "STANDBY", "WORKING", "SCRAPPED"]
        if status not in valid_status:
            raise ValidationError(
                {
                    status: "%(current)s is not a valid status. Please select a valid status from %(valid)s" % {
                        "current": status,
                        "valid": valid_status
                    }
                }
            )

    def before_import_row(self, row, row_number=None, **kwargs):
        row["Code*"] = row.get("Code*")
        row["Name*"] = clean_string(row.get("Name*"))
        row["GPS Location"] = clean_point_field(row.get("GPS Location"))

        # check required fields
        if row.get("Code*") in ["", None]:
            raise ValidationError("Code* is required field")
        if row.get("Name*") in ["", None]:
            raise ValidationError("Name* is required field")
        if row.get("Type*") in ["", None]:
            raise ValidationError("Type* is required field")
        if row.get("Status*") in ["", None]:
            raise ValidationError("Status* is required field")

        # status validation
        self.check_valid_status(row)

        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row["Code*"]
        if re.search(r'\s|__', value):
            raise ValidationError("Please enter text without any spaces")
        if not re.match(regex, value):
            raise ValidationError(
                "Please enter valid text avoid any special characters except [_, -]"
            )

        # unique record check
        if (
            Location.objects.select_related()
            .filter(loccode=row["Code*"], client__bucode=row["Client*"])
            .exists()
        ):
            raise ValidationError(
                f"Record with these values already exist {row.values()}"
            )
        super().before_import_row(row, row_number, **kwargs)

    def before_save_instance(self, instance,row,**kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


class LocationResourceUpdate(resources.ModelResource):
    Client = fields.Field(
        column_name="Client",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BV = fields.Field(
        column_name="Site",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )

    PARENT = fields.Field(
        column_name="Belongs To",
        attribute="parent",
        widget=wg.ForeignKeyWidget(Location, "loccode"),
        saves_null_values=True,
        default=utils.get_or_create_none_location,
    )

    Type = fields.Field(
        column_name = 'Type',
        attribute = 'type',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    ID = fields.Field(attribute="id", column_name="ID*")
    ENABLE = fields.Field(attribute="enable", column_name="Enable", default=True)
    CODE = fields.Field(attribute="loccode", column_name="Code")
    NAME = fields.Field(attribute="locname", column_name="Name")
    RS = fields.Field(attribute="locstatus", column_name="Status")
    ISCRITICAL = fields.Field(
        attribute="iscritical", column_name="Is Critical", default=False
    )
    GPS = fields.Field(attribute="gpslocation", column_name="GPS Location")

    class Meta:
        model = Location
        skip_unchanged = True
        #import_id_fields = ["ID"]
        report_skipped = True
        fields = [
            "ID",
            "CODE",
            "NAME",
            "PARENT",
            "RS",
            "ISCRITICAL",
            "GPS",
            "CLIENT",
            "BV",
            "Type",
            "Client",
            "ENABLE",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def check_valid_status(self, row):
        if "Status" in row:
            status = row.get("Status")
            valid_status = ["MAINTENANCE", "STANDBY", "WORKING", "SCRAPPED"]
            if status not in valid_status:
                raise ValidationError(
                    {
                        status: "%(current)s is not a valid status. Please select a valid status from %(valid)s" % {
                            "current": status,
                            "valid": valid_status
                        }
                    }
                )

    def before_import_row(self, row, row_number=None, **kwargs):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        if 'GPS Location' in row:
            row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        #check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})

        # status validation
        self.check_valid_status(row)

        # code validation
        if "Code" in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row["Code"]
            if re.search(r'\s|__', value):
                raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError(
                    "Please enter valid text avoid any special characters except [_, -]"
                )

        # check record exists
        if not Location.objects.filter(id=row["ID*"]).exists():
            raise ValidationError(
                f"Record with these values not exist: ID - {row['ID*']}"
            )
        super().before_import_row(row, row_number, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


