from pydantic import BaseModel, Field
from typing import Optional

class AnomalyInjectionRequest(BaseModel):
    """Payload for the REST API to trigger a failure on a device."""
    anomaly_type: str = Field(..., description="String identifier of the anomaly (e.g., 'bearing_wear')")
    duration_seconds: Optional[int] = Field(default=None, description="How long the anomaly should last before reverting to normal. If None, it lasts until manually cleared.")
    intensity: Optional[float] = Field(default=1.0, description="Multiplier or scale for the severity of the anomaly.")
