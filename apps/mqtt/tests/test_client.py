import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.conf import settings
from paho.mqtt.enums import CallbackAPIVersion

from apps.mqtt.client import MqttClient, get_task_status


class TestGetTaskStatus(TestCase):

    @patch('apps.mqtt.client.AsyncResult')
    def test_get_task_status_success(self, mock_async_result):
        mock_result = Mock()
        mock_result.status = 'SUCCESS'
        mock_async_result.return_value = mock_result
        
        item = {'taskId': 'test-task-id'}
        result = get_task_status(item)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['taskId'], 'test-task-id')
        mock_async_result.assert_called_once_with('test-task-id')

    @patch('apps.mqtt.client.AsyncResult')
    def test_get_task_status_pending(self, mock_async_result):
        mock_result = Mock()
        mock_result.status = 'PENDING'
        mock_async_result.return_value = mock_result
        
        item = {'taskId': 'pending-task-id'}
        result = get_task_status(item)
        
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(result['taskId'], 'pending-task-id')

    @patch('apps.mqtt.client.AsyncResult')
    def test_get_task_status_failure(self, mock_async_result):
        mock_result = Mock()
        mock_result.status = 'FAILURE'
        mock_async_result.return_value = mock_result
        
        item = {'taskId': 'failed-task-id'}
        result = get_task_status(item)
        
        self.assertEqual(result['status'], 'FAILURE')


