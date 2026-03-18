import time
from threading import Lock


class Task:
    def __init__(self):
        pass

    def update_state(self, state):
        pass


class TaskBoard:
    def __init__(self):
        self.tasks = []
        self.flying_tasks = []
        self.finished_tasks = []
        self.task_cnt = 0
        self.task_lock = Lock()
        self.flying_task_lock = Lock()

    def reg_task(self, task):
        with self.task_lock:
            self.tasks.append(task)
        self.task_cnt += 1

    def get_tasks(self, timeout=0):
        st_time = time.time()
        while len(self.tasks) == 0:
            if time.time() - st_time > timeout:
                return []
            pass
        with self.task_lock:
            tasks = self.tasks.copy()
            self.tasks = []
        return tasks

    def commit_task(self, tasks):
        raise NotImplementedError("commit_task not implemented")

    def finished(self):
        raise NotImplementedError("finished not implemented")
