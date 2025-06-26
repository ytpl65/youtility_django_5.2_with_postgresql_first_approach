import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock
from background_tasks.report_tasks import set_state


class ReportTasksSimpleTest(TestCase):
    """Test report tasks functions - simplified version"""
    
    def test_set_state_functionality(self):
        """Test the set_state helper function"""
        # Initialize state map
        state_map = {
            'total': 0,
            'processed': 0,
            'failed': 0
        }
        
        # Test incrementing a state
        result = set_state(state_map, set="processed")
        self.assertEqual(result['processed'], 1)
        
        # Test incrementing again
        result = set_state(state_map, set="processed")
        self.assertEqual(result['processed'], 2)
        
        # Test resetting
        result = set_state(state_map, reset=True)
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['failed'], 0)