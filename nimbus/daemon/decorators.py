from functools import wraps

from nimbus.daemon import ComponentStatus, StatusReporter


def status_monitor(running_status=ComponentStatus.RUNNING, completed_status=ComponentStatus.COMPLETED):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, "status_reporter"):
                self.status_reporter = StatusReporter(self.__class__.__name__)

            self.status_reporter.update_status(running_status)

            try:
                result = func(self, *args, **kwargs)
                self.status_reporter.update_status(completed_status)
                return result
            except Exception as e:
                raise e

        return wrapper

    return decorator
