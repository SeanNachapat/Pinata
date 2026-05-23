# Dummio 🤖🌡️

Dummio is an open-source virtual IoT device service and Python package. It lets developers spin up fake sensor devices — like industrial motors, freezers, and power meters — that behave exactly like real hardware. 

With Dummio, you get a stand-in device with a realistic data stream, complete with an **event injection API** to trigger failures (spikes, dropouts, drift) on demand, all tagged with ground truth labels. 

Dummio acts as the perfect companion data source for ML pipelines and anomaly detection libraries like [`edgewatch`](https://github.com/your-org/edgewatch).

## Features

- **Real-World Device Presets:** Instantly spin up complex, physically realistic virtual devices (starting with an Industrial Motor).
- **MQTT Integration:** Dummio behaves exactly like real hardware by acting as an MQTT client. (Includes a zero-setup test broker for data scientists).
- **REST & WebSocket API:** Tap into the live data stream directly or inject anomalies on the fly.
- **Ground Truth Labels:** Every data point is tagged with a label, making it trivial to train and validate anomaly detection models.

## Installation

*(Note: Not yet published to PyPI)*

```bash
git clone https://github.com/your-org/dummio.git
cd dummio
pip install -e .
```

## Quickstart

Start a virtual Industrial Motor that streams data to an MQTT broker:

```python
import asyncio
from dummio.devices import IndustrialMotor
from dummio import Server

async def main():
    # Spin up an Industrial Motor
    # Includes a temporary zero-setup MQTT broker on localhost:1883
    motor = IndustrialMotor(start_test_broker=True)
    
    # Expose the REST/WebSocket API and start streaming
    server = Server(device=motor, port=8000)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

Once running, you can inject an anomaly via REST:
```bash
curl -X POST http://localhost:8000/api/inject \
    -H "Content-Type: application/json" \
    -d '{"anomaly_type": "bearing_wear", "duration": 60}'
```

## License
MIT License. See [LICENSE](LICENSE) for details.
