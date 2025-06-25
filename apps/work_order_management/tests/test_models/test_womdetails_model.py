"""
Tests for WomDetails model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from apps.work_order_management.models import WomDetails


@pytest.mark.django_db
class TestWomDetailsModel:
    """Test suite for WomDetails model"""
    
    def test_womdetails_creation_basic(self, womdetails_factory):
        """Test creating a basic WomDetails instance"""
        womdetails = womdetails_factory()
        
        assert womdetails.uuid is not None
        assert womdetails.seqno is not None
        assert womdetails.question is not None
        assert womdetails.answertype is not None
        assert womdetails.answer is not None
        assert womdetails.isavpt is False
        assert womdetails.ismandatory is True
        assert womdetails.alerts is False
        assert womdetails.attachmentcount == 0
    
    
    def test_womdetails_answer_type_choices(self, womdetails_factory, answer_types):
        """Test WomDetails answer type choices"""
        for answer_type in answer_types[:5]:  # Test first 5 to avoid too many objects
            womdetails = womdetails_factory(
                answertype=answer_type,
                answer=f'Test answer for {answer_type}'
            )
            assert womdetails.answertype == answer_type
    
    
    def test_womdetails_avpt_type_choices(self, womdetails_factory, attachment_types):
        """Test WomDetails attachment type choices"""
        for avpt_type in attachment_types:
            womdetails = womdetails_factory(
                isavpt=True if avpt_type != WomDetails.AvptType.NONE else False,
                avpttype=avpt_type
            )
            assert womdetails.avpttype == avpt_type
    
    
    def test_womdetails_relationships(self, womdetails_factory, wom_factory, test_question, test_questionset):
        """Test WomDetails foreign key relationships"""
        wom = wom_factory()
        
        womdetails = womdetails_factory(
            wom=wom,
            question=test_question,
            qset=test_questionset
        )
        
        # Test forward relationships
        assert womdetails.wom == wom
        assert womdetails.question == test_question
        assert womdetails.qset == test_questionset
        
        # Test reverse relationships
        assert womdetails in wom.womdetails_set.all()
        assert womdetails in test_questionset.qset_answers.all()
    
    
    def test_womdetails_unique_constraint(self, womdetails_factory, wom_factory, test_question):
        """Test WomDetails unique constraint on question, wom"""
        wom = wom_factory()
        
        # Create first WomDetails
        womdetails1 = womdetails_factory(
            question=test_question,
            wom=wom
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            womdetails_factory(
                question=test_question,
                wom=wom
            )
    
    
    def test_womdetails_numeric_answer_with_min_max(self, womdetails_factory):
        """Test WomDetails numeric answer with min/max validation"""
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.NUMERIC,
            answer='75',
            min=Decimal('0.0'),
            max=Decimal('100.0')
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.NUMERIC
        assert womdetails.answer == '75'
        assert womdetails.min == Decimal('0.0')
        assert womdetails.max == Decimal('100.0')
    
    
    def test_womdetails_rating_answer(self, womdetails_factory):
        """Test WomDetails rating answer type"""
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.RATING,
            answer='4',
            min=Decimal('1.0'),
            max=Decimal('5.0'),
            options='1,2,3,4,5'
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.RATING
        assert womdetails.answer == '4'
        assert womdetails.options == '1,2,3,4,5'
    
    
    def test_womdetails_dropdown_with_options(self, womdetails_factory):
        """Test WomDetails dropdown with options"""
        options = 'Option A,Option B,Option C,Option D'
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.DROPDOWN,
            answer='Option B',
            options=options
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.DROPDOWN
        assert womdetails.answer == 'Option B'
        assert womdetails.options == options
    
    
    def test_womdetails_multiselect_answer(self, womdetails_factory):
        """Test WomDetails multiselect answer type"""
        options = 'Red,Green,Blue,Yellow,Orange'
        selected_answers = 'Red,Blue,Yellow'
        
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.MULTISELECT,
            answer=selected_answers,
            options=options
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.MULTISELECT
        assert womdetails.answer == selected_answers
        assert womdetails.options == options
    
    
    def test_womdetails_checkbox_answer(self, womdetails_factory):
        """Test WomDetails checkbox answer type"""
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.CHECKBOX,
            answer='true',
            options='true,false'
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.CHECKBOX
        assert womdetails.answer == 'true'
    
    
    def test_womdetails_date_time_answers(self, womdetails_factory):
        """Test WomDetails date and time answer types"""
        # Date answer
        date_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.DATE,
            answer='2024-01-15'
        )
        
        # Time answer
        time_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.TIME,
            answer='14:30:00'
        )
        
        assert date_womdetails.answertype == WomDetails.AnswerType.DATE
        assert date_womdetails.answer == '2024-01-15'
        
        assert time_womdetails.answertype == WomDetails.AnswerType.TIME
        assert time_womdetails.answer == '14:30:00'
    
    
    def test_womdetails_text_answer_types(self, womdetails_factory):
        """Test WomDetails text-based answer types"""
        # Single line text
        singleline_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='Short text answer'
        )
        
        # Multi line text
        multiline_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.MULTILINE,
            answer='This is a longer text answer\nthat spans multiple lines\nwith detailed information'
        )
        
        # Email answer
        email_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.EMAILID,
            answer='user@example.com'
        )
        
        assert singleline_womdetails.answertype == WomDetails.AnswerType.SINGLELINE
        assert singleline_womdetails.answer == 'Short text answer'
        
        assert multiline_womdetails.answertype == WomDetails.AnswerType.MULTILINE
        assert 'multiple lines' in multiline_womdetails.answer
        
        assert email_womdetails.answertype == WomDetails.AnswerType.EMAILID
        assert email_womdetails.answer == 'user@example.com'
    
    
    def test_womdetails_camera_attachment_types(self, womdetails_factory):
        """Test WomDetails camera attachment types"""
        # Back camera
        back_camera_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.BACKCAMERA,
            isavpt=True,
            avpttype=WomDetails.AvptType.BACKCAMPIC,
            attachmentcount=1
        )
        
        # Front camera
        front_camera_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.FRONTCAMERA,
            isavpt=True,
            avpttype=WomDetails.AvptType.FRONTCAMPIC,
            attachmentcount=1
        )
        
        assert back_camera_womdetails.answertype == WomDetails.AnswerType.BACKCAMERA
        assert back_camera_womdetails.avpttype == WomDetails.AvptType.BACKCAMPIC
        assert back_camera_womdetails.isavpt is True
        
        assert front_camera_womdetails.answertype == WomDetails.AnswerType.FRONTCAMERA
        assert front_camera_womdetails.avpttype == WomDetails.AvptType.FRONTCAMPIC
        assert front_camera_womdetails.isavpt is True
    
    
    def test_womdetails_audio_video_attachments(self, womdetails_factory):
        """Test WomDetails audio and video attachment types"""
        # Audio attachment
        audio_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='Audio recording description',
            isavpt=True,
            avpttype=WomDetails.AvptType.AUDIO,
            attachmentcount=1
        )
        
        # Video attachment
        video_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='Video recording description',
            isavpt=True,
            avpttype=WomDetails.AvptType.VIDEO,
            attachmentcount=1
        )
        
        assert audio_womdetails.avpttype == WomDetails.AvptType.AUDIO
        assert audio_womdetails.isavpt is True
        
        assert video_womdetails.avpttype == WomDetails.AvptType.VIDEO
        assert video_womdetails.isavpt is True
    
    
    def test_womdetails_list_answer_types(self, womdetails_factory):
        """Test WomDetails list-based answer types"""
        # People list
        people_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.PEOPLELIST,
            answer='John Doe,Jane Smith,Bob Johnson',
            options='Available people list'
        )
        
        # Site list
        site_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SITELIST,
            answer='Site A,Site B,Site C',
            options='Available sites list'
        )
        
        assert people_womdetails.answertype == WomDetails.AnswerType.PEOPLELIST
        assert 'John Doe' in people_womdetails.answer
        
        assert site_womdetails.answertype == WomDetails.AnswerType.SITELIST
        assert 'Site A' in site_womdetails.answer
    
    
    def test_womdetails_signature_answer(self, womdetails_factory):
        """Test WomDetails signature answer type"""
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SIGNATURE,
            answer='Digital signature data',
            isavpt=True,
            attachmentcount=1
        )
        
        assert womdetails.answertype == WomDetails.AnswerType.SIGNATURE
        assert womdetails.answer == 'Digital signature data'
        assert womdetails.isavpt is True
    
    
    def test_womdetails_mandatory_optional_fields(self, womdetails_factory):
        """Test WomDetails mandatory and optional field handling"""
        # Mandatory field
        mandatory_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='Required answer',
            ismandatory=True
        )
        
        # Optional field
        optional_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='',  # Empty answer for optional field
            ismandatory=False
        )
        
        assert mandatory_womdetails.ismandatory is True
        assert mandatory_womdetails.answer == 'Required answer'
        
        assert optional_womdetails.ismandatory is False
        assert optional_womdetails.answer == ''
    
    
    def test_womdetails_alert_configuration(self, womdetails_factory):
        """Test WomDetails alert configuration"""
        womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.NUMERIC,
            answer='85',
            min=Decimal('0.0'),
            max=Decimal('100.0'),
            alerton='value_exceeds_80',
            alerts=True
        )
        
        assert womdetails.alerts is True
        assert womdetails.alerton == 'value_exceeds_80'
        assert float(womdetails.answer) > 80  # Alert condition met
    
    
    def test_womdetails_sequence_ordering(self, womdetails_factory, wom_factory):
        """Test WomDetails sequence ordering"""
        wom = wom_factory()
        
        # Create details with different sequence numbers
        womdetails_1 = womdetails_factory(
            wom=wom,
            seqno=1,
            answer='First question'
        )
        
        womdetails_3 = womdetails_factory(
            wom=wom,
            seqno=3,
            answer='Third question'
        )
        
        womdetails_2 = womdetails_factory(
            wom=wom,
            seqno=2,
            answer='Second question'
        )
        
        # Test ordering by sequence number
        ordered_details = WomDetails.objects.filter(wom=wom).order_by('seqno')
        ordered_list = list(ordered_details)
        
        assert ordered_list[0] == womdetails_1
        assert ordered_list[1] == womdetails_2
        assert ordered_list[2] == womdetails_3
    
    
    def test_womdetails_bulk_operations(self, womdetails_factory, wom_factory):
        """Test bulk operations on WomDetails"""
        wom = wom_factory()
        
        # Create multiple womdetails records
        womdetails_list = []
        for i in range(10):
            womdetails = womdetails_factory(
                wom=wom,
                seqno=i + 1,
                answertype=WomDetails.AnswerType.SINGLELINE if i % 2 == 0 else WomDetails.AnswerType.NUMERIC,
                answer=f'Answer {i}',
                ismandatory=True if i % 3 == 0 else False
            )
            womdetails_list.append(womdetails)
        
        # Test bulk filtering
        singleline_details = WomDetails.objects.filter(
            wom=wom,
            answertype=WomDetails.AnswerType.SINGLELINE
        )
        numeric_details = WomDetails.objects.filter(
            wom=wom,
            answertype=WomDetails.AnswerType.NUMERIC
        )
        
        assert singleline_details.count() == 5
        assert numeric_details.count() == 5
        
        # Test mandatory field filtering
        mandatory_details = WomDetails.objects.filter(
            wom=wom,
            ismandatory=True
        )
        assert mandatory_details.count() == 4  # Positions 0, 3, 6, 9
        
        # Test bulk update
        WomDetails.objects.filter(
            wom=wom
        ).update(alerts=True)
        
        # Verify bulk update
        updated_details = WomDetails.objects.filter(
            wom=wom,
            alerts=True
        )
        assert updated_details.count() == 10
    
    
    def test_womdetails_attachment_handling(self, womdetails_factory):
        """Test WomDetails attachment handling"""
        # Question with multiple attachments
        multi_attachment_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.MULTILINE,
            answer='Work progress description',
            isavpt=True,
            avpttype=WomDetails.AvptType.BACKCAMPIC,
            attachmentcount=3
        )
        
        # Question without attachments
        no_attachment_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.SINGLELINE,
            answer='Simple text answer',
            isavpt=False,
            avpttype=WomDetails.AvptType.NONE,
            attachmentcount=0
        )
        
        assert multi_attachment_womdetails.isavpt is True
        assert multi_attachment_womdetails.attachmentcount == 3
        
        assert no_attachment_womdetails.isavpt is False
        assert no_attachment_womdetails.attachmentcount == 0
    
    
    def test_womdetails_validation_scenarios(self, womdetails_factory):
        """Test WomDetails validation scenarios"""
        # Numeric validation with range
        numeric_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.NUMERIC,
            answer='75.5',
            min=Decimal('0.0'),
            max=Decimal('100.0'),
            alerton='value_exceeds_threshold'
        )
        
        # Rating validation
        rating_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.RATING,
            answer='4',
            min=Decimal('1.0'),
            max=Decimal('5.0'),
            options='1,2,3,4,5'
        )
        
        # Email validation
        email_womdetails = womdetails_factory(
            answertype=WomDetails.AnswerType.EMAILID,
            answer='test@example.com'
        )
        
        # Verify numeric range
        assert Decimal(numeric_womdetails.answer) >= numeric_womdetails.min
        assert Decimal(numeric_womdetails.answer) <= numeric_womdetails.max
        
        # Verify rating range
        assert Decimal(rating_womdetails.answer) >= rating_womdetails.min
        assert Decimal(rating_womdetails.answer) <= rating_womdetails.max
        
        # Verify email format (basic check)
        assert '@' in email_womdetails.answer
        assert '.' in email_womdetails.answer
    
    
    def test_womdetails_performance_queries(self, womdetails_factory, wom_factory):
        """Test performance-oriented queries on WomDetails"""
        wom = wom_factory()
        
        # Create many womdetails records for performance testing
        womdetails_list = []
        answer_types = [
            WomDetails.AnswerType.SINGLELINE,
            WomDetails.AnswerType.NUMERIC,
            WomDetails.AnswerType.DROPDOWN,
            WomDetails.AnswerType.CHECKBOX
        ]
        
        for i in range(50):
            answer_type = answer_types[i % len(answer_types)]
            womdetails = womdetails_factory(
                wom=wom,
                seqno=i + 1,
                answertype=answer_type,
                answer=f'Performance Answer {i}',
                ismandatory=True if i % 5 == 0 else False,
                isavpt=True if i % 7 == 0 else False
            )
            womdetails_list.append(womdetails)
        
        # Test count queries
        total_count = WomDetails.objects.filter(wom=wom).count()
        assert total_count == 50
        
        # Test answer type filtering
        for answer_type in answer_types:
            type_count = WomDetails.objects.filter(
                wom=wom,
                answertype=answer_type
            ).count()
            assert type_count > 0  # Each type should have some records
        
        # Test mandatory field count
        mandatory_count = WomDetails.objects.filter(
            wom=wom,
            ismandatory=True
        ).count()
        assert mandatory_count == 10  # Every 5th record
        
        # Test attachment count
        attachment_count = WomDetails.objects.filter(
            wom=wom,
            isavpt=True
        ).count()
        assert attachment_count == 8  # Every 7th record (0,7,14,21,28,35,42,49)