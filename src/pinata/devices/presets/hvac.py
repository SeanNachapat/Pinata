import random
from typing import Dict
from dummio.devices.base import VirtualDevice

class SmartHVAC(VirtualDevice):
    """
    Simulates a smart commercial HVAC system.
    Tracks room temperature, ambient temperature, compressor pressures, and electricity loads.
    Supports anomalies: 'refrigerant_leak' and 'fan_failure'.
    """
    preset_name = "SmartHVAC"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_room_temp = 21.0
        self.ambient_temp = 32.0
        self.current_room_temp = 25.0
        self.compressor_pressure = 120.0
        self.power_load = 3.5
        
    def generate_sensors(self) -> Dict[str, float]:
        # HVAC turns cooling on if temperature is above target
        cooling_power = 0.0
        if self.current_room_temp > self.target_room_temp:
            cooling_power = min(1.0, (self.current_room_temp - self.target_room_temp) / 2.0)
            
        pressure = self.compressor_pressure + cooling_power * 30.0 + random.uniform(-1.5, 1.5)
        power = cooling_power * self.power_load + 0.2 + random.uniform(-0.05, 0.05)
        
        # Heat transfer model
        heat_gain = (self.ambient_temp - self.current_room_temp) * 0.05
        heat_removal = cooling_power * 0.16
        self.current_room_temp += heat_gain - heat_removal + random.uniform(-0.02, 0.02)
        
        vib_x = cooling_power * 0.06 + random.uniform(0.01, 0.03)
        vib_y = cooling_power * 0.06 + random.uniform(0.01, 0.03)
        vib_z = cooling_power * 0.06 + random.uniform(0.01, 0.03)
        
        # Apply anomalies
        if self.current_anomaly == "refrigerant_leak":
            severity = self.anomaly_intensity
            pressure = max(15.0, pressure - 75.0 * severity + random.uniform(-2, 2))
            self.current_room_temp += 0.3 * severity
            power = max(0.5, 1.2 + random.uniform(-0.05, 0.05))
            
        elif self.current_anomaly == "fan_failure":
            severity = self.anomaly_intensity
            pressure += 85.0 * severity
            power = self.power_load * (1.2 + 0.3 * severity)
            self.current_room_temp += 0.15 * severity
            vib_x += random.uniform(0.35, 0.7) * severity
            vib_y += random.uniform(0.35, 0.7) * severity
            vib_z += random.uniform(0.35, 0.7) * severity
            
        return {
            "RoomTemp": round(self.current_room_temp, 2),
            "AmbientTemp": round(self.ambient_temp, 2),
            "CompressorPressure": round(pressure, 2),
            "PowerLoad": round(power, 2),
            "VibrationX": round(vib_x, 4),
            "VibrationY": round(vib_y, 4),
            "VibrationZ": round(vib_z, 4)
        }
