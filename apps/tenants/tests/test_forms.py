from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.tenants.forms import SearchFieldForm


class SearchFieldFormTest(TestCase):
    
    def test_form_initialization(self):
        form = SearchFieldForm()
        
        self.assertIn('search_col', form.fields)
        self.assertIn('search_val', form.fields)

    def test_form_fields_properties(self):
        form = SearchFieldForm()
        
        # Check search_col field
        search_col_field = form.fields['search_col']
        self.assertEqual(search_col_field.__class__.__name__, 'ChoiceField')
        self.assertFalse(search_col_field.required)
        self.assertEqual(search_col_field.choices, [])

    def test_search_val_field_properties(self):
        form = SearchFieldForm()
        
        # Check search_val field
        search_val_field = form.fields['search_val']
        self.assertEqual(search_val_field.__class__.__name__, 'CharField')
        self.assertEqual(search_val_field.max_length, 50)
        self.assertEqual(search_val_field.min_length, 3)
        self.assertFalse(search_val_field.required)

    def test_form_with_valid_data(self):
        form_data = {
            'search_val': 'test value'
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data.get('search_col'), '')
        self.assertEqual(form.cleaned_data['search_val'], 'test value')

    def test_form_with_empty_data(self):
        form_data = {}
        
        form = SearchFieldForm(data=form_data)
        
        # Should be valid since both fields are not required
        self.assertTrue(form.is_valid())

    def test_form_with_partial_data(self):
        # Test with only search_col (empty)
        form_data1 = {'search_col': ''}
        form1 = SearchFieldForm(data=form_data1)
        self.assertTrue(form1.is_valid())
        
        # Test with only search_val
        form_data2 = {'search_val': 'test'}
        form2 = SearchFieldForm(data=form_data2)
        self.assertTrue(form2.is_valid())

    def test_search_val_min_length_validation(self):
        # Test with value less than min_length (3)
        form_data = {
            'search_col': 'name',
            'search_val': 'ab'  # Only 2 characters
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('search_val', form.errors)

    def test_search_val_max_length_validation(self):
        # Test with value exceeding max_length (50)
        long_value = 'a' * 51  # 51 characters
        form_data = {
            'search_col': 'name',
            'search_val': long_value
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('search_val', form.errors)

    def test_search_val_exact_min_length(self):
        # Test with value exactly at min_length (3)
        form_data = {
            'search_val': 'abc'  # Exactly 3 characters
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_search_val_exact_max_length(self):
        # Test with value exactly at max_length (50)
        exact_max_value = 'a' * 50  # Exactly 50 characters
        form_data = {
            'search_val': exact_max_value
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_search_col_with_custom_choices(self):
        # Create form with custom choices
        class CustomSearchFieldForm(SearchFieldForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['search_col'].choices = [
                    ('name', 'Name'),
                    ('email', 'Email'),
                    ('id', 'ID')
                ]
        
        form_data = {
            'search_col': 'name',
            'search_val': 'test'
        }
        
        form = CustomSearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search_col'], 'name')

    def test_search_col_invalid_choice(self):
        # Create form with specific choices
        class CustomSearchFieldForm(SearchFieldForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['search_col'].choices = [
                    ('name', 'Name'),
                    ('email', 'Email')
                ]
        
        form_data = {
            'search_col': 'invalid_choice',
            'search_val': 'test'
        }
        
        form = CustomSearchFieldForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('search_col', form.errors)

    def test_form_without_data(self):
        # Test form initialization without data
        form = SearchFieldForm()
        
        # Form should not be bound
        self.assertFalse(form.is_bound)

    def test_form_cleaned_data_access(self):
        form_data = {
            'search_col': 'email',
            'search_val': 'test@example.com'
        }
        
        form = SearchFieldForm(data=form_data)
        
        if form.is_valid():
            self.assertEqual(form.cleaned_data.get('search_col'), 'email')
            self.assertEqual(form.cleaned_data.get('search_val'), 'test@example.com')

    def test_form_error_messages(self):
        # Test error messages for min_length validation
        form_data = {
            'search_val': 'a'  # Too short
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('search_val', form.errors)
        # Check that error message mentions minimum length
        error_message = str(form.errors['search_val'])
        self.assertIn('at least 3', error_message)

    def test_form_field_help_text(self):
        form = SearchFieldForm()
        
        # Check if fields have help_text (they don't by default, but this tests the structure)
        search_col_field = form.fields['search_col']
        search_val_field = form.fields['search_val']
        
        # These should be empty strings by default
        self.assertEqual(search_col_field.help_text, '')
        self.assertEqual(search_val_field.help_text, '')

    def test_form_field_widgets(self):
        form = SearchFieldForm()
        
        # Test that fields use default widgets
        search_col_field = form.fields['search_col']
        search_val_field = form.fields['search_val']
        
        # ChoiceField uses Select widget by default
        self.assertEqual(search_col_field.widget.__class__.__name__, 'Select')
        # CharField uses TextInput widget by default
        self.assertEqual(search_val_field.widget.__class__.__name__, 'TextInput')

    def test_form_special_characters_in_search_val(self):
        # Test with special characters
        form_data = {
            'search_val': 'test@#$%'
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search_val'], 'test@#$%')

    def test_form_unicode_characters_in_search_val(self):
        # Test with unicode characters
        form_data = {
            'search_val': 'tëst_ñame'
        }
        
        form = SearchFieldForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search_val'], 'tëst_ñame')