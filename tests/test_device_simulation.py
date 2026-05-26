import pytest
from dummio.devices import IndustrialMotor, WindTurbine, SmartHVAC
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
    assert reading["Temperature"] >= 48.0

def test_clear_anomaly():
    motor = IndustrialMotor()
    req = AnomalyInjectionRequest(anomaly_type="mechanical_jam", duration_seconds=10)
    motor.inject_anomaly(req)
    
    assert motor.current_anomaly == "mechanical_jam"
    motor.clear_anomaly()
    
    assert motor.current_anomaly is None

def test_wind_turbine_default():
    turbine = WindTurbine()
    reading = turbine.generate_sensors()
    
    # Check normal ranges
    assert 8.0 <= reading["WindSpeed"] <= 16.0
    assert 10.0 <= reading["RotorRPM"] <= 25.0
    assert 1000.0 <= reading["PowerOutput"] <= 3000.0

def test_wind_turbine_blade_imbalance():
    turbine = WindTurbine()
    req = AnomalyInjectionRequest(anomaly_type="blade_imbalance")
    turbine.inject_anomaly(req)
    reading = turbine.generate_sensors()
    
    # Vibration should spike
    assert reading["VibrationX"] >= 0.8
    # Power drops slightly due to rotor drag
    assert reading["PowerOutput"] <= 2800.0

def test_smart_hvac_default():
    hvac = SmartHVAC()
    reading = hvac.generate_sensors()
    
    # Check default temperature cooling system
    assert 100.0 <= reading["CompressorPressure"] <= 160.0
    assert 20.0 <= reading["RoomTemp"] <= 26.0

def test_smart_hvac_leak():
    hvac = SmartHVAC()
    req = AnomalyInjectionRequest(anomaly_type="refrigerant_leak")
    hvac.inject_anomaly(req)
    reading = hvac.generate_sensors()
    
    # Pressure should drop below base
    assert reading["CompressorPressure"] <= 100.0

