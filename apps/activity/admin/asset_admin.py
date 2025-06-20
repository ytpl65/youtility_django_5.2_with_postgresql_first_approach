import re
from math import isnan
from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ValidationError
from import_export import fields, resources
from import_export import widgets as wg
from apps.activity.models.asset_model import Asset
import apps.onboarding.models as om
from apps.core import utils
import logging

logger = logging.getLogger(__name__)
from apps.core.widgets import EnabledTypeAssistWidget
from apps.service.validators import clean_point_field, clean_string
import math

def default_ta():
    return utils.get_or_create_none_typeassist()[0]


def clean_value(value):
    if isinstance(value, str) and value.strip().upper() == "NONE":
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value

class AssetResource(resources.ModelResource):
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
    Unit = fields.Field(
        column_name="Unit",
        attribute="unit",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=default_ta,
    )
    Category = fields.Field(
        column_name="Category",
        attribute="category",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )
    Brand = fields.Field(
        column_name="Brand",
        attribute="brand",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )

    ServiceProvider = fields.Field(
        column_name="Service Provider",
        attribute="servprov",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )

    SubCategory = fields.Field(
        column_name="Sub Category",
        attribute="subcategory",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )

    BelongsTo = fields.Field(
        column_name="Belongs To",
        attribute="parent",
        widget=wg.ForeignKeyWidget(Asset, "tacode"),
        saves_null_values=True,
        default=utils.get_or_create_none_asset,
    )

    Type = fields.Field(
        column_name="Asset Type",
        attribute="type",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )
    Identifier = fields.Field(
        attribute="identifier", column_name="Identifier*", default="ASSET"
    )
    ENABLE = fields.Field(attribute="id", column_name="Enable")
    is_critical = fields.Field(
        attribute="iscritical",
        column_name="Is Critical",
        default=False,
        widget=wg.BooleanWidget(),
    )
    is_meter = fields.Field(
        column_name="Is Meter", widget=wg.BooleanWidget(), default=False
    )
    Code = fields.Field(attribute="assetcode", column_name="Code*")
    Name = fields.Field(attribute="assetname", column_name="Name*")
    RunningStatus = fields.Field(
        attribute="runningstatus", column_name="Running Status*"
    )
    Capacity = fields.Field(
        widget=wg.DecimalWidget(),
        column_name="Capacity",
        attribute="capacity",
        default=0.0,
    )
    GPS = fields.Field(attribute="gpslocation", column_name="GPS Location")
    is_nonengg_asset = fields.Field(
        column_name="Is Non Engg. Asset", default=False, widget=wg.BooleanWidget()
    )
    supplier = fields.Field(column_name="Supplier", default="")
    meter = fields.Field(column_name="Meter", default="")
    model = fields.Field(column_name="Model", default="")
    invoice_no = fields.Field(column_name="Invoice No", default="")
    invoice_date = fields.Field(column_name="Invoice Date", default="")
    service = fields.Field(column_name="Service", default="")
    sfdate = fields.Field(column_name="Service From Date", default="")
    stdate = fields.Field(column_name="Service To Date", default="")
    yom = fields.Field(column_name="Year of Manufacture", default="")
    msn = fields.Field(column_name="Manufactured Serial No", default="")
    bill_val = fields.Field(column_name="Bill Value", default="")
    bill_date = fields.Field(column_name="Bill Date", default="")
    purchase_date = fields.Field(column_name="Purchase Date", default="")
    inst_date = fields.Field(column_name="Installation Date", default="")
    po_number = fields.Field(column_name="PO Number", default="")
    far_asset_id = fields.Field(column_name="FAR Asset ID", default="")

    class Meta:
        model = Asset
        skip_unchanged = True
        import_id_fields = ["Code"]
        report_skipped = True
        fields = [
            "Code",
            "Name",
            "GPS",
            "Identifier",
            "is_critical",
            "RunningStatus",
            "Capacity",
            "BelongsTo",
            "Type",
            "Client",
            "BV",
            "Category",
            "SubCategory",
            "Brand",
            "Unit",
            "ServiceProvider",
            "ENABLE",
            "is_critical",
            "is_meter",
            "is_nonengg_asset",
            "supplier",
            "meter",
            "model",
            "invoice_no",
            "invoice_date",
            "service",
            "sfdate",
            "stdate",
            "yom",
            "msn",
            "bill_val",
            "bill_date",
            "purchase_date",
            "inst_date",
            "po_number",
            "far_asset_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number=None, **kwargs):
        for key in row:
            row[key] = clean_value(row[key])
        self.validations(row)
        self.initialize_attributes(row)
        self.validating_identifier(row)
        self.validating_running_status(row)

    def validating_identifier(self, row):
        asset_identifier = row.get("Identifier*")
        valid_idetifier_values = ["NONE", "ASSET", "CHECKPOINT", "NEA"]
        if asset_identifier not in valid_idetifier_values:
            raise ValidationError(
                {
                    asset_identifier: "%(identifier)s is not a valid identifier. please select a valid identifier from %(valid)s" % {
                        "identifier": asset_identifier,
                        "valid": valid_idetifier_values
                    }
                }
            )

    def validating_running_status(self, row):
        running_status = row.get("Running Status*")
        valid_running_status = ["MAINTENANCE", "STANDBY", "WORKING", "SCRAPPED"]
        if running_status not in valid_running_status:
            raise ValidationError(
                {
                    "running_status": "%(status)s is not a valid running status. Please select a valid running status from %(valid)s." % {
                        "status": running_status,
                        "valid": valid_running_status
                    }
                }
            )

    def initialize_attributes(self, row):
        attributes = [
            ("_ismeter", "Is Meter", False),
            ("_is_nonengg_asset", "Is Non Engg. Asset", False),
            ("_supplier", "Supplier", ""),
            ("_meter", "Meter", ""),
            ("_model", "Model", ""),
            ("_invoice_no", "Invoice No", ""),
            ("_invoice_date", "Invoice Date", ""),
            ("_service", "Service", ""),
            ("_sfdate", "Service From Date", ""),
            ("_stdate", "Service To Date", ""),
            ("_yom", "Year of Manufacture", ""),
            ("_msn", "Manufactured Serial No", ""),
            ("_bill_val", "Bill Value", 0.0),
            ("_bill_date", "Bill Date", ""),
            ("_purchase_date", "Purchase Date", ""),
            ("_inst_date", "Installation Date", ""),
            ("_po_number", "PO Number", ""),
            ("_far_asset_id", "FAR Asset ID", ""),
        ]

        for attribute_name, key, default_value in attributes:
            value = row.get(key, default_value)
            if isinstance(value, float) and isnan(value):
                value = None
            setattr(self, attribute_name, value)

    def before_save_instance(self, instance, row, **kwargs):
        asset_json = instance.asset_json

        attributes = {
            "ismeter": self._ismeter,
            "tempcode": self._ismeter,  # I assume this is intentional, otherwise, replace with the correct value
            "is_nonengg_asset": self._is_nonengg_asset,
            "supplier": self._supplier,
            "service": self._service,
            "meter": self._meter,
            "model": self._model,
            "bill_val": self._bill_val,
            "invoice_date": self._invoice_date,
            "invoice_no": self._invoice_no,
            "msn": self._msn,
            "bill_date": self._bill_date,
            "purchase_date": self._purchase_date,  # I assume this is intentional, otherwise, replace with the correct value
            "inst_date": self._inst_date,
            "sfdate": self._sfdate,
            "stdate": self._po_number,
            "yom": self._yom,
            "po_number": self._po_number,
            "far_asset_id": self._far_asset_id,
        }

        for key, value in attributes.items():
            asset_json[key] = value
        instance.asset_json.update(asset_json)
        utils.save_common_stuff(self.request, instance, self.is_superuser)

    def validations(self, row):
        row["Code*"] = row.get("Code*")
        row["Name*"] = clean_string(row.get("Name*"))
        row["GPS Location"] = clean_point_field(row.get("GPS Location"))

        # check required fields
        if row.get("Code*") in ["", None]:
            raise ValidationError("Code* is required field")
        if row.get("Name*") in ["", None]:
            raise ValidationError("Name* is required field")
        if row.get("Identifier*") in ["", None]:
            raise ValidationError("Identifier* is required field")
        if row.get("Running Status*") in ["", None]:
            raise ValidationError("Running Status* is required field")

        # code validation
        regex, value = r"^[a-zA-Z0-9\-_]*$", row["Code*"]
        if re.search(r'\s|__', value):
            raise ValidationError("Please enter text without any spaces")
        if not re.match(regex, value):
            raise ValidationError(
                "Please enter valid text avoid any special characters except [_, -]"
            )
        logger.debug("Row %s", row)
        logger.debug("ASSETMETER: %s", (row.get("ASSETMETER", None), row.get("ASSET_METER", None)))
        logger.debug("Client %s", row["Client*"])
        logger.debug("Service %s", row["Service"])
        # unique record check
        if (
            Asset.objects.select_related()
            .filter(
                assetcode=row["Code*"],
                bu__bucode=row["Site*"],
                client__bucode=row["Client*"],
            )
            .exists()
        ):
            raise ValidationError(
                f"Record with these values already exist {row.values()}"
            )
        
        if row.get("Service"):
            if row.get("Service") == "NONE":
                obj = utils.get_or_create_none_typeassist()
                row["Service"] = obj.id
            if isnan(row.get("Service")):
                row["Service"] = ""
            else:
                obj = (
                    om.TypeAssist.objects.select_related("tatype")
                    .filter(
                        tatype__tacode__in=[
                            "SERVICE_TYPE",
                            "ASSETSERVICE",
                            "ASSET_SERVICE", 
                            "SERVICETYPE",
                        ],
                        #tacode=row["Service"],
                        client__bucode=row["Client*"],
                    )
                    .first()
                )
                row["Service"] = obj.id
                if not obj:
                    raise ValidationError(f"Service {row['Service']} does not exist")
        
        if row.get("Meter"):
            if row.get("Meter") == "NONE":
                obj = utils.get_or_create_none_typeassist()
                row["Meter"] = obj.id
            if isnan(row.get("Meter")):
                row["Meter"] = ""
            else:
                obj = (
                    om.TypeAssist.objects.select_related("tatype")
                    .filter(
                        tatype__tacode=row["ASSETMETER", "ASSET_METER"],
                        client__bucode=row["Client*"],
                    )
                    .first()
                )
                row["Meter"] = obj.id
                if not obj:
                    raise ValidationError(f"Meter {row['Meter']} does not exist")


class AssetResourceUpdate(resources.ModelResource):
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

    Unit = fields.Field(
        column_name = 'Unit',
        attribute = 'unit',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    Category = fields.Field(
        column_name = 'Category',
        attribute = 'category',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    Brand = fields.Field(
        column_name = 'Brand',
        attribute = 'brand',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    ServiceProvider = fields.Field(
        column_name="Service Provider",
        attribute="servprov",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )

    SubCategory = fields.Field(
        column_name = 'SubCategory',
        attribute = 'subcategory',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    BelongsTo = fields.Field(
        column_name="Belongs To",
        attribute="parent",
        widget=wg.ForeignKeyWidget(Asset, "tacode"),
        saves_null_values=True,
        default=utils.get_or_create_none_asset,
    )

    Type = fields.Field(
        column_name = 'Type',
        attribute = 'type',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default = default_ta
    )

    Identifier = fields.Field(
        attribute="identifier", column_name="Identifier", default="ASSET"
    )
    ID = fields.Field(attribute="id", column_name="ID*")
    ENABLE = fields.Field(attribute="enable", column_name="Enable")
    is_critical = fields.Field(
        attribute="iscritical",
        column_name="Is Critical",
        default=False,
        widget=wg.BooleanWidget(),
    )
    is_meter = fields.Field(
        column_name="Is Meter", attribute='asset_json.is_meter', widget=wg.BooleanWidget(), default=False
    )
    Code = fields.Field(attribute="assetcode", column_name="Code")
    Name = fields.Field(attribute="assetname", column_name="Name")
    RunningStatus = fields.Field(
        attribute="runningstatus", column_name="Running Status"
    )
    Capacity = fields.Field(
        widget=wg.DecimalWidget(),
        column_name="Capacity",
        attribute="capacity",
        default=0.0,
    )
    GPS = fields.Field(attribute="gpslocation", column_name="GPS Location")
    is_nonengg_asset = fields.Field(
        column_name="Is Non Engg. Asset", attribute='asset_json.is_nonengg_asset', default=False, widget=wg.BooleanWidget()
    )
    supplier = fields.Field(column_name="Supplier", attribute='asset_json.supplier', default="")
    meter = fields.Field(column_name="Meter", attribute='asset_json.meter', default="")
    model = fields.Field(column_name="Model", attribute='asset_json.model', default="")
    invoice_no = fields.Field(column_name="Invoice No", attribute='asset_json.invoice_no', default="")
    invoice_date = fields.Field(column_name="Invoice Date", attribute='asset_json.invoice_date', default="")
    service = fields.Field(column_name="Service", attribute='asset_json.service', default="")
    sfdate = fields.Field(column_name="Service From Date", attribute='asset_json.sfdate', default="")
    stdate = fields.Field(column_name="Service To Date", attribute='asset_json.stdate', default="")
    yom = fields.Field(column_name="Year of Manufacture", attribute='asset_json.yom', default="")
    msn = fields.Field(column_name="Manufactured Serial No", attribute='asset_json.msn', default="")
    bill_val = fields.Field(column_name="Bill Value", attribute='asset_json.bill_val', default="")
    bill_date = fields.Field(column_name="Bill Date", attribute='asset_json.bill_date', default="")
    purchase_date = fields.Field(column_name="Purchase Date", attribute='asset_json.purchase_date', default="")
    inst_date = fields.Field(column_name="Installation Date", attribute='asset_json.inst_date', default="")
    po_number = fields.Field(column_name="PO Number", attribute='asset_json.po_number', default="")
    far_asset_id = fields.Field(column_name="FAR Asset ID", attribute='asset_json.far_asset_id', default="")

    class Meta:
        model = Asset
        skip_unchanged = True
        import_id_fields = ["ID"]
        report_skipped = True
        fields = [
            "ID",
            "Code",
            "Name",
            "GPS",
            "Identifier",
            "is_critical",
            "RunningStatus",
            "Capacity",
            "BelongsTo",
            "Type",
            "Client",
            "BV",
            "Category",
            "SubCategory",
            "Brand",
            "Unit",
            "ServiceProvider",
            "ENABLE",
            "is_critical",
            "is_meter",
            "is_nonengg_asset",
            "supplier",
            "meter",
            "model",
            "invoice_no",
            "invoice_date",
            "service",
            "sfdate",
            "stdate",
            "yom",
            "msn",
            "bill_val",
            "bill_date",
            "purchase_date",
            "inst_date",
            "po_number",
            "far_asset_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number=None, **kwargs):
        self.validations(row)
        self.initialize_attributes(row)
        self.validating_identifier(row)
        self.validating_running_status(row)

    def validating_identifier(self, row):
        if "Identifier" in row:
            asset_identifier = row.get("Identifier")
            valid_idetifier_values = ["NONE", "ASSET", "CHECKPOINT", "NEA"]
            if asset_identifier not in valid_idetifier_values:
                raise ValidationError(
                    {
                        asset_identifier: "%(identifier)s is not a valid identifier. please select a valid identifier from %(valid)s" % {
                            "identifier": asset_identifier,
                            "valid": valid_idetifier_values
                        }
                    }
                )

    def validating_running_status(self, row):
        if "Running Status" in row:
            running_status = row.get("Running Status")
            valid_running_status = ["MAINTENANCE", "STANDBY", "WORKING", "SCRAPPED"]
            if running_status not in valid_running_status:
                raise ValidationError(
                    {
                        "running_status": "%(status)s is not a valid running status. Please select a valid running status from %(valid)s." % {
                            "status": running_status,
                            "valid": valid_running_status
                        }
                    }
                )

    def initialize_attributes(self, row):
        attributes = [
            ("_ismeter", "Is Meter", False),
            ("_is_nonengg_asset", "Is Non Engg. Asset", False),
            ("_supplier", "Supplier", ""),
            ("_meter", "Meter", ""),
            ("_model", "Model", ""),
            ("_invoice_no", "Invoice No", ""),
            ("_invoice_date", "Invoice Date", ""),
            ("_service", "Service", ""),
            ("_sfdate", "Service From Date", ""),
            ("_stdate", "Service To Date", ""),
            ("_yom", "Year of Manufacture", ""),
            ("_msn", "Manufactured Serial No", ""),
            ("_bill_val", "Bill Value", 0.0),
            ("_bill_date", "Bill Date", ""),
            ("_purchase_date", "Purchase Date", ""),
            ("_inst_date", "Installation Date", ""),
            ("_po_number", "PO Number", ""),
            ("_far_asset_id", "FAR Asset ID", ""),
        ]

        for attribute_name, key, default_value in attributes:
            if key in row:
                value = row.get(key, default_value)
                if isinstance(value, float) and isnan(value):
                    value = None
                setattr(self, attribute_name, value)

    def before_save_instance(self, instance,row,**kwargs):
        asset_json = instance.asset_json
        attributes = {
            "ismeter": "_ismeter",
            "tempcode": "_ismeter",  # I assume this is intentional, otherwise, replace with the correct value
            "is_nonengg_asset": "_is_nonengg_asset",
            "supplier": "_supplier",
            "service": "_service",
            "meter": "_meter",
            "model": "_model",
            "bill_val": "_bill_val",
            "invoice_date": "_invoice_date",
            "invoice_no": "_invoice_no",
            "msn": "_msn",
            "bill_date": "_bill_date",
            "purchase_date": "_purchase_date",  # I assume this is intentional, otherwise, replace with the correct value
            "inst_date": "_inst_date",
            "sfdate": "_sfdate",
            "stdate": "_po_number",
            "yom": "_yom",
            "po_number": "_po_number",
            "far_asset_id": "_far_asset_id",
        }

        for key, attr_name in attributes.items():
            value = getattr(self, attr_name, None)
            if value is not None:
                asset_json[key] = value
        instance.asset_json.update(asset_json)
        utils.save_common_stuff(self.request, instance, self.is_superuser)

    def validations(self, row):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        if 'GPS Location' in row:
            row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        
        #check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Code' in row:
            if row.get('Code') in  ['', None]:raise ValidationError("Code is required field")
        if 'Name' in row:
            if row.get('Name') in  ['', None]:raise ValidationError("Name is required field")
        if 'Identifier' in row:
            if row.get('Identifier') in  ['', None]:raise ValidationError("Identifier is required field")
        if 'Running Status' in row:
            if row.get('Running Status') in  ['', None]:raise ValidationError("Running Status is required field")
        
        # code validation
        if "Code" in row:
            regex, value = r"^[a-zA-Z0-9\-_]*$", row["Code"]
            if re.search(r'\s|__', value):
                raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError(
                    "Please enter valid text avoid any special characters except [_, -]"
                )

        # check record exists
        if not Asset.objects.filter(id=row["ID*"]).exists():
            raise ValidationError(
                f"Record with these values not exist: ID - {row['ID*']}"
            )

        if "Service" in row:
            if row.get("Service"):
                if row.get("Service") == "NONE":
                    obj = utils.get_or_create_none_typeassist()
                    row["Service"] = obj.id

                if isnan(row.get("Service")):
                    row["Service"] = ""
                else:
                    if "Client" in row:
                        obj = (
                            om.TypeAssist.objects.select_related("tatype")
                            .filter(
                                tatype__tacode__in=[
                                    "SERVICE_TYPE",
                                    "ASSETSERVICE",
                                    "ASSET_SERVICE" "SERVICETYPE",
                                ],
                                tacode=row["Service"],
                                client__bucode=row["Client"],
                            )
                            .first()
                        )
                        row["Service"] = obj.id
                        if not obj:
                            raise ValidationError(
                                f"Service {row['Service']} does not exist"
                            )

        if "Meter" in row:
            if row.get("Meter"):
                if row.get("Meter") == "NONE":
                    obj = utils.get_or_create_none_typeassist()
                    row["Meter"] = obj.id
                if isnan(row.get("Meter")):
                    row["Meter"] = ""
                else:
                    if "Client" in row and "ASSETMETER" in row and "ASSET_METER" in row:
                        obj = (
                            om.TypeAssist.objects.select_related("tatype")
                            .filter(
                                tatype__tacode=row["ASSETMETER", "ASSET_METER"],
                                client__bucode=row["Client"],
                            )
                            .first()
                        )
                        row["Meter"] = obj.id
                        if not obj:
                            raise ValidationError(
                                f"Meter {row['Meter']} does not exist"
                            )
