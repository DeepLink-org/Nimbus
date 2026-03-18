from abc import abstractmethod

from nimbus.scheduler.instructions import (
    DeDumpInstruction,
    DumpInstruction,
    Instruction,
    LoadSceneInstruction,
    PlanPathInstruction,
    PlanWithRenderInstruction,
    RandomizeLayoutInstruction,
    RenderInstruction,
    StoreInstruction,
)
from nimbus.utils.types import (
    DEDUMPER,
    DUMPER,
    LAYOUT_RANDOM_GENERATOR,
    PLAN_WITH_RENDER,
    RENDERER,
    SCENE_LOADER,
    SEQ_PLANNER,
    WRITER,
    StageInput,
)


class Stage:
    def __init__(self, config):
        self.config = config
        self.instructions: list[Instruction] = []
        self.output_queue = None

    @abstractmethod
    def run(self, stage_input):
        raise NotImplementedError()


class LoadStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        if SCENE_LOADER in config:
            self.instructions.append(LoadSceneInstruction(config[SCENE_LOADER]))
        if LAYOUT_RANDOM_GENERATOR in config:
            self.instructions.append(RandomizeLayoutInstruction(config[LAYOUT_RANDOM_GENERATOR]))

    def run(self, stage_input: StageInput):
        for instruction in self.instructions:
            scene_iterator = instruction.run(stage_input)
            stage_input = StageInput((scene_iterator,), {})
        return stage_input


class PlanStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        if SEQ_PLANNER in config:
            self.instructions.append(PlanPathInstruction(config[SEQ_PLANNER]))

    def run(self, stage_input: StageInput):
        for instruction in self.instructions:
            scene_seqs_iter = instruction.run(stage_input)
            stage_input = StageInput((scene_seqs_iter,), {})
        return stage_input


class RenderStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        self.instructions.append(RenderInstruction(config[RENDERER]))

    def run(self, stage_input: StageInput):
        for instruction in self.instructions:
            obs_iter = instruction.run(stage_input)
            stage_input = StageInput((obs_iter,), {})
        return stage_input


class PlanWithRenderStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        self.instructions.append(PlanWithRenderInstruction(config[PLAN_WITH_RENDER]))

    def run(self, stage_input: StageInput):
        for instruction in self.instructions:
            scene_seqs_iter = instruction.run(stage_input)
            stage_input = StageInput((scene_seqs_iter,), {})
        return stage_input


class StoreStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        if WRITER in config:
            self.instructions.append(StoreInstruction(config[WRITER]))

    def run(self, stage_input: StageInput):
        for instruction in self.instructions:
            store_iter = instruction.run(stage_input)
            stage_input = StageInput((store_iter,), {})
        return stage_input


class DumpStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        self.instructions.append(DumpInstruction(config[DUMPER]))

    def run(self, stage_input: StageInput, output_queue=None):
        for instruction in self.instructions:
            dump_iter = instruction.run(stage_input, output_queue)
            stage_input = StageInput((dump_iter,), {})
        return stage_input


class DedumpStage(Stage):
    def __init__(self, config):
        super().__init__(config)
        if DEDUMPER in config:
            self.instructions.append(DeDumpInstruction(config[DEDUMPER]))
        if SCENE_LOADER in config:
            self.instructions.append(LoadSceneInstruction(config[SCENE_LOADER]))
        if LAYOUT_RANDOM_GENERATOR in config:
            self.instructions.append(RandomizeLayoutInstruction(config[LAYOUT_RANDOM_GENERATOR]))
        if SEQ_PLANNER in config:
            self.instructions.append(PlanPathInstruction(config[SEQ_PLANNER]))

    def run(self, stage_input: StageInput, input_queue=None):
        if input_queue is not None:
            self.input_queue = input_queue

        for instruction in self.instructions:
            if isinstance(instruction, DeDumpInstruction):
                result = instruction.run(stage_input, input_queue)
            else:
                result = instruction.run(stage_input)
            stage_input = StageInput((result,), {})
        return stage_input
