"""
Dummio Quickstart Template

Use this template as a starting point to spin up your virtual devices.
You can swap out the `IndustrialMotor` for any other preset, or even
build your own custom VirtualDevice.
"""

import asyncio
from dummio import Server

# 1. Import the device preset you want to use
from dummio.devices import IndustrialMotor

async def main():
    # 2. Instantiate your device
    # Set start_test_broker=True if you don't have Mosquitto/AWS IoT running
    # and just want Dummio to spin up a quick local broker for you.
    device = IndustrialMotor(start_test_broker=True)
    
    # 3. Create the server
    # The server automatically manages the REST API, WebSockets, and MQTT
    server = Server(
        device=device, 
        host="0.0.0.0", 
        port=8000,
        # mqtt_host="192.168.1.50" # Point this to your real broker if you have one
    )
    
    print(f"Starting Dummio Simulation for: {device.preset_name}")
    print(f"REST API: http://localhost:{server.port}")
    print(f"WebSocket: ws://localhost:{server.port}/ws")
    
    # 4. Start the engine!
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
