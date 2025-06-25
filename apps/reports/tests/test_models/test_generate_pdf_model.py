"""
Tests for GeneratePDF model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.reports.models import GeneratePDF


@pytest.mark.django_db
class TestGeneratePDFModel:
    """Test suite for GeneratePDF model"""
    
    def test_generate_pdf_creation_basic(self, generate_pdf_factory):
        """Test creating a basic GeneratePDF instance"""
        generate_pdf = generate_pdf_factory()
        
        assert generate_pdf.id is not None
        assert generate_pdf.document_type == GeneratePDF.DocumentType.PAYROLL
        assert generate_pdf.company == GeneratePDF.Company.SPS
        assert generate_pdf.additional_filter == GeneratePDF.AdditionalFilter.CUSTOMER
        assert generate_pdf.customer is not None
        assert generate_pdf.site is not None
        assert generate_pdf.period_from is not None
        assert generate_pdf.type_of_form == GeneratePDF.FormType.NORMALFORM
    
    
    def test_generate_pdf_str_representation(self, generate_pdf_factory):
        """Test GeneratePDF string representation"""
        generate_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            customer='Test Customer'
        )
        
        # Test if it has a proper string representation (inherited from BaseModel)
        str_repr = str(generate_pdf)
        assert str_repr is not None
        assert len(str_repr) > 0
    
    
    def test_generate_pdf_document_type_choices(self, generate_pdf_factory, document_type_choices):
        """Test GeneratePDF document type choices"""
        for document_type in document_type_choices:
            generate_pdf = generate_pdf_factory(
                document_type=document_type,
                customer=f'Customer for {document_type.value}'
            )
            assert generate_pdf.document_type == document_type
    
    
    def test_generate_pdf_company_choices(self, generate_pdf_factory, company_choices):
        """Test GeneratePDF company choices"""
        for company in company_choices:
            generate_pdf = generate_pdf_factory(
                company=company,
                customer=f'Customer for {company.value}'
            )
            assert generate_pdf.company == company
    
    
    def test_generate_pdf_additional_filter_choices(self, generate_pdf_factory, additional_filter_choices):
        """Test GeneratePDF additional filter choices"""
        for additional_filter in additional_filter_choices:
            generate_pdf = generate_pdf_factory(
                additional_filter=additional_filter,
                customer=f'Customer for {additional_filter.value}'
            )
            assert generate_pdf.additional_filter == additional_filter
    
    
    def test_generate_pdf_form_type_choices(self, generate_pdf_factory, form_type_choices):
        """Test GeneratePDF form type choices"""
        for form_type in form_type_choices:
            generate_pdf = generate_pdf_factory(
                type_of_form=form_type,
                customer=f'Customer for {form_type.value}'
            )
            assert generate_pdf.type_of_form == form_type
    
    
    def test_generate_pdf_payroll_document(self, generate_pdf_factory):
        """Test GeneratePDF for payroll document generation"""
        payroll_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='ABC Corporation',
            site='Main Office',
            period_from='2024-01',
            type_of_form=GeneratePDF.FormType.NORMALFORM
        )
        
        assert payroll_pdf.document_type == GeneratePDF.DocumentType.PAYROLL
        assert payroll_pdf.company == GeneratePDF.Company.SPS
        assert payroll_pdf.customer == 'ABC Corporation'
        assert payroll_pdf.site == 'Main Office'
        assert payroll_pdf.period_from == '2024-01'
        assert payroll_pdf.type_of_form == GeneratePDF.FormType.NORMALFORM
    
    
    def test_generate_pdf_pf_document(self, generate_pdf_factory):
        """Test GeneratePDF for PF document generation"""
        pf_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PF,
            company=GeneratePDF.Company.SFS,
            additional_filter=GeneratePDF.AdditionalFilter.SITE,
            customer='XYZ Industries',
            site='Manufacturing Plant',
            period_from='2024-02',
            type_of_form=GeneratePDF.FormType.FORM16
        )
        
        assert pf_pdf.document_type == GeneratePDF.DocumentType.PF
        assert pf_pdf.company == GeneratePDF.Company.SFS
        assert pf_pdf.additional_filter == GeneratePDF.AdditionalFilter.SITE
        assert pf_pdf.customer == 'XYZ Industries'
        assert pf_pdf.site == 'Manufacturing Plant'
        assert pf_pdf.period_from == '2024-02'
        assert pf_pdf.type_of_form == GeneratePDF.FormType.FORM16
    
    
    def test_generate_pdf_esic_document(self, generate_pdf_factory):
        """Test GeneratePDF for ESIC document generation"""
        esic_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.ESIC,
            company=GeneratePDF.Company.TARGET,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='DEF Enterprises',
            site='Regional Office',
            period_from='2024-03'
        )
        
        assert esic_pdf.document_type == GeneratePDF.DocumentType.ESIC
        assert esic_pdf.company == GeneratePDF.Company.TARGET
        assert esic_pdf.customer == 'DEF Enterprises'
        assert esic_pdf.site == 'Regional Office'
        assert esic_pdf.period_from == '2024-03'
    
    
    def test_generate_pdf_customer_filter(self, generate_pdf_factory):
        """Test GeneratePDF with customer filter"""
        customer_pdf = generate_pdf_factory(
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='Global Tech Solutions',
            site=None  # Site should be None for customer filter
        )
        
        assert customer_pdf.additional_filter == GeneratePDF.AdditionalFilter.CUSTOMER
        assert customer_pdf.customer == 'Global Tech Solutions'
        # Site can be None when filtering by customer
    
    
    def test_generate_pdf_site_filter(self, generate_pdf_factory):
        """Test GeneratePDF with site filter"""
        site_pdf = generate_pdf_factory(
            additional_filter=GeneratePDF.AdditionalFilter.SITE,
            customer='Tech Innovations Inc',
            site='Development Center'
        )
        
        assert site_pdf.additional_filter == GeneratePDF.AdditionalFilter.SITE
        assert site_pdf.customer == 'Tech Innovations Inc'
        assert site_pdf.site == 'Development Center'
    
    
    def test_generate_pdf_period_formats(self, generate_pdf_factory):
        """Test GeneratePDF with different period formats"""
        period_formats = [
            '2024-01',       # YYYY-MM
            '2024-Q1',       # YYYY-Q1
            '2024',          # YYYY
            'Jan-2024',      # Mon-YYYY
            '01/2024',       # MM/YYYY
            '2024-01-31'     # YYYY-MM-DD
        ]
        
        for period in period_formats:
            generate_pdf = generate_pdf_factory(
                period_from=period,
                customer=f'Customer for period {period}'
            )
            assert generate_pdf.period_from == period
    
    
    def test_generate_pdf_company_combinations(self, generate_pdf_factory):
        """Test GeneratePDF with different company combinations"""
        company_scenarios = [
            (GeneratePDF.Company.SPS, GeneratePDF.DocumentType.PAYROLL),
            (GeneratePDF.Company.SFS, GeneratePDF.DocumentType.PF),
            (GeneratePDF.Company.TARGET, GeneratePDF.DocumentType.ESIC),
            (GeneratePDF.Company.SPS, GeneratePDF.DocumentType.ESIC),
            (GeneratePDF.Company.SFS, GeneratePDF.DocumentType.PAYROLL),
            (GeneratePDF.Company.TARGET, GeneratePDF.DocumentType.PF)
        ]
        
        for company, doc_type in company_scenarios:
            generate_pdf = generate_pdf_factory(
                company=company,
                document_type=doc_type,
                customer=f'{company.value} Customer for {doc_type.value}'
            )
            assert generate_pdf.company == company
            assert generate_pdf.document_type == doc_type
    
    
    def test_generate_pdf_form_type_scenarios(self, generate_pdf_factory):
        """Test GeneratePDF with different form type scenarios"""
        # Normal form for payroll
        normal_form = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            type_of_form=GeneratePDF.FormType.NORMALFORM,
            customer='Normal Form Customer'
        )
        
        # Form 16 for PF
        form16 = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PF,
            type_of_form=GeneratePDF.FormType.FORM16,
            customer='Form16 Customer'
        )
        
        assert normal_form.type_of_form == GeneratePDF.FormType.NORMALFORM
        assert form16.type_of_form == GeneratePDF.FormType.FORM16
    
    
    def test_generate_pdf_get_solo_method(self, generate_pdf_factory):
        """Test GeneratePDF get_solo class method"""
        # Test get_solo method creates a single instance
        solo_instance1 = GeneratePDF.get_solo()
        solo_instance2 = GeneratePDF.get_solo()
        
        # Both calls should return the same instance
        assert solo_instance1.id == solo_instance2.id
        assert solo_instance1.pk == 1  # Should use constant primary key
        
        # Test that it uses defaults when created
        assert solo_instance1.id is not None
    
    
    def test_generate_pdf_null_and_blank_fields(self, generate_pdf_factory):
        """Test GeneratePDF with null and blank field handling"""
        # Test with minimal required fields
        minimal_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer=None,  # Test null customer
            site=None,      # Test null site
            period_from=None,  # Test null period
            type_of_form=None  # Test null form type
        )
        
        assert minimal_pdf.customer is None
        assert minimal_pdf.site is None
        assert minimal_pdf.period_from is None
        assert minimal_pdf.type_of_form is None
    
    
    def test_generate_pdf_field_defaults(self, generate_pdf_factory):
        """Test GeneratePDF field default values"""
        # Create instance with explicit None values to test defaults
        generate_pdf = GeneratePDF.objects.create(
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER
        )
        
        # Test default values
        assert generate_pdf.customer is None  # Default None
        assert generate_pdf.site is None      # Default None
        assert generate_pdf.period_from is None  # Default None
    
    
    def test_generate_pdf_bulk_operations(self, generate_pdf_factory):
        """Test bulk operations on GeneratePDF"""
        # Create multiple GeneratePDF records
        pdfs = []
        document_types = [
            GeneratePDF.DocumentType.PAYROLL,
            GeneratePDF.DocumentType.PF,
            GeneratePDF.DocumentType.ESIC
        ]
        companies = [
            GeneratePDF.Company.SPS,
            GeneratePDF.Company.SFS,
            GeneratePDF.Company.TARGET
        ]
        
        for i in range(15):
            pdf = generate_pdf_factory(
                document_type=document_types[i % len(document_types)],
                company=companies[i % len(companies)],
                customer=f'Bulk Customer {i}',
                period_from=f'2024-{(i % 12) + 1:02d}'
            )
            pdfs.append(pdf)
        
        # Test bulk filtering by document type
        payroll_pdfs = GeneratePDF.objects.filter(document_type=GeneratePDF.DocumentType.PAYROLL)
        pf_pdfs = GeneratePDF.objects.filter(document_type=GeneratePDF.DocumentType.PF)
        esic_pdfs = GeneratePDF.objects.filter(document_type=GeneratePDF.DocumentType.ESIC)
        
        assert payroll_pdfs.count() == 5  # 0,3,6,9,12
        assert pf_pdfs.count() == 5       # 1,4,7,10,13
        assert esic_pdfs.count() == 5     # 2,5,8,11,14
        
        # Test bulk filtering by company
        sps_pdfs = GeneratePDF.objects.filter(company=GeneratePDF.Company.SPS)
        sfs_pdfs = GeneratePDF.objects.filter(company=GeneratePDF.Company.SFS)
        target_pdfs = GeneratePDF.objects.filter(company=GeneratePDF.Company.TARGET)
        
        assert sps_pdfs.count() == 5     # 0,3,6,9,12
        assert sfs_pdfs.count() == 5     # 1,4,7,10,13
        assert target_pdfs.count() == 5  # 2,5,8,11,14
    
    
    def test_generate_pdf_filtering_scenarios(self, generate_pdf_factory):
        """Test GeneratePDF filtering scenarios"""
        # Create PDFs for different scenarios
        customer_payroll = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='Customer A',
            period_from='2024-01'
        )
        
        site_pf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PF,
            additional_filter=GeneratePDF.AdditionalFilter.SITE,
            customer='Customer B',
            site='Site B',
            period_from='2024-02'
        )
        
        customer_esic = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.ESIC,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='Customer C',
            period_from='2024-03'
        )
        
        # Test filtering by customer filter type
        customer_filtered = GeneratePDF.objects.filter(
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER
        )
        site_filtered = GeneratePDF.objects.filter(
            additional_filter=GeneratePDF.AdditionalFilter.SITE
        )
        
        assert customer_payroll in customer_filtered
        assert customer_esic in customer_filtered
        assert site_pf not in customer_filtered
        
        assert site_pf in site_filtered
        assert customer_payroll not in site_filtered
        assert customer_esic not in site_filtered
        
        # Test filtering by period
        january_pdfs = GeneratePDF.objects.filter(period_from='2024-01')
        february_pdfs = GeneratePDF.objects.filter(period_from='2024-02')
        
        assert customer_payroll in january_pdfs
        assert site_pf not in january_pdfs
        
        assert site_pf in february_pdfs
        assert customer_payroll not in february_pdfs
    
    
    def test_generate_pdf_complex_filtering(self, generate_pdf_factory):
        """Test GeneratePDF complex filtering combinations"""
        # Create PDF with specific combination
        target_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER,
            customer='Target Customer',
            period_from='2024-06',
            type_of_form=GeneratePDF.FormType.NORMALFORM
        )
        
        # Create other PDFs with different combinations
        other_pdf1 = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PF,
            company=GeneratePDF.Company.SPS,
            customer='Other Customer 1'
        )
        
        other_pdf2 = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SFS,
            customer='Other Customer 2'
        )
        
        # Test complex filtering
        filtered_pdfs = GeneratePDF.objects.filter(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            additional_filter=GeneratePDF.AdditionalFilter.CUSTOMER
        )
        
        assert target_pdf in filtered_pdfs
        assert other_pdf1 not in filtered_pdfs  # Wrong document type
        assert other_pdf2 not in filtered_pdfs  # Wrong company
    
    
    def test_generate_pdf_update_operations(self, generate_pdf_factory):
        """Test GeneratePDF update operations"""
        generate_pdf = generate_pdf_factory(
            document_type=GeneratePDF.DocumentType.PAYROLL,
            company=GeneratePDF.Company.SPS,
            customer='Original Customer',
            period_from='2024-01'
        )
        
        # Update fields
        generate_pdf.customer = 'Updated Customer'
        generate_pdf.period_from = '2024-02'
        generate_pdf.document_type = GeneratePDF.DocumentType.PF
        generate_pdf.save()
        
        # Verify updates
        updated_pdf = GeneratePDF.objects.get(id=generate_pdf.id)
        assert updated_pdf.customer == 'Updated Customer'
        assert updated_pdf.period_from == '2024-02'
        assert updated_pdf.document_type == GeneratePDF.DocumentType.PF
    
    
    def test_generate_pdf_performance_queries(self, generate_pdf_factory):
        """Test performance-oriented queries on GeneratePDF"""
        # Create many GeneratePDF records for performance testing
        pdfs = []
        for i in range(100):
            pdf = generate_pdf_factory(
                document_type=GeneratePDF.DocumentType.PAYROLL if i % 2 == 0 else GeneratePDF.DocumentType.PF,
                company=GeneratePDF.Company.SPS if i % 3 == 0 else GeneratePDF.Company.SFS,
                customer=f'Performance Customer {i}',
                period_from=f'2024-{(i % 12) + 1:02d}'
            )
            pdfs.append(pdf)
        
        # Test count queries
        total_count = GeneratePDF.objects.count()
        assert total_count >= 100
        
        # Test document type filtering
        payroll_count = GeneratePDF.objects.filter(
            document_type=GeneratePDF.DocumentType.PAYROLL
        ).count()
        pf_count = GeneratePDF.objects.filter(
            document_type=GeneratePDF.DocumentType.PF
        ).count()
        
        assert payroll_count == 50  # Even indices
        assert pf_count == 50       # Odd indices
        
        # Test company filtering
        sps_count = GeneratePDF.objects.filter(
            company=GeneratePDF.Company.SPS
        ).count()
        sfs_count = GeneratePDF.objects.filter(
            company=GeneratePDF.Company.SFS
        ).count()
        
        assert sps_count >= 33  # Every 3rd record
        assert sfs_count >= 67  # Remaining records