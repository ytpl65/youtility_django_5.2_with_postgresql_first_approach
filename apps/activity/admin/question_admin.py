from math import isnan
from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ValidationError
from import_export import fields, resources
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
import apps.onboarding.models as om
from apps.core.widgets import EnabledTypeAssistWidget
import logging

logger = logging.getLogger(__name__)
from apps.core import utils
from apps.service.validators import clean_string

# Register your models here.
def default_ta():
    return utils.get_or_create_none_typeassist()[0]


class QuestionResource(resources.ModelResource):
    Unit = fields.Field(
        column_name="Unit",
        attribute="unit",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )
    Category = fields.Field(
        column_name="Category",
        attribute="category",
        widget=wg.ForeignKeyWidget(om.TypeAssist, "tacode"),
        saves_null_values=True,
        default=default_ta,
    )
    Client = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    id = fields.Field(attribute="id", column_name="ID")
    AlertON = fields.Field(
        attribute="alerton", column_name="Alert On", saves_null_values=True
    )
    ALERTABOVE = fields.Field(column_name="Alert Above", saves_null_values=True)
    ALERTBELOW = fields.Field(column_name="Alert Below", saves_null_values=True)
    Options = fields.Field(
        attribute="options", column_name="Options", saves_null_values=True
    )
    Name = fields.Field(attribute="quesname", column_name="Question Name*")
    Type = fields.Field(attribute="answertype", column_name="Answer Type*")
    Min = fields.Field(attribute="min", column_name="Min", saves_null_values=True)
    Max = fields.Field(attribute="max", column_name="Max", saves_null_values=True)
    Enable = fields.Field(
        attribute="enable",
        column_name="Enable",
        default=True,
        widget=wg.BooleanWidget(),
    )
    IsAvpt = fields.Field(
        attribute="isavpt",
        column_name="Is AVPT",
        default=False,
        widget=wg.BooleanWidget(),
    )
    AttType = fields.Field(
        attribute="avpttype", column_name="AVPT Type", saves_null_values=True
    )
    isworkflow = fields.Field(
        attribute="isworkflow", column_name="Is WorkFlow", default=False
    )

    class Meta:
        model = Question
        skip_unchanged = True
        report_skipped = True
        fields = [
            "Name",
            "Type",
            "Unit",
            "Options",
            "Enable",
            "IsAvpt",
            "AttType",
            "id",
            "Client",
            "Min",
            "Max",
            "AlertON",
            "isworkflow",
            "Category",
            "ALERTABOVE",
            "ALERTBELOW",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.handle_nan_values(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.check_answertype_fields(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_unique_record(row)
        super().before_import_row(row, **kwargs)

    def check_answertype_fields(self, row):
        Authorized_AnswerTypes = [
            "DATE",
            "CHECKBOX",
            "MULTISELECT",
            "DROPDOWN",
            "EMAILID",
            "MULTILINE",
            "NUMERIC",
            "SIGNATURE",
            "SINGLELINE",
            "TIME",
            "RATING",
            "PEOPLELIST",
            "SITELIST",
            "METERREADING",
        ]
        Answer_type_val = row.get("Answer Type*")
        if Answer_type_val not in Authorized_AnswerTypes:
            raise ValidationError(
                {
                    Answer_type_val: f"{Answer_type_val} is a not a valid Answertype.Please select a valid AnswerType."
                }
            )

    def check_required_fields(self, row):
        required_fields = ["Answer Type*", "Question Name*", "Client*"]
        for field in required_fields:
            if row.get(field) in ["", None]:
                raise ValidationError({field: f"{field} is a required field"})

    def clean_question_name_and_answer_type(self, row):
        row["Question Name*"] = clean_string(row.get("Question Name*"))
        row["Answer Type*"] = clean_string(row.get("Answer Type*"), code=True)

    def clean_numeric_and_rating_fields(self, row):
        answer_type = row.get("Answer Type*")
        if answer_type in ["NUMERIC", "RATING"]:
            row["Options"] = None
            self.convert_to_float(row, "Min")
            self.convert_to_float(row, "Max")
            self.convert_to_float(row, "Alert Below")
            self.convert_to_float(row, "Alert Above")

    def convert_to_float(self, row, field):
        value = row.get(field)
        if value is not None:
            row[field] = float(value)
        elif field in ["Min", "Max"]:
            raise ValidationError(
                {
                    field: f"{field} is required when Answer Type* is {row['Answer Type*']}"
                }
            )

    def handle_nan_values(self, row):
        values = ["Min", "Max", "Alert Below", "Alert Above"]
        for val in values:
            value = row.get(val)
            if value is None or value == "NONE":  # Allow "NONE" and None values
                row[val] = None
                continue
            try:
                row[val] = float(value)  # Convert valid numbers
            except (ValueError, TypeError):
                row[val] = None  # Replace invalid values with None


    def validate_numeric_values(self, row):
        self.handle_nan_values(row)
        min_value = row.get("Min")
        max_value = row.get("Max")
        alert_below = row.get("Alert Below")
        alert_above = row.get("Alert Above")
        if min_value is not None and alert_below is not None:
            if min_value > alert_below:
                raise ValidationError("Alert Below should be greater than Min")

        if max_value is not None and alert_above is not None:
            if max_value < alert_above:
                raise ValidationError("Alert Above should be smaller than Max")

        if alert_above is not None and alert_below is not None:
            if alert_above < alert_below:
                raise ValidationError("Alert Above should be greater than Alert Below")


    def validate_options_values(self, row):
        if row["Answer Type*"] in ["CHECKBOX", "DROPDOWN"]:
            if row.get("Options") is None:
                raise ValidationError(
                    "Options is required when Answer Type* is in [DROPDOWN, CHECKBOX]"
                )
            if row.get("Alert On") and row["Alert On"] not in row["Options"]:
                raise ValidationError({"Alert On": "Alert On needs to be in Options"})

    def set_alert_on_value(self, row):
        if row.get("Answer Type*") == "NUMERIC":
            alert_below = row.get("Alert Below")
            alert_above = row.get("Alert Above")
            if alert_above and alert_below:
                row["Alert On"] = f"<{alert_below}, >{alert_above}"

    def check_unique_record(self, row):
        if (
            Question.objects.select_related()
            .filter(
                quesname=row["Question Name*"],
                answertype=row["Answer Type*"],
                client__bucode=row["Client*"],
            )
            .exists()
        ):
            values = [str(value) if value is not None else "" for value in row.values()]
            raise ValidationError(
                f"Record with these values already exists: {', '.join(values)}"
            )

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    resource_class = QuestionResource
    list_display = ["id", "quesname"]

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {"request": request}

    def get_queryset(self, request):
        return Question.objects.select_related().all()


class QuestionSetResource(resources.ModelResource):

    CLIENT = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )
    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BelongsTo = fields.Field(
        column_name="Belongs To*",
        default=utils.get_or_create_none_qset,
        attribute="parent",
        widget=wg.ForeignKeyWidget(QuestionSet, "qsetname"),
    )

    id = fields.Field(attribute="id", column_name="ID")
    SEQNO = fields.Field(attribute="seqno", column_name="Seq No*", default=-1)
    QSETNAME = fields.Field(attribute="qsetname", column_name="Question Set Name*")
    Type = fields.Field(attribute="type", column_name="QuestionSet Type*")
    ASSETINCLUDES = fields.Field(
        attribute="assetincludes", column_name="Asset Includes", default=[]
    )
    SITEINCLUDES = fields.Field(
        attribute="buincludes", column_name="Site Includes", default=[]
    )
    SITEGRPINCLUDES = fields.Field(
        attribute="site_grp_includes", column_name="Site Group Includes", default=[]
    )
    SITETYPEINCLUDES = fields.Field(
        attribute="site_type_includes", column_name="Site Type Includes", default=[]
    )
    SHOWTOALLSITES = fields.Field(
        attribute="show_to_all_sites", column_name="Show To All Sites", default=False
    )
    URL = fields.Field(attribute="url", column_name="URL", default="NONE")

    class Meta:
        model = QuestionSet
        skip_unchanged = True
        report_skipped = True
        fields = [
            "Question Set Name*",
            "ASSETINCLUDES",
            "SITEINCLUDES",
            "SITEGRPINCLUDES",
            "SITETYPEINCLUDES",
            "SHOWTOALLSITES",
            "URL",
            "BV",
            "CLIENT",
            "Type",
            "BelongsTo",
            "SEQNO",
            "ID",
            "Name",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionSetResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        self.verify_valid_questionset_type(row)
        super().before_import_row(row, **kwargs)

    def verify_valid_questionset_type(self, row):
        Authorized_Questionset_type = [
            "CHECKLIST",
            "RPCHECKLIST",
            "INCIDENTREPORT",
            "SITEREPORT",
            "WORKPERMIT",
            "RETURN_WORK_PERMIT",
            "KPITEMPLATE",
            "SCRAPPEDTEMPLATE",
            "ASSETAUDIT",
            "ASSETMAINTENANCE",
            "WORK_ORDER",
        ]
        questionset_type = row.get("QuestionSet Type*")
        if questionset_type not in Authorized_Questionset_type:
            raise ValidationError(
                {
                    questionset_type: f"{questionset_type} is not a valid Questionset Type. Please select a valid QuestionSet."
                }
            )

    def check_required_fields(self, row):
        required_fields = ["QuestionSet Type*", "Question Set Name*", "Seq No*"]
        for field in required_fields:
            if not row.get(field):
                raise ValidationError({field: f"{field} is a required field"})

        """ optional_fields = ['Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes']
        if all(not row.get(field) for field in optional_fields):
            raise ValidationError("You should provide a value for at least one field from the following: "
                                "'Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes'") """

    def validate_row(self, row):
        models_mapping = {
            "Site Group Includes": ("peoples", "Pgroup", "groupname"),
            "Site Includes": ("onboarding", "Bt", "bucode"),
            "Asset Includes": ("activity", "Asset", "assetcode"),
            "Site Type Includes": ("onboarding", "TypeAssist", "tacode"),
        }

        for field, (app_name, model_name, lookup_field) in models_mapping.items():
            if field_value := row.get(field):
                model = apps.get_model(app_name, model_name)
                values = field_value.replace(" ", "").split(",")
                ids = list(
                    model.objects.filter(**{f"{lookup_field}__in": values}).values_list(
                        "id", flat=True
                    )
                )
                count = model.objects.filter(**{f"{lookup_field}__in": values}).count()
                if len(values) != count:
                    raise ValidationError(
                        {
                            field: f"Some of the values specified in {field} do not exist in the system"
                        }
                    )
                row[field] = ids

    def unique_record_check(self, row):
        # unique record check
        if (
            QuestionSet.objects.select_related()
            .filter(
                qsetname=row["Question Set Name*"],
                type=row["QuestionSet Type*"],
                client__bucode=row["Client*"],
                parent__qsetname=row["Belongs To*"],
                bu__bucode=row["Site*"],
            )
            .exists()
        ):
            raise ValidationError(
                f"Record with these values already exist {row.values()}"
            )

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


class QsetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related("client", "bu").filter(
            client__bucode__exact=row["Client*"],
            bu__bucode__exact=row["Site*"],
            enable=True,
        )


class QuesFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            client__bucode__exact=row["Client*"], enable=True
        )


class QsetFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if "Client" in row and "Site" in row:
            return self.model.objects.select_related("client", "bu").filter(
                client__bucode__exact=row["Client"],
                bu__bucode__exact=row["Site"],
                enable=True,
            )


class QuesFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if "Client" in row:
            return self.model.objects.filter(
                client__bucode__exact=row["Client"], enable=True
            )


class QuestionSetBelongingResource(resources.ModelResource):
    Name = fields.Field(
        column_name="Question Name*",
        attribute="question",
        widget=QuesFKW(Question, "quesname"),
        saves_null_values=True,
        default=utils.get_or_create_none_question,
    )
    QSET = fields.Field(
        column_name="Question Set*",
        attribute="qset",
        widget=QsetFKW(QuestionSet, "qsetname"),
        saves_null_values=True,
        default=utils.get_or_create_none_qset,
    )

    CLIENT = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    ANSTYPE = fields.Field(attribute="answertype", column_name="Answer Type*")
    id = fields.Field(attribute="id", column_name="ID")
    SEQNO = fields.Field(attribute="seqno", column_name="Seq No*")
    ISAVPT = fields.Field(attribute="isavpt", column_name="Is AVPT", default=False)
    AVPTType = fields.Field(
        attribute="avpttype", column_name="AVPT Type", saves_null_values=True
    )
    MIN = fields.Field(attribute="min", column_name="Min")
    ALERTON = fields.Field(attribute="alerton", column_name="Alert On")
    ALERTABOVE = fields.Field(column_name="Alert Above", saves_null_values=True)
    ALERTBELOW = fields.Field(column_name="Alert Below", saves_null_values=True)
    MAX = fields.Field(attribute="max", column_name="Max")
    OPTIONS = fields.Field(attribute="options", column_name="Options")
    ISMANDATORY = fields.Field(
        attribute="ismandatory", column_name="Is Mandatory", default=True
    )

    class Meta:
        model = QuestionSetBelonging
        skip_unchanged = True
        report_skipped = True
        fields = [
            "NAME",
            "QSET",
            "CLIENT",
            "BV",
            "OPTIONS",
            "ISAVPT",
            "AVPTType",
            "ID",
            "MIN",
            "MAX",
            "ISMANDATORY",
            "SEQNO",
            "ANSTYPE",
            "ALERTON",
            "Name",
            "ALERTABOVE",
            "ALERTBELOW",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionSetBelongingResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_unique_record(row)
        self.check_AVPT_fields(row)
        self.check_answertype_fields(row)
        super().before_import_row(row, **kwargs)

    def check_AVPT_fields(self, row):
        valid_avpt = ["BACKCAMPIC", "FRONTCAMPIC", "AUDIO", "VIDEO", "NONE"]
        avpt_type = row.get("AVPT Type")
        if avpt_type and avpt_type != "NONE":
            if avpt_type not in valid_avpt:
                raise ValidationError(
                    {
                        avpt_type: "%(type)s is not a valid AVPT Type. Please select a valid AVPT Type from %(valid)s" % {
                            "type": avpt_type,
                            "valid": valid_avpt
                        }
                    }
                )

    def check_required_fields(self, row):
        required_fields = [
            "Answer Type*",
            "Question Name*",
            "Question Set*",
            "Client*",
            "Site*",
        ]
        for field in required_fields:
            if row.get(field) in ["", None]:
                raise ValidationError(f"{field} is a required field")

    def clean_question_name_and_answer_type(self, row):
        row["Question Name*"] = clean_string(row.get("Question Name*"))
        row["Answer Type*"] = clean_string(row.get("Answer Type*"), code=True)

    def clean_numeric_and_rating_fields(self, row):
        answer_type = row.get("Answer Type*")
        if answer_type in ["NUMERIC", "RATING"]:
            row["Options"] = None
            self.convert_to_float(row, "Min")
            self.convert_to_float(row, "Max")
            self.convert_to_float(row, "Alert Below")
            self.convert_to_float(row, "Alert Above")

    def convert_to_float(self, row, field):
        value = None if str(row.get(field)).strip().upper() == 'NONE' or row.get(field) == '' else float(row.get(field))
        logger.debug("Value: %s %s", value, type(value))
        if value is not None:
            row[field] = float(value)
        elif field in ["Min", "Max"]:
            raise ValidationError(
                f"{field} is required when Answer  Type*  is  {row['Answer  Type*']}"
            )
        
    def parse_float(self,value):
        if str(value).strip().upper() == "NONE" or value == "":
            return None
        return float(value)

    def validate_numeric_values(self, row):
        answer_type = str(row.get("Answer Type*")).strip().upper()
        
        min_value = self.parse_float(row.get("Min"))
        max_value = self.parse_float(row.get("Max"))
        alert_below = self.parse_float(row.get("Alert Below"))
        alert_above = self.parse_float(row.get("Alert Above"))

        # Enforce Min/Max if NUMERIC
        if answer_type == "NUMERIC" or answer_type == 'RATING':
            if min_value is None or max_value is None:
                raise ValidationError("NUMERIC type must have both Min and Max values")

        # Logical consistency checks (only if values are present)
        if min_value is not None and alert_below is not None and min_value > alert_below:
            raise ValidationError("Min should be smaller than Alert Below")
        if max_value is not None and alert_above is not None and max_value < alert_above:
            raise ValidationError("Max should be greater than Alert Above")
        if alert_above is not None and alert_below is not None and alert_above < alert_below:
            raise ValidationError("Alert Above should be greater than Alert Below")
                                                                    
    def set_alert_on_value(self, row):
        if row.get("Answer Type*") == "NUMERIC":
            alert_below = row.get("Alert Below")
            alert_above = row.get("Alert Above")
            if alert_above and alert_below:
                row["Alert On"] = f"<{alert_below}, >{alert_above}"

    def check_unique_record(self, row):
        if (
            QuestionSetBelonging.objects.select_related()
            .filter(
                qset__qsetname=row["Question Set*"],
                question__quesname=row["Question Name*"],
                client__bucode=row["Client*"],
                bu__bucode=row["Site*"],
            )
            .exists()
        ):
            raise ValidationError(
                f"Record with these values already exists: {row.values()}"
            )
        
    def check_answertype_fields(self, row):
        Authorized_AnswerTypes = [
            "DATE",
            "CHECKBOX",
            "MULTISELECT",
            "DROPDOWN",
            "EMAILID",
            "MULTILINE",
            "NUMERIC",
            "SIGNATURE",
            "SINGLELINE",
            "TIME",
            "RATING",
            "PEOPLELIST",
            "SITELIST",
            "METERREADING",
        ]
        Answer_type_val = row.get("Answer Type*")
        if Answer_type_val not in Authorized_AnswerTypes:
            raise ValidationError(
                {
                    Answer_type_val: f"{Answer_type_val} is a not a valid Answertype.Please select a valid AnswerType."
                }
            )

    def validate_options_values(self, row):
        if row["Answer Type*"] in ["CHECKBOX", "DROPDOWN"]:
            if row.get("Options") is None:
                raise ValidationError(
                    "Options is required when Answer Type* is in [DROPDOWN, CHECKBOX]"
                )
            if row.get("Alert On") and row["Alert On"] not in row["Options"]:
                raise ValidationError("Alert On needs to be in Options")

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


class QuestionResourceUpdate(resources.ModelResource):
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

    Client = fields.Field(
        column_name="Client",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    ID = fields.Field(attribute="id", column_name="ID*")
    AlertON = fields.Field(
        attribute="alerton", column_name="Alert On", saves_null_values=True
    )
    ALERTABOVE = fields.Field(column_name="Alert Above", saves_null_values=True)
    ALERTBELOW = fields.Field(column_name="Alert Below", saves_null_values=True)
    Options = fields.Field(
        attribute="options", column_name="Options", saves_null_values=True
    )
    Name = fields.Field(attribute="quesname", column_name="Question Name")
    Type = fields.Field(attribute="answertype", column_name="Answer Type")
    Min = fields.Field(attribute="min", column_name="Min", saves_null_values=True)
    Max = fields.Field(attribute="max", column_name="Max", saves_null_values=True)
    Enable = fields.Field(
        attribute="enable",
        column_name="Enable",
        default=True,
        widget=wg.BooleanWidget(),
    )
    IsAvpt = fields.Field(
        attribute="isavpt",
        column_name="Is AVPT",
        default=False,
        widget=wg.BooleanWidget(),
    )
    AttType = fields.Field(
        attribute="avpttype", column_name="AVPT Type", saves_null_values=True
    )
    isworkflow = fields.Field(
        attribute="isworkflow", column_name="Is WorkFlow", default=False
    )

    class Meta:
        model = Question
        skip_unchanged = True
        report_skipped = True
        fields = [
            "Name",
            "Type",
            "Unit",
            "Options",
            "Enable",
            "IsAvpt",
            "AttType",
            "ID",
            "Client",
            "Min",
            "Max",
            "AlertON",
            "isworkflow",
            "Category",
            "ALERTABOVE",
            "ALERTBELOW",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.handle_nan_values(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.check_answertype_fields(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_record_exists(row)
        super().before_import_row(row, **kwargs)

    def check_answertype_fields(self, row):
        if "Answer Type" in row:
            Authorized_AnswerTypes = [
                "DATE",
                "CHECKBOX",
                "MULTISELECT",
                "DROPDOWN",
                "EMAILID",
                "MULTILINE",
                "NUMERIC",
                "SIGNATURE",
                "SINGLELINE",
                "TIME",
                "RATING",
                "PEOPLELIST",
                "SITELIST",
                "METERREADING",
            ]
            Answer_type_val = row.get("Answer Type")
            if Answer_type_val not in Authorized_AnswerTypes:
                raise ValidationError(
                    {
                        Answer_type_val: f"{Answer_type_val} is a not a valid Answertype.Please select a valid AnswerType."
                    }
                )

    def check_required_fields(self, row):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        required_fields = ['Answer Type', 'Question Name',  'Client']
        for field in required_fields:
            if field in row:
                if row.get(field) in ["", None]:
                    raise ValidationError({field: f"{field} is a required field"})

    def clean_question_name_and_answer_type(self, row):
        if "Question Name" in row:
            row["Question Name"] = clean_string(row.get("Question Name"))
        if "Answer Type" in row:
            row["Answer Type"] = clean_string(row.get("Answer Type"), code=True)

    def clean_numeric_and_rating_fields(self, row):
        if "Answer Type" in row:
            answer_type = row.get("Answer Type")
            if answer_type in ["NUMERIC", "RATING"]:
                if "Options" in row:
                    row["Options"] = None
                if "Min" in row:
                    self.convert_to_float(row, "Min")
                if "Max" in row:
                    self.convert_to_float(row, "Max")
                if "Alert Below" in row:
                    self.convert_to_float(row, "Alert Below")
                if "Alert Above" in row:
                    self.convert_to_float(row, "Alert Above")

    def convert_to_float(self, row, field):
        value = row.get(field)
        if value is not None and value != "NONE":
            row[field] = float(value)
        elif field in ["Min", "Max"]:
            raise ValidationError(
                {field: f"{field} is required when Answer Type is {row['Answer Type']}"}
            )

    def handle_nan_values(self, row):
        values = ["Min", "Max", "Alert Below", "Alert Above"]
        for val in values:
            if val in row:
                if type(row.get(val)) == int:
                    continue
                elif row.get(val) == None:
                    continue
                elif row.get(val) == "NONE":
                    continue
                elif isnan(row.get(val)):
                    row[val] = None

    def validate_numeric_values(self, row):
        if "Min" in row and "Alert Below" in row:
            min_value = row.get("Min")
            alert_below = row.get("Alert Below")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if min_value and alert_below and float(min_value) > float(alert_below):
                    raise ValidationError("Alert Below should be greater than Min")
        if "Max" in row and "Alert Above" in row:
            max_value = row.get("Max")
            alert_above = row.get("Alert Above")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if max_value and alert_above and float(max_value) < float(alert_above):
                    raise ValidationError("Alert Above should be smaller than Max")
        if "Alert Below" in row and "Alert Above" in row:
            alert_below = row.get("Alert Below")
            alert_above = row.get("Alert Above")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if (
                    alert_above
                    and alert_below
                    and float(alert_above) < float(alert_below)
                ):
                    raise ValidationError(
                        "Alert Above should be greater than Alert Below"
                    )

    def validate_options_values(self, row):
        if "Answer Type" in row:
            if row["Answer Type"] in ["CHECKBOX", "DROPDOWN"]:
                if "Options" in row:
                    if row.get("Options") is None:
                        raise ValidationError(
                            "Options is required when Answer Type is in [DROPDOWN, CHECKBOX]"
                        )
                if "Alert On" in row and "Options" in row:
                    if row.get("Alert On") and row["Alert On"] not in row["Options"]:
                        raise ValidationError(
                            {"Alert On": "Alert On needs to be in Options"}
                        )

    def set_alert_on_value(self, row):
        if "Answer Type" in row:
            if row.get("Answer Type") == "NUMERIC":
                if "Alert Below" in row and "Alert Above" in row and "Alert On" in row:
                    alert_below = row.get("Alert Below")
                    alert_above = row.get("Alert Above")
                    alert_below_str = (
                        "null"
                        if alert_below is None
                        or alert_below == ""
                        or (isinstance(alert_below, float) and isnan(alert_below))
                        else alert_below
                    )
                    alert_above_str = (
                        "null"
                        if alert_above is None
                        or alert_above == ""
                        or (isinstance(alert_above, float) and isnan(alert_above))
                        else alert_above
                    )
                    if alert_above_str != "null" and alert_below_str != "null":
                        row["Alert On"] = f"<{alert_below_str}, >{alert_above_str}"
                    else:
                        row["Alert On"] = None
                else:
                    raise ValidationError(
                        "Alert Above, Alert Below and Alert On Field is required"
                    )

    def check_record_exists(self, row):
        if not Question.objects.filter(id=row["ID*"]).exists():
            raise ValidationError(
                f"Record with these values not exist: ID - {row['ID*']}"
            )

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


class QuestionSetBelongingResourceUpdate(resources.ModelResource):
    Name = fields.Field(
        column_name="Question Name",
        attribute="question",
        widget=QuesFKWUpdate(Question, "quesname"),
        saves_null_values=True,
        default=utils.get_or_create_none_question,
    )

    QSET = fields.Field(
        column_name="Question Set",
        attribute="qset",
        widget=QsetFKWUpdate(QuestionSet, "qsetname"),
        saves_null_values=True,
        default=utils.get_or_create_none_qset,
    )

    CLIENT = fields.Field(
        column_name="Client",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BV = fields.Field(
        column_name="Site",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    ANSTYPE = fields.Field(attribute="answertype", column_name="Answer Type")
    ID = fields.Field(attribute="id", column_name="ID*")
    SEQNO = fields.Field(attribute="seqno", column_name="Seq No")
    ISAVPT = fields.Field(attribute="isavpt", column_name="Is AVPT", default=False)
    AVPTType = fields.Field(attribute="avpttype", column_name="AVPT Type", saves_null_values=True)
    MIN = fields.Field(attribute="min", column_name="Min")
    ALERTON = fields.Field(attribute="alerton", column_name="Alert On")
    ALERTABOVE = fields.Field(column_name="Alert Above", saves_null_values=True)
    ALERTBELOW = fields.Field(column_name="Alert Below", saves_null_values=True)
    MAX = fields.Field(attribute="max", column_name="Max")
    OPTIONS = fields.Field(attribute="options", column_name="Options")
    ISMANDATORY = fields.Field(attribute="ismandatory", column_name="Is Mandatory", default=True)

    class Meta:
        model = QuestionSetBelonging
        skip_unchanged = True
        report_skipped = True
        fields = [
            "NAME",
            "QSET",
            "CLIENT",
            "BV",
            "OPTIONS",
            "ISAVPT",
            "AVPTType",
            "ID",
            "MIN",
            "MAX",
            "ISMANDATORY",
            "SEQNO",
            "ANSTYPE",
            "ALERTON",
            "Name",
            "ALERTABOVE",
            "ALERTBELOW",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionSetBelongingResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_record_exists(row)
        self.check_AVPT_fields(row)
        super().before_import_row(row, **kwargs)

    def check_AVPT_fields(self, row):
        if "AVPT Type" in row:
            valid_avpt = ["BACKCAMPIC", "FRONTCAMPIC", "AUDIO", "VIDEO", "NONE"]
            avpt_type = row.get("AVPT Type")
            if avpt_type and avpt_type != "NONE":
                if avpt_type not in valid_avpt:
                    raise ValidationError(
                        {
                            avpt_type: "%(type)s is not a valid AVPT Type. Please select a valid AVPT Type from %(valid)s" % {
                                "type": avpt_type,
                                "valid": valid_avpt
                            }
                        }
                    )

    def check_required_fields(self, row):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        required_fields = ['Answer Type', 'Question Name', 'Question Set', 'Client', 'Site']
        for field in required_fields:
            if field in row:
                if row.get(field) in ["", None]:
                    raise ValidationError(f"{field} is a required field")

    def clean_question_name_and_answer_type(self, row):
        if "Question Name" in row:
            row["Question Name"] = clean_string(row.get("Question Name"))
        if "Answer Type" in row:
            row["Answer Type"] = clean_string(row.get("Answer Type"), code=True)

    def clean_numeric_and_rating_fields(self, row):
        if "Answer Type" in row:
            answer_type = row.get("Answer Type")
            if answer_type in ["NUMERIC", "RATING"]:
                if "Options" in row:
                    row["Options"] = None
                if "Min" in row:
                    self.convert_to_float(row, "Min")
                if "Max" in row:
                    self.convert_to_float(row, "Max")
                if "Alert Below" in row:
                    self.convert_to_float(row, "Alert Below")
                if "Alert Above" in row:
                    self.convert_to_float(row, "Alert Above")

    def convert_to_float(self, row, field):
        value = row.get(field)
        if value is not None and value != "NONE":
            row[field] = float(value)
        elif field in ["Min", "Max"]:
            raise ValidationError(
                f"{field} is required when Answer Type is {row['Answer Type']}"
            )

    def validate_numeric_values(self, row):
        if "Min" in row and "Alert Below" in row:
            min_value = row.get("Min")
            alert_below = row.get("Alert Below")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if min_value and alert_below and float(min_value) > float(alert_below):
                    raise ValidationError("Alert Below should be greater than Min")
        if "Max" in row and "Alert Above" in row:
            max_value = row.get("Max")
            alert_above = row.get("Alert Above")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if max_value and alert_above and float(max_value) < float(alert_above):
                    raise ValidationError("Alert Above should be smaller than Max")
        if "Alert Below" in row and "Alert Above" in row:
            alert_below = row.get("Alert Below")
            alert_above = row.get("Alert Above")
            if isinstance(alert_below, (int, float)) and isinstance(
                alert_below, (int, float)
            ):
                if (
                    alert_above
                    and alert_below
                    and float(alert_above) < float(alert_below)
                ):
                    raise ValidationError(
                        "Alert Above should be greater than Alert Below"
                    )

    def set_alert_on_value(self, row):
        if "Answer Type" in row:
            if row.get("Answer Type") == "NUMERIC":
                if "Alert Below" in row and "Alert Above" in row and "Alert On" in row:
                    alert_below = row.get("Alert Below")
                    alert_above = row.get("Alert Above")
                    alert_below_str = (
                        "null"
                        if alert_below is None
                        or alert_below == ""
                        or (isinstance(alert_below, float) and isnan(alert_below))
                        else alert_below
                    )
                    alert_above_str = (
                        "null"
                        if alert_above is None
                        or alert_above == ""
                        or (isinstance(alert_above, float) and isnan(alert_above))
                        else alert_above
                    )
                    if alert_above_str != "null" and alert_below_str != "null":
                        row["Alert On"] = f"<{alert_below_str}, >{alert_above_str}"
                    else:
                        row["Alert On"] = None
                else:
                    raise ValidationError(
                        "Alert Above, Alert Below and Alert On Field is required"
                    )

    def check_record_exists(self, row):
        if not QuestionSetBelonging.objects.filter(id=row["ID*"]).exists():
            raise ValidationError(
                f"Record with these values not exist: ID - {row['ID*']}"
            )

    def validate_options_values(self, row):
        if "Answer Type" in row:
            if row["Answer Type"] in ["CHECKBOX", "DROPDOWN"]:
                if "Options" in row:
                    if row.get("Options") is None:
                        raise ValidationError(
                            "Options is required when Answer Type is in [DROPDOWN, CHECKBOX]"
                        )
                if "Alert On" in row and "Options" in row:
                  if row.get("Alert On"):
                    # Convert comma-separated strings to lists
                    alert_on_list = [item.strip() for item in row["Alert On"].split(',') if item.strip()]
                    options_list = [item.strip() for item in row["Options"].split(',') if item.strip()]
                    invalid_items = [item for item in alert_on_list if item not in options_list]
                    if invalid_items:
                        raise ValidationError(
                            {"Alert On": f"The following items are not in Options: {', '.join(invalid_items)}"}
                        )

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


class QuestionSetResourceUpdate(resources.ModelResource):
    CLIENT = fields.Field(
        column_name="Client",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BV = fields.Field(
        column_name="Site",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )

    BelongsTo = fields.Field(
        column_name = 'Belongs To',
        default = utils.get_or_create_none_qset,
        attribute = 'parent',
        widget = wg.ForeignKeyWidget(QuestionSet, 'qsetname'))
    
    ID               = fields.Field(attribute='id', column_name='ID*')
    SEQNO            = fields.Field(attribute='seqno', column_name="Seq No",default=-1)
    QSETNAME         = fields.Field(attribute='qsetname', column_name='Question Set Name')
    Type             = fields.Field(attribute='type', column_name='QuestionSet Type')
    ASSETINCLUDES    = fields.Field(attribute='assetincludes', column_name='Asset Includes', default=[])
    SITEINCLUDES     = fields.Field(attribute='buincludes', column_name='Site Includes', default=[])
    SITEGRPINCLUDES  = fields.Field(attribute='site_grp_includes', column_name='Site Group Includes', default=[])
    SITETYPEINCLUDES = fields.Field(attribute='site_type_includes', column_name='Site Type Includes', default=[])
    SHOWTOALLSITES   = fields.Field(attribute='show_to_all_sites', column_name='Show To All Sites', default=False)
    URL              = fields.Field(attribute='url', column_name='URL', default='NONE')
    
    class Meta:
        model = QuestionSet
        skip_unchanged = True
        report_skipped = True
        fields = [
            "ID",
            "Question Set Name",
            "ASSETINCLUDES",
            "SITEINCLUDES",
            "SITEGRPINCLUDES",
            "SITETYPEINCLUDES",
            "SHOWTOALLSITES",
            "URL",
            "BV",
            "CLIENT",
            "Type",
            "BelongsTo",
            "SEQNO",
        ]

    def __init__(self, *args, **kwargs):
        super(QuestionSetResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop("is_superuser", None)
        self.request = kwargs.pop("request", None)

    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.check_record_exists(row)
        self.verify_valid_questionset_type(row)
        super().before_import_row(row, **kwargs)

    def verify_valid_questionset_type(self, row):
        if "QuestionSet Type" in row:
            Authorized_Questionset_type = [
                "CHECKLIST",
                "RPCHECKLIST",
                "INCIDENTREPORT",
                "SITEREPORT",
                "WORKPERMIT",
                "RETURN_WORK_PERMIT",
                "KPITEMPLATE",
                "SCRAPPEDTEMPLATE",
                "ASSETAUDIT",
                "ASSETMAINTENANCE",
                "WORK_ORDER",
            ]
            questionset_type = row.get("QuestionSet Type")
            if questionset_type not in Authorized_Questionset_type:
                raise ValidationError(
                    {
                        questionset_type: f"{questionset_type} is not a valid Questionset Type. Please select a valid QuestionSet."
                    }
                )

    def check_required_fields(self, row):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        required_fields = ['QuestionSet Type', 'Question Set Name','Seq No']
        for field in required_fields:
            if field in row:
                if not row.get(field):
                    raise ValidationError({field: f"{field} is a required field"})

        """ optional_fields = ['Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes']
        if all(not row.get(field) for field in optional_fields):
            raise ValidationError("You should provide a value for at least one field from the following: "
                                "'Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes'") """

    def validate_row(self, row):
        models_mapping = {
            "Site Group Includes": ("peoples", "Pgroup", "id", "groupname"),
            "Site Includes": ("onboarding", "Bt", "id", "bucode"),
            "Asset Includes": ("activity", "Asset", "id", "assetcode"),
            "Site Type Includes": ("onboarding", "TypeAssist", "id", "tacode"),
        }

        for field, (
            app_name,
            model_name,
            lookup_field,
            model_field,
        ) in models_mapping.items():
            if field_value := row.get(field):
                model = apps.get_model(app_name, model_name)
                values = field_value.split(",")
                list_value = []
                for val in values:
                    get_value = list(
                        model.objects.filter(**{f"{model_field}": val}).values()
                    )
                    list_value.append(str(get_value[0]["id"]))
                count = model.objects.filter(
                    **{f"{lookup_field}__in": list_value}
                ).count()
                if len(values) != count:
                    raise ValidationError(
                        {
                            field: f"Some of the values specified in {field} do not exist in the system"
                        }
                    )
                row[field] = list_value

    def check_record_exists(self, row):
        if not QuestionSet.objects.select_related().filter(id=row["ID*"]).exists():
            raise ValidationError(
                f"Record with these values not exist: ID - {row['ID*']}"
            )

    def before_save_instance(self, instance, row, **kwargs):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
