from nimbus.components.data.observation import Observations
from nimbus.components.render import BaseRenderer


class EnvRenderer(BaseRenderer):
    """
    Renderer for environment simulation.
    """

    def __init__(self, scene_seq_iter):
        super().__init__(scene_seq_iter)

    def _lazy_init(self):
        pass

    def _close_resource(self):
        pass

    def generate_obs(self, seq):
        wf = self.scene.wf
        obs_num = wf.seq_replay(seq.data)
        if obs_num <= 0:
            return None
        obs = Observations(seq.scene_name, seq.index, length=obs_num)
        return obs
