import pytest
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging


@pytest.mark.django_db
def test_create_minimal_question():
    question = Question.objects.create(
        quesname="Test Question",
        enable=True,
        answertype="NUMERIC",
        isavpt=True
    )
    assert str(question) == "Test Question | NUMERIC"


@pytest.mark.django_db
def test_create_minimal_questionset(client_bt, bu_bt):
    questionset = QuestionSet.objects.create(
        qsetname="Test Question Set",
        enable=True,
        client=client_bt,
        bu=bu_bt,
        seqno=1,
        show_to_all_sites=True,
    )
    assert str(questionset) == "Test Question Set"


@pytest.mark.django_db
def test_create_minimal_questionsetbelonging(client_bt, bu_bt):
    questionsetbelonging = QuestionSetBelonging.objects.create(
        qset=QuestionSet.objects.create(qsetname="Test Question Set", enable=True, client=client_bt, bu=bu_bt, seqno=1, show_to_all_sites=True),
        question=Question.objects.create(quesname="Test Question", enable=True, client=client_bt,answertype="NUMERIC", isavpt=True),
        client=client_bt,
        bu=bu_bt,
        seqno=1,
        isavpt=True,
        avpttype="VIDEO",
        answertype="NUMERIC"
    )
    assert str(questionsetbelonging) == "NUMERIC"
