from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class ComponentStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class DeviceOperationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNREACHABLE = "UNREACHABLE"
    AUTH_FAILED = "AUTH_FAILED"
    SKIPPED = "SKIPPED"


class DeviceOperationResult(BaseModel):
    execution_id: str
    job_id: str
    device_id: str
    ip_address: str
    vendor: str
    segment: str
    operation: str
    status: DeviceOperationStatus
    raw_output: Optional[str] = None
    normalized_data: Optional[dict] = None
    error_message: Optional[str] = None
    executed_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    duration_ms: Optional[int] = None

    class Config:
        use_enum_values = True


class ComponentHealth(BaseModel):
    component_name: str
    instance_id: str
    status: ComponentStatus
    error_count: int = 0
    processed_count: int = 0
    error_threshold: int = 100
    last_heartbeat: datetime = Field(
        default_factory=datetime.utcnow
    )
    error_message: Optional[str] = None

    @property
    def is_threshold_reached(self) -> bool:
        return self.error_count >= self.error_threshold

    class Config:
        use_enum_values = True


class RawOutputMessage(BaseModel):
    execution_id: str
    job_id: str
    device_id: str
    ip_address: str
    vendor: str
    segment: str
    operation: str
    raw_output: str
    produced_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    class Config:
        use_enum_values = True


class NormalizedOutputMessage(BaseModel):
    execution_id: str
    job_id: str
    device_id: str
    ip_address: str
    vendor: str
    segment: str
    operation: str
    normalized_data: dict
    produced_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    class Config:
        use_enum_values = True
