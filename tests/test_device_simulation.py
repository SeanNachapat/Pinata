import pytest
from dummio.devices import IndustrialMotor
from dummio.models import AnomalyInjectionRequest

def test_motor_default_behavior():
    motor = IndustrialMotor()
    reading = motor.generate_sensors()
    
    # Check that reading is within normal bounds
    assert 1490 <= reading["RPM"] <= 1510
    assert 44 <= reading["Temperature"] <= 46
    assert 9.5 <= reading["Current"] <= 10.5

def test_motor_jam_anomaly():
    motor = IndustrialMotor()
    req = AnomalyInjectionRequest(anomaly_type="mechanical_jam", duration_seconds=10)
    motor.inject_anomaly(req)
    
    reading = motor.generate_sensors()
    
    assert reading["RPM"] == 0.0
    assert reading["Current"] >= 48.0
    assert reading["Temperature"] >= 50.0

def test_clear_anomaly():
    motor = IndustrialMotor()
    req = AnomalyInjectionRequest(anomaly_type="mechanical_jam", duration_seconds=10)
    motor.inject_anomaly(req)
    
    assert motor.current_anomaly == "mechanical_jam"
    motor.clear_anomaly()
    
    assert motor.current_anomaly is None