class TestMqttClient(TestCase):

    def setUp(self):
        self.patcher_mqtt = patch('apps.mqtt.client.mqtt.Client')
        self.mock_mqtt_client = self.patcher_mqtt.start()
        self.mock_client_instance = Mock()
        self.mock_mqtt_client.return_value = self.mock_client_instance
        
        self.mqtt_client = MqttClient()

    def tearDown(self):
        self.patcher_mqtt.stop()

    def test_mqtt_client_initialization(self):
        self.mock_mqtt_client.assert_called_once_with(CallbackAPIVersion.VERSION2)
        self.assertEqual(self.mqtt_client.client, self.mock_client_instance)
        self.assertEqual(self.mock_client_instance.on_connect, self.mqtt_client.on_connect)
        self.assertEqual(self.mock_client_instance.on_message, self.mqtt_client.on_message)
        self.assertEqual(self.mock_client_instance.on_disconnect, self.mqtt_client.on_disconnect)

    @patch('apps.mqtt.client.log')
    def test_on_connect_success(self, mock_log):
        client_mock = Mock()
        
        self.mqtt_client.on_connect(client_mock, None, None, 0, None)
        
        mock_log.info.assert_called_with("Connected to MQTT Broker!")
        client_mock.subscribe.assert_any_call("graphql/mutation")
        client_mock.subscribe.assert_any_call("graphql/mutation/status")

    @patch('apps.mqtt.client.log')
    def test_on_connect_failure(self, mock_log):
        client_mock = Mock()
        
        self.mqtt_client.on_connect(client_mock, None, None, 1, None)
        
        mock_log.info.assert_called_with("Failed to connect, return code 1")
        client_mock.subscribe.assert_not_called()

    @patch('apps.mqtt.client.process_graphql_mutation_async')
    @patch('apps.mqtt.client.log')
    def test_on_message_mutation_topic(self, mock_log, mock_process_task):
        mock_result = Mock()
        mock_result.task_id = 'test-task-id'
        mock_result.state = 'PENDING'
        mock_process_task.delay.return_value = mock_result
        
        client_mock = Mock()
        msg_mock = Mock()
        msg_mock.topic = "graphql/mutation"
        msg_mock.payload.decode.return_value = json.dumps({
            'uuids': ['uuid1', 'uuid2'],
            'serviceName': 'test-service',
            'mutation': 'test mutation'
        })
        msg_mock.mid = 123
        
        self.mqtt_client.on_message(client_mock, None, msg_mock)
        
        mock_process_task.delay.assert_called_once()
        client_mock.publish.assert_called_once()
        
        publish_call = client_mock.publish.call_args
        self.assertEqual(publish_call[0][0], "response/acknowledgement")
        
        published_data = json.loads(publish_call[0][1])
        self.assertEqual(published_data['task_id'], 'test-task-id')
        self.assertEqual(published_data['status'], 'PENDING')
        self.assertEqual(published_data['uuids'], ['uuid1', 'uuid2'])
        self.assertEqual(published_data['serviceName'], 'test-service')

    @patch('apps.mqtt.client.get_task_status')
    @patch('apps.mqtt.client.log')
    def test_on_message_status_topic(self, mock_log, mock_get_task_status):
        mock_get_task_status.side_effect = lambda x: {**x, 'status': 'SUCCESS'}
        
        client_mock = Mock()
        msg_mock = Mock()
        msg_mock.topic = "graphql/mutation/status"
        msg_mock.payload.decode.return_value = json.dumps({
            'taskIds': [
                {'taskId': 'task1'},
                {'taskId': 'task2'}
            ]
        })
        msg_mock.mid = 124
        
        self.mqtt_client.on_message(client_mock, None, msg_mock)
        
        self.assertEqual(mock_get_task_status.call_count, 2)
        client_mock.publish.assert_called_once()
        
        publish_call = client_mock.publish.call_args
        self.assertEqual(publish_call[0][0], "response/status")
        
        published_data = json.loads(publish_call[0][1])
        self.assertEqual(len(published_data), 2)
        self.assertEqual(published_data[0]['status'], 'SUCCESS')
        self.assertEqual(published_data[1]['status'], 'SUCCESS')

    @patch('apps.mqtt.client.log')
    def test_on_message_empty_payload(self, mock_log):
        client_mock = Mock()
        msg_mock = Mock()
        msg_mock.topic = "unknown/topic"
        msg_mock.payload.decode.return_value = ""
        msg_mock.mid = 125
        
        self.mqtt_client.on_message(client_mock, None, msg_mock)
        
        mock_log.info.assert_any_call("message: 125 from MQTT broker on topicunknown/topic payload not recieved")

    @patch('apps.mqtt.client.log')
    def test_on_disconnect(self, mock_log):
        client_mock = Mock()
        userdata = {'test': 'data'}
        
        self.mqtt_client.on_disconnect(client_mock, userdata, None, 0, None)
        
        mock_log.info.assert_called_with("Disconnected from MQTT broker", userdata)

    @patch('apps.mqtt.client.BROKER_ADDRESS', 'test-broker')
    @patch('apps.mqtt.client.BROKER_PORT', 1883)
    def test_loop_forever(self):
        with patch.object(self.mqtt_client.client, 'connect') as mock_connect, \
             patch.object(self.mqtt_client.client, 'loop_forever') as mock_loop:
            
            self.mqtt_client.loop_forever()
            
            mock_connect.assert_called_once_with('test-broker', 1883)
            mock_loop.assert_called_once()

    def test_on_message_invalid_json_payload(self):
        client_mock = Mock()
        msg_mock = Mock()
        msg_mock.topic = "graphql/mutation/status"
        msg_mock.payload.decode.return_value = "invalid json"
        msg_mock.mid = 126
        
        with self.assertRaises(json.JSONDecodeError):
            self.mqtt_client.on_message(client_mock, None, msg_mock)

    @patch('apps.mqtt.client.process_graphql_mutation_async')
    @patch('apps.mqtt.client.log')
    def test_on_message_mutation_missing_fields(self, mock_log, mock_process_task):
        mock_result = Mock()
        mock_result.task_id = 'test-task-id'
        mock_result.state = 'PENDING'
        mock_process_task.delay.return_value = mock_result
        
        client_mock = Mock()
        msg_mock = Mock()
        msg_mock.topic = "graphql/mutation"
        msg_mock.payload.decode.return_value = json.dumps({
            'mutation': 'test mutation'
        })
        msg_mock.mid = 127
        
        self.mqtt_client.on_message(client_mock, None, msg_mock)
        
        publish_call = client_mock.publish.call_args
        published_data = json.loads(publish_call[0][1])
        self.assertEqual(published_data['uuids'], [])
        self.assertEqual(published_data['serviceName'], "")


class TestMqttClientIntegration(TestCase):

    @patch('apps.mqtt.client.mqtt.Client')
    def test_full_mqtt_client_workflow(self, mock_mqtt_client):
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance
        
        mqtt_client = MqttClient()
        
        with patch.object(mqtt_client, 'on_connect') as mock_on_connect, \
             patch.object(mqtt_client, 'on_message') as mock_on_message, \
             patch.object(mqtt_client, 'on_disconnect') as mock_on_disconnect:
            
            mock_client_instance.on_connect = mock_on_connect
            mock_client_instance.on_message = mock_on_message
            mock_client_instance.on_disconnect = mock_on_disconnect
            
            mqtt_client.loop_forever()
            
            mock_client_instance.connect.assert_called_once()
            mock_client_instance.loop_forever.assert_called_once()