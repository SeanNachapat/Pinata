from .base import VirtualDevice
from .presets.motor import IndustrialMotor
from .presets.turbine import WindTurbine
from .presets.hvac import SmartHVAC

__all__ = ["VirtualDevice", "IndustrialMotor", "WindTurbine", "SmartHVAC"]
