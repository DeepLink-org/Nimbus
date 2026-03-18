import threading
from typing import Dict, Optional

from .status import ComponentStatus, StatusInfo


class StatusMonitor:
    _instance = None
    _lock = threading.Lock()

    DEFAULT_TIMEOUTS = {
        ComponentStatus.IDLE: 100,
        ComponentStatus.READY: float("inf"),
        ComponentStatus.RUNNING: 360,
        ComponentStatus.COMPLETED: float("inf"),
        ComponentStatus.TIMEOUT: float("inf"),
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.components: Dict[str, StatusInfo] = {}
            self.status_timeouts = self.DEFAULT_TIMEOUTS.copy()
            self.initialized = True

    @classmethod
    def get_instance(cls):
        return cls()

    def set_logger(self, logger):
        self.logger = logger

    def set_status_timeout(self, status: ComponentStatus, timeout_seconds: float):
        self.status_timeouts[status] = timeout_seconds

    def set_component_timeouts(self, timeouts: Dict[str, float]):
        converted_timeouts = {}

        for status_name, timeout_value in timeouts.items():
            try:
                if isinstance(status_name, str):
                    status = ComponentStatus[status_name.upper()]
                elif isinstance(status_name, ComponentStatus):
                    status = status_name
                else:
                    self._record(
                        f"Warning: Invalid status type '{type(status_name)}' for status '{status_name}', skipping"
                    )
                    continue

                try:
                    timeout_value = float(timeout_value)
                    if timeout_value < 0:
                        timeout_value = float("inf")

                    converted_timeouts[status] = timeout_value
                    self._record(f"Set timeout for {status.value}: {timeout_value}s")

                except (ValueError, TypeError) as e:
                    self._record(
                        f"Warning: Invalid timeout value '{timeout_value}' for status '{status_name}': {e}, skipping"
                    )
                    continue

            except KeyError:
                self._record(
                    f"Warning: Unknown status '{status_name}', skipping. Available statuses:"
                    f" {[s.name for s in ComponentStatus]}"
                )
                continue
            except Exception as e:
                self._record(f"Error processing status '{status_name}': {e}, skipping")
                continue

        self.status_timeouts.update(converted_timeouts)

    def register_update(self, status_info: StatusInfo):
        self.components[status_info.component_id] = status_info

    def get_all_status(self) -> Dict[str, StatusInfo]:
        return self.components.copy()

    def get_status(self, component_id: str) -> Optional[StatusInfo]:
        return self.components.get(component_id)

    def get_timeout_components(self) -> Dict[str, StatusInfo]:
        timeout_components = {}
        for component_id, status_info in self.components.items():
            if status_info.status == ComponentStatus.TIMEOUT:
                timeout_components[component_id] = status_info
        return timeout_components

    def get_components_length(self):
        return len(self.components)

    def check_and_update_timeouts(self) -> Dict[str, StatusInfo]:
        newly_timeout_components = {}
        components = self.get_all_status()
        for component_id, status_info in components.items():
            if status_info.status == ComponentStatus.TIMEOUT:
                newly_timeout_components[component_id] = status_info
                continue

            time_since_update = status_info.get_status_duration()
            timeout_threshold = self.status_timeouts.get(status_info.status, 300)
            self._record(
                f"[COMPONENT DETAIL] {component_id}: "
                f"Status={status_info.status}, "
                f"Duration={status_info.get_status_duration():.1f}s, "
                f"Threshold={timeout_threshold}s"
            )

            if time_since_update > timeout_threshold:
                self._record(
                    f"Component {component_id} timeout: {status_info.status.value} for {time_since_update:.1f}s"
                    f" (threshold: {timeout_threshold}s)"
                )

                status_info.status = ComponentStatus.TIMEOUT
                status_info.last_update = time_since_update
                newly_timeout_components[component_id] = status_info

        return newly_timeout_components

    def clear(self):
        self.components.clear()
        self._record("Cleared all registered components.")

    def get_component_status_duration(self, component_id: str) -> Optional[float]:
        status_info = self.components.get(component_id)
        if status_info:
            return status_info.get_status_duration()
        return None

    def get_all_status_with_duration(self) -> Dict[str, Dict]:
        result = {}
        for comp_id, status_info in self.components.items():
            result[comp_id] = {
                "status": status_info.status,
                "duration": status_info.get_status_duration(),
                "timeout_threshold": self.status_timeouts.get(status_info.status, 300),
                "last_update": status_info.last_update,
            }
        return result

    def set_check_interval(self, interval_seconds: float):
        self.check_interval = interval_seconds
        self._record(f"Set daemon check interval to {interval_seconds}s")

    def _record(self, info):
        if hasattr(self, "logger") and self.logger is not None:
            self.logger.info(f"[STATUS MONITOR]: {info}")
        else:
            print(f"[STATUS MONITOR]: {info}")
