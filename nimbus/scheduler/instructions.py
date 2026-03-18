from abc import abstractmethod

from nimbus.components.dedump import dedumper_dict
from nimbus.components.dump import dumper_dict
from nimbus.components.load import layout_randomizer_dict, scene_loader_dict
from nimbus.components.plan_with_render import plan_with_render_dict
from nimbus.components.planner import seq_planner_dict
from nimbus.components.render import renderer_dict
from nimbus.components.store import writer_dict
from nimbus.utils.types import ARGS, PLANNER, TYPE


class Instruction:
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def run(self, stage_input):
        raise NotImplementedError()


class LoadSceneInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.scene_iter = scene_loader_dict[self.config[TYPE]]

    def run(self, stage_input):
        pack_iter = pack_iter = stage_input.Args[0] if stage_input.Args is not None else None
        return self.scene_iter(pack_iter=pack_iter, **self.config.get(ARGS, {}))


class RandomizeLayoutInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.layout_randomlizer = layout_randomizer_dict[self.config[TYPE]]

    def run(self, stage_input):
        scene_iterator = stage_input.Args[0]
        extend_scene_iterator = self.layout_randomlizer(scene_iterator, **self.config.get(ARGS, {}))
        return extend_scene_iterator


class PlanPathInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.seq_planner = seq_planner_dict[self.config[TYPE]]

    def run(self, stage_input):
        scene_iter = stage_input.Args[0]
        planner_cfg = self.config[PLANNER] if PLANNER in self.config else None
        return self.seq_planner(scene_iter, planner_cfg, **self.config.get(ARGS, {}))


class RenderInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.renderer = renderer_dict[self.config[TYPE]]

    def run(self, stage_input):
        scene_seqs_iter = stage_input.Args[0]
        obs_iter = self.renderer(scene_seqs_iter, **self.config.get(ARGS, {}))
        return obs_iter


class PlanWithRenderInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.plan_with_render = plan_with_render_dict[config[TYPE]]

    def run(self, stage_input):
        scene_iter = stage_input.Args[0]
        plan_with_render_iter = self.plan_with_render(scene_iter, **self.config.get(ARGS, {}))
        return plan_with_render_iter


class StoreInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.writer = writer_dict[config[TYPE]]

    def run(self, stage_input):
        seqs_obs_iter = stage_input.Args[0]
        store_iter = self.writer(seqs_obs_iter, **self.config.get(ARGS, {}))
        return store_iter


class DumpInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.dumper = dumper_dict[config[TYPE]]

    def run(self, stage_input, output_queue=None):
        seqs_obs_iter = stage_input.Args[0]
        dump_iter = self.dumper(seqs_obs_iter, output_queue=output_queue, **self.config.get(ARGS, {}))
        return dump_iter


class DeDumpInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
        self.dedumper = dedumper_dict[config[TYPE]]

    def run(self, stage_input, input_queue=None):
        dump_iter = self.dedumper(input_queue=input_queue, **self.config.get(ARGS, {}))
        return dump_iter


class ComposeInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)


class AnnotateDataInstruction(Instruction):
    def __init__(self, config):
        super().__init__(config)
