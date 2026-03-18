import threading
import time

from .status import ComponentStatus, StatusInfo
from .status_monitor import StatusMonitor


class StatusReporter:
    def __init__(self, component_id: str):
        self.component_id = component_id
        self._status_info = StatusInfo(component_id, ComponentStatus.IDLE)
        self._lock = threading.Lock()

    def update_status(self, status: ComponentStatus):
        with self._lock:
            self._status_info = StatusInfo(component_id=self.component_id, status=status, last_update=time.time())
            StatusMonitor.get_instance().register_update(self._status_info)

    def get_status(self) -> StatusInfo:
        with self._lock:
            return self._status_info
