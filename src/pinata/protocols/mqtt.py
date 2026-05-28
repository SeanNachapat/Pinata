import asyncio
import socket
import logging
from typing import Optional
import paho.mqtt.client as mqtt

from pinata.models import SensorReading

logger = logging.getLogger("pinata.mqtt")

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class MQTTClient:
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, start_test_broker: bool = False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.start_test_broker = start_test_broker
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        self._test_broker_task = None
        self.is_connected = False
        
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.is_connected = True
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {reason_code}")
            
    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.is_connected = False
        logger.warning("Disconnected from MQTT broker")

    async def start(self):
        if self.start_test_broker:
            await self._spin_up_test_broker()
            
        try:
            self.client.connect_async(self.broker_host, self.broker_port)
            self.client.loop_start()
        except ConnectionRefusedError:
            if self.broker_host == "localhost":
                logger.error(
                    f"No broker found on localhost:{self.broker_port}. "
                    "Run with start_test_broker=True to spin one up, or point to an existing broker."
                )
            raise
            
    async def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        if self._test_broker_task:
            self._test_broker_task.cancel()
            
    async def _spin_up_test_broker(self):
        """Spins up a lightweight amqtt broker on a random port if 1883 is taken."""
        try:
            from amqtt.broker import Broker
        except ImportError:
            logger.error("amqtt is required for the test broker. Install it with `poetry add amqtt`")
            return
            
        # Try 1883 first, fallback to random
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', self.broker_port))
            s.close()
        except OSError:
            self.broker_port = get_free_port()
            logger.info(f"Port 1883 is taken. Test broker falling back to random port: {self.broker_port}")
            
        config = {
            'listeners': {
                'default': {
                    'type': 'tcp',
                    'bind': f'localhost:{self.broker_port}'
                }
            },
            'sys_interval': 10,
            'topic-check': {
                'enabled': False
            }
        }
        broker = Broker(config)
        self._test_broker_task = asyncio.create_task(broker.start())
        logger.info(f"Test MQTT broker running on localhost:{self.broker_port}")
        await asyncio.sleep(1) # wait for broker to start
        
    def publish_reading(self, reading: SensorReading):
        if self.is_connected:
            topic = f"pinata/devices/{reading.preset}/{reading.device_id}/sensors"
            payload = reading.model_dump_json()
            self.client.publish(topic, payload)
