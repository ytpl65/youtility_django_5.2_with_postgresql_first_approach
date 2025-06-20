import pytest
from apps.activity.models.attachment_model import Attachment
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from apps.onboarding.models import TypeAssist
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_create_minimal_attachment(client_bt, bu_bt):
    uploaded_file = SimpleUploadedFile("default.jpg", b"file_content",content_type="image/jpeg")
    typeassist = TypeAssist.objects.create(tacode="TEST", taname="Test")
    attachment  = Attachment.objects.create(
        filepath="youtility4_media",
        filename=uploaded_file,
        ownername=typeassist,
        owner="None",
        bu=bu_bt
    )
    assert attachment.uuid is not None

