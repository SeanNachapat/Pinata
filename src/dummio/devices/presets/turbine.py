import random
from typing import Dict
from dummio.devices.base import VirtualDevice

class WindTurbine(VirtualDevice):
    """
    Simulates a utility-scale wind power turbine generator.
    Tracks wind speeds, rotor rotations, power output, and gearbox/generator temperatures.
    Supports anomalies: 'blade_imbalance' and 'gearbox_slippage'.
    """
    preset_name = "WindTurbine"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_wind = 12.0
        self.base_temp = 55.0
        self.base_power = 1500.0
        
    def generate_sensors(self) -> Dict[str, float]:
        wind_speed = max(1.0, self.base_wind + random.uniform(-1.5, 1.5))
        # Power follows wind speed cubed profile
        power = max(0.0, (wind_speed / 12.0) ** 3 * self.base_power + random.uniform(-25.0, 25.0))
        rotor_rpm = wind_speed * 1.5 + random.uniform(-0.2, 0.2)
        temp = self.base_temp + (power / 1000.0) * 5.0 + random.uniform(-0.5, 0.5)
        
        # Base vibrations
        vib_x = random.uniform(0.1, 0.2)
        vib_y = random.uniform(0.1, 0.2)
        vib_z = random.uniform(0.1, 0.2)
        
        # Apply anomalies
        if self.current_anomaly == "blade_imbalance":
            severity = self.anomaly_intensity
            vib_x += random.uniform(0.8, 1.6) * severity
            vib_y += random.uniform(0.8, 1.6) * severity
            vib_z += random.uniform(0.8, 1.6) * severity
            power *= max(0.4, 0.88 - 0.1 * severity)
            rotor_rpm *= max(0.5, 0.9 - 0.05 * severity)
            
        elif self.current_anomaly == "gearbox_slippage":
            severity = self.anomaly_intensity
            rotor_rpm = max(rotor_rpm + 8.0 * severity, 40.0)
            power *= max(0.1, 0.35 - 0.05 * severity)
            temp += 28.0 * severity
            vib_x += random.uniform(0.4, 0.8) * severity
            vib_y += random.uniform(0.4, 0.8) * severity
            vib_z += random.uniform(0.4, 0.8) * severity
            
        return {
            "WindSpeed": round(wind_speed, 2),
            "RotorRPM": round(rotor_rpm, 2),
            "GeneratorTemp": round(temp, 2),
            "PowerOutput": round(power, 2),
            "VibrationX": round(vib_x, 4),
            "VibrationY": round(vib_y, 4),
            "VibrationZ": round(vib_z, 4)
        }
