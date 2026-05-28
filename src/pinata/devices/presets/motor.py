import random
from typing import Dict
from dummio.devices.base import VirtualDevice

class IndustrialMotor(VirtualDevice):
    """
    Simulates an industrial motor with sensors for RPM, Vibration, Temperature, and Current.
    Supports anomalies: 'bearing_wear' and 'mechanical_jam'.
    """
    preset_name = "IndustrialMotor"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_rpm = 1500.0
        self.base_temp = 45.0
        self.base_current = 10.0
        
        # Track state for gradual anomalies
        self.wear_factor = 0.0
        
    def generate_sensors(self) -> Dict[str, float]:
        # Default states with some noise
        rpm = self.base_rpm + random.uniform(-10, 10)
        vib_x = random.uniform(0.05, 0.15)
        vib_y = random.uniform(0.05, 0.15)
        vib_z = random.uniform(0.05, 0.15)
        temp = self.base_temp + random.uniform(-1, 1)
        current = self.base_current + random.uniform(-0.5, 0.5)
        
        # Apply anomalies
        if self.current_anomaly == "bearing_wear":
            self.wear_factor = min(self.wear_factor + 0.05 * self.anomaly_intensity, 5.0)
            vib_x += self.wear_factor * random.uniform(0.5, 1.0)
            vib_y += self.wear_factor * random.uniform(0.5, 1.0)
            vib_z += self.wear_factor * random.uniform(0.5, 1.0)
            temp += self.wear_factor * 2.0
            current += self.wear_factor * 1.5
            rpm -= self.wear_factor * 5.0 # Slight drop in efficiency
            
        elif self.current_anomaly == "mechanical_jam":
            rpm = 0.0
            vib_x = random.uniform(0.0, 0.01)
            vib_y = random.uniform(0.0, 0.01)
            vib_z = random.uniform(0.0, 0.01)
            current = 50.0 + random.uniform(-2, 2)
            temp += 5.0 # Heats up quickly
            
        else:
            # Gradually cool down/repair if no anomaly
            self.wear_factor = max(0.0, self.wear_factor - 0.1)
            # Cool down temperature back to base if it got heated
            self.base_temp = max(45.0, self.base_temp - 0.1)
            
        return {
            "RPM": round(rpm, 2),
            "VibrationX": round(vib_x, 4),
            "VibrationY": round(vib_y, 4),
            "VibrationZ": round(vib_z, 4),
            "Temperature": round(temp, 2),
            "Current": round(current, 2)
        }
