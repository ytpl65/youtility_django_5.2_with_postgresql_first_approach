import pytest
import os
import django
from django.conf import settings
from unittest.mock import patch

@pytest.fixture(scope='session', autouse=True)
def django_setup():
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
        django.setup()

@pytest.fixture
def mock_mqtt_config():
    mock_config = {
        'BROKER_ADDRESS': 'test-broker.local',
        'BROKER_PORT': 1883,
        'USERNAME': 'test_user',
        'PASSWORD': 'test_pass'
    }
    with patch('apps.mqtt.client.MQTT_CONFIG', mock_config):
        yield mock_config

@pytest.fixture
def mock_celery_task():
    with patch('apps.mqtt.client.process_graphql_mutation_async') as mock_task:
        mock_result = type('MockResult', (), {
            'task_id': 'test-task-123',
            'state': 'PENDING'
        })()
        mock_task.delay.return_value = mock_result
        yield mock_task

@pytest.fixture
def sample_mutation_payload():
    return {
        'uuids': ['uuid-1', 'uuid-2', 'uuid-3'],
        'serviceName': 'test-service',
        'mutation': 'mutation { createUser(input: { name: "test" }) { id } }'
    }

@pytest.fixture
def sample_status_payload():
    return {
        'taskIds': [
            {'taskId': 'task-1'},
            {'taskId': 'task-2'},
            {'taskId': 'task-3'}
        ]
    }