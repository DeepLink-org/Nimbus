import time
from dataclasses import dataclass, field
from enum import Enum


class ComponentStatus(Enum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"


@dataclass
class StatusInfo:
    component_id: str
    status: ComponentStatus
    last_update: float = field(default_factory=time.time)

    def get_status_duration(self) -> float:
        return time.time() - self.last_update
