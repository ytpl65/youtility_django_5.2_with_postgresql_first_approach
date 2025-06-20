# mqtt_utils.py

import logging
from paho.mqtt import client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

log = logging.getLogger("message_qlogs")

def publish_message(topic, message, host="django5.youtility.in", port=1883, qos=1):
    try:
        log.info(f"Connecting to MQTT broker at {host}:{port}")
        client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        client.connect(host, port, 60)
        result = client.publish(topic, message, qos=qos)
        client.loop(2)
        client.disconnect()
        log.info(f"Published message to topic {topic}: {message}")
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            log.info(f"[MQTT] Message sent to topic {topic}")
        else:
            log.warning(f"[MQTT] Failed with result code {result.rc}")
    except Exception as e:
        log.error(f"[MQTT] Exception during publish: {e}", exc_info=True)
