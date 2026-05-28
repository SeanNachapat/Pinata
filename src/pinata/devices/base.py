import asyncio
import uuid
import datetime
from typing import Callable, List, Optional, Dict, Awaitable

from pinata.models import SensorReading, AnomalyInjectionRequest

class VirtualDevice:
    """
    Base class for all virtual IoT devices.
    Handles the asynchronous event loop, anomaly state, and listener callbacks.
    """
    preset_name: str = "BaseDevice"
    
    def __init__(self, device_id: Optional[str] = None, frequency_hz: float = 1.0, start_test_broker: bool = False):
        self.device_id = device_id or str(uuid.uuid4())
        self.frequency_hz = frequency_hz
        self.start_test_broker = start_test_broker
        
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        
        self.current_anomaly: Optional[str] = None
        self.anomaly_end_time: Optional[datetime.datetime] = None
        self.anomaly_intensity: float = 1.0
        
        # Callbacks that receive SensorReading objects
        self._listeners: List[Callable[[SensorReading], Awaitable[None] | None]] = []
    
    def add_listener(self, callback: Callable[[SensorReading], Awaitable[None] | None]):
        """Register a callback (sync or async) to be called whenever a new reading is generated."""
        self._listeners.append(callback)
        
    def inject_anomaly(self, request: AnomalyInjectionRequest):
        """Trigger a failure or anomaly in the device behavior."""
        self.current_anomaly = request.anomaly_type
        self.anomaly_intensity = request.intensity
        if request.duration_seconds:
            self.anomaly_end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=request.duration_seconds)
        else:
            self.anomaly_end_time = None
            
    def clear_anomaly(self):
        """Reset the device to normal behavior."""
        self.current_anomaly = None
        self.anomaly_end_time = None
        self.anomaly_intensity = 1.0
        
    def _check_anomaly_timeout(self):
        if self.anomaly_end_time and datetime.datetime.utcnow() > self.anomaly_end_time:
            self.clear_anomaly()
            
    async def start(self):
        """Start the generation loop."""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        
    async def stop(self):
        """Stop the generation loop."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
    async def _run_loop(self):
        sleep_time = 1.0 / self.frequency_hz
        while self._is_running:
            self._check_anomaly_timeout()
            
            # Generate the specific sensor values
            sensor_data = self.generate_sensors()
            
            reading = SensorReading(
                device_id=self.device_id,
                preset=self.preset_name,
                anomaly=1 if self.current_anomaly else 0,
                anomaly_type=self.current_anomaly,
                sensors=sensor_data
            )
            
            # Notify all listeners
            for listener in self._listeners:
                res = listener(reading)
                if asyncio.iscoroutine(res):
                    # We fire and forget, catching exceptions could be added
                    asyncio.create_task(res)
                    
            await asyncio.sleep(sleep_time)
            
    def generate_sensors(self) -> Dict[str, float]:
        """
        Override this in subclasses to generate physics-based sensor data.
        Use self.current_anomaly to alter behavior if an anomaly is active.
        """
        raise NotImplementedError
