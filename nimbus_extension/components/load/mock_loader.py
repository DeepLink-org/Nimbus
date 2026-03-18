from nimbus.components.data.iterator import Iterator
from nimbus.components.data.package import Package
from nimbus.components.data.scene import Scene
from nimbus.components.load import SceneLoader
from nimbus.daemon import ComponentStatus, StatusReporter
from nimbus.daemon.decorators import status_monitor
from nimbus.utils.flags import get_random_seed
from workflows import import_extensions
from workflows.base import create_workflow


class MockLoader(SceneLoader):
    """A SceneLoader that does not depend on Isaac Sim, dedicated to driving MockWorkFlow.

    Responsibilities:
    - Create a MockWorkFlow instance
    - For each task, generate a lightweight Scene object that only carries the workflow and metadata
    """

    def __init__(
        self,
        pack_iter: Iterator[Package],
        cfg_path: str,
        workflow_type: str = "MockWorkFlow",
        task_repeat: int = -1,
        need_preload: bool = False,
    ):
        super().__init__(pack_iter)

        self.status_reporter = StatusReporter(self.__class__.__name__)
        self.status_reporter.update_status(ComponentStatus.IDLE)
        self.need_preload = need_preload
        self.task_repeat_cnt = task_repeat
        self.task_repeat_idx = 0
        self.workflow_type = workflow_type

        # Import and create the workflow (no world object needed for the mock workflow)
        import_extensions(workflow_type)
        self.workflow = create_workflow(
            workflow_type,
            world=None,
            task_cfg_path=cfg_path,
            scene_info=None,
            random_seed=get_random_seed(),
        )

        self.scene = None
        self.task_finish = False
        self.cur_index = 0

        self.status_reporter.update_status(ComponentStatus.READY)

    @status_monitor()
    def _init_next_task(self):
        if self.scene is not None and self.task_repeat_cnt > 0 and self.task_repeat_idx < self.task_repeat_cnt:
            self.logger.info(f"Task execute times {self.task_repeat_idx + 1}/{self.task_repeat_cnt}")
            self.workflow.init_task(self.cur_index - 1, self.need_preload)
            self.task_repeat_idx += 1
            scene = Scene(
                name=self.workflow.get_task_name(),
                wf=self.workflow,
                task_id=self.cur_index - 1,
                task_exec_num=self.task_repeat_idx,
                simulation_app=None,
            )
            return scene

        if self.cur_index >= len(self.workflow.task_cfgs):
            self.logger.info("No more tasks to load, stopping iteration.")
            raise StopIteration

        self.logger.info(f"Loading task {self.cur_index + 1}/{len(self.workflow.task_cfgs)}")
        self.workflow.init_task(self.cur_index, self.need_preload)
        self.task_repeat_idx = 1
        scene = Scene(
            name=self.workflow.get_task_name(),
            wf=self.workflow,
            task_id=self.cur_index,
            task_exec_num=self.task_repeat_idx,
            simulation_app=None,
        )
        self.cur_index += 1
        return scene

    def load_asset(self) -> Scene:
        try:
            # Standalone mode: iterate tasks directly from the workflow
            if self.pack_iter is None:
                self.scene = self._init_next_task()
            # Pipeline mode: read task_id from the incoming package
            else:
                package = next(self.pack_iter)
                self.cur_index = package.task_id

                if self.scene is None:
                    self.scene = self._init_next_task()
                elif self.cur_index > self.scene.task_id:
                    self.scene = self._init_next_task()

                # If upstream has serialized plan_info, deserialize and attach it to the scene
                if package.data is not None:
                    package.data = self.scene.wf.dedump_plan_info(package.data)
                    self.scene.add_plan_info(package.data)

            return self.scene
        except StopIteration:
            raise StopIteration
        except Exception as e:
            raise e

