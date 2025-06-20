import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from datetime import datetime
from apps.activity.models.question_model import QuestionSet, Question, QuestionSetBelonging
from apps.onboarding.models import Bt
from apps.peoples.models import People

@pytest.fixture
def session_request(rf):
    bt = Bt.objects.create(bucode='TEST', buname='Test BU', enable=True)
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.session['client_id'] = bt.id
    request.session['bu_id'] = bt.id
    request.session['assignedsites'] = [bt.id]
    request.user = People.objects.create(
        peoplename="TestUser", email="test@example.com",
        client=bt, bu=bt,
        dateofbirth="2000-01-01", dateofjoin="2020-01-01", dateofreport="2020-01-01"
    )
    return request

@pytest.mark.django_db
def test_get_template_list():
    qset = QuestionSet.objects.create(qsetname='Template1', enable=True, buincludes=[1])
    result = QuestionSet.objects.get_template_list('1')
    assert qset.id in result

@pytest.mark.django_db
def test_questions_of_client(session_request):
    q = Question.objects.create(quesname="Test Question", client_id=session_request.session['client_id'])
    session_request.GET = {'search': 'Test'}
    result = Question.objects.questions_of_client(session_request, session_request.GET)
    assert result[0]['id'] == q.id

@pytest.mark.django_db
def test_get_questions_of_qset(session_request):
    qset = QuestionSet.objects.create(qsetname="QSet1", client_id=session_request.session['client_id'], bu_id=session_request.session['bu_id'])
    question = Question.objects.create(quesname="Q1", client_id=session_request.session['client_id'])
    qsb = QuestionSetBelonging.objects.create(
        qset=qset, question=question, client_id=session_request.session['client_id'],
        bu_id=session_request.session['bu_id'], cuser=session_request.user, muser=session_request.user,
        ctzoffset=0, seqno=1,cdtz=datetime.now(), mdtz=datetime.now()
    )
    data = {'qset_id': qset.id}
    result = QuestionSetBelonging.objects.get_questions_of_qset(data)
    assert result[0]['quesname'] == "Q1"

