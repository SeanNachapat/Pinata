import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pinata.devices.base import VirtualDevice
from pinata.models import AnomalyInjectionRequest, SensorReading
from pinata.protocols.mqtt import MQTTClient

logger = logging.getLogger("pinata.server")

class Server:
    """
    FastAPI and WebSocket server that wraps a VirtualDevice.
    Also manages the MQTT client and streams device readings to all connected clients and topics.
    """
    def __init__(self, device: VirtualDevice, host: str = "0.0.0.0", port: int = 8000, mqtt_host: str = "localhost"):
        self.device = device
        self.host = host
        self.port = port
        
        self.app = FastAPI(
            title=f"Piñata - {device.preset_name}",
            description="Virtual IoT device simulation server"
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.mqtt_client = MQTTClient(broker_host=mqtt_host, start_test_broker=device.start_test_broker)
        self.connected_websockets: list[WebSocket] = []
        
        self.setup_routes()
        # Add the broadcast function to the device's event loop
        self.device.add_listener(self._broadcast_reading)
        
    def setup_routes(self):
        @self.app.post("/api/inject")
        async def inject_anomaly(request: AnomalyInjectionRequest):
            """Inject a failure or anomaly into the running device."""
            self.device.inject_anomaly(request)
            return {"status": "success", "message": f"Injected {request.anomaly_type}"}
            
        @self.app.post("/api/clear")
        async def clear_anomaly():
            """Clear all current anomalies and return the device to normal."""
            self.device.clear_anomaly()
            return {"status": "success", "message": "Cleared anomalies"}
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Live data stream of the device's sensor readings."""
            await websocket.accept()
            self.connected_websockets.append(websocket)
            try:
                while True:
                    # Keep connection alive, wait for client messages if any
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.connected_websockets.remove(websocket)

    async def _broadcast_reading(self, reading: SensorReading):
        """Called by the VirtualDevice every time a new reading is generated."""
        # 1. Publish to MQTT
        self.mqtt_client.publish_reading(reading)
        
        # 2. Broadcast to WebSockets
        if self.connected_websockets:
            payload = reading.model_dump_json()
            disconnected = []
            for ws in self.connected_websockets:
                try:
                    await ws.send_text(payload)
                except Exception:
                    disconnected.append(ws)
                    
            for ws in disconnected:
                if ws in self.connected_websockets:
                    self.connected_websockets.remove(ws)

    async def start(self):
        """Starts the MQTT client, the Virtual Device loop, and the FastAPI server."""
        logging.basicConfig(level=logging.INFO)
        
        # Start MQTT client (and test broker if requested)
        await self.mqtt_client.start()
        
        # Start the virtual device simulation loop
        await self.device.start()
        
        # Run FastAPI
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        
        # Cleanup on exit
        await self.device.stop()
        await self.mqtt_client.stop()
