from nimbus.components.dump import BaseDumper


class EnvDumper(BaseDumper):
    def __init__(self, data_iter, output_queue=None):
        super().__init__(data_iter, output_queue=output_queue)

    def dump(self, seq, obs):
        ser_obj = self.scene.wf.dump_plan_info()
        return ser_obj
