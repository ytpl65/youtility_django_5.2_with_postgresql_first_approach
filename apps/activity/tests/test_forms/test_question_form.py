import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import patch
from apps.activity.forms.question_form import QuestionForm

@pytest.fixture
def request_with_session(client_bt):
    rf = RequestFactory()
    request = rf.post("/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.session['client_id'] = client_bt.id
    request.session['bu_id'] = client_bt.id
    request.user = get_user_model()()
    request.user.id = 1
    return request

@pytest.mark.django_db
def test_question_form_valid(request_with_session):
    form = QuestionForm(
        data={
            'quesname': 'Voltage Level',
            'answertype': 'NUMERIC',
            'min': 1,
            'max': 10,
            'ctzoffset': -1
        },
        request=request_with_session
    )
    assert form.is_valid(), form.errors

