from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .base import NimbusWorkFlow


@dataclass
class MockTaskCfg:
    name: str
    steps: int


@NimbusWorkFlow.register("MockWorkFlow")
class MockWorkFlow(NimbusWorkFlow):
    """
    A pure CPU, simulation-free workflow implementation of NimbusWorkFlow,
    used to validate the data engine pipeline (load → randomize → plan → render → store).

    Task config file format (JSON or YAML-equivalent) example:

        [
          {"name": "task_a", "steps": 3},
          {"name": "task_b", "steps": 5}
        ]
    """

    def __init__(self, world, task_cfg_path: str, scene_info: Optional[str] = None, random_seed: int = 0, **kwargs):
        # "world" can be None for the mock workflow and is ignored here
        super().__init__(world, task_cfg_path, **kwargs)
        self.random_seed = random_seed
        self.scene_info = scene_info
        self.task_cfg: Optional[MockTaskCfg] = None
        self._seq: List[int] = []
        self._obs: List[int] = []

    # ---- 必选接口 ----
    def parse_task_cfgs(self, task_cfg_path) -> list:
        path = Path(task_cfg_path)
        if not path.exists():
            # If the file does not exist, fall back to a default single-task config
            return [MockTaskCfg(name="default_task", steps=3)]

        text = path.read_text(encoding="utf-8")
        # First try JSON; if it fails, fall back to a simple line-based format: name,steps
        try:
            raw = json.loads(text)
            cfgs = [MockTaskCfg(name=item.get("name", f"task_{i}"), steps=int(item.get("steps", 3))) for i, item in enumerate(raw)]
        except Exception:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            cfgs = []
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(",")]
                name = parts[0] if parts else f"task_{i}"
                steps = int(parts[1]) if len(parts) > 1 else 3
                cfgs.append(MockTaskCfg(name=name, steps=steps))
        return cfgs

    def get_task_name(self) -> str:
        return self.task_cfg.name

    def reset(self, need_preload):
        # Reset internal state for the current task
        self._seq = []
        self._obs = []

    def randomization(self, layout_path=None) -> bool:
        # For the mock workflow, we simply clear state and optionally record that randomization happened
        self._seq = []
        self._obs = []
        return True

    def generate_seq(self) -> list:
        # Generate a simple integer sequence: [0, 1, ..., steps-1]
        steps = max(1, int(self.task_cfg.steps))
        self._seq = list(range(steps))
        return list(self._seq)

    def seq_replay(self, sequence: list) -> int:
        # Square each element in the sequence as a dummy "rendered" observation
        self._obs = [int(x) * int(x) for x in sequence]
        return len(self._obs)

    def save(self, save_path: str) -> int:
        # Write observations into {save_path}/obs.json
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "obs.json").write_text(json.dumps(self._obs, indent=2), encoding="utf-8")
        return len(self._obs)

    # ---- plan mode ----
    def save_seq(self, save_path: str) -> int:
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "seq.json").write_text(json.dumps(self._seq, indent=2), encoding="utf-8")
        return len(self._seq)

    # ---- render mode ----
    def recover_seq(self, seq_path: str) -> list:
        if seq_path is None:
            # If no seq file is provided, generate a fresh sequence for the current task
            return self.generate_seq()
        path = Path(seq_path)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._seq = list(map(int, data))
        except Exception:
            self._seq = []
        return list(self._seq)

    # ---- plan with render mode ----
    def generate_seq_with_obs(self) -> int:
        seq = self.generate_seq()
        return self.seq_replay(seq)

    # ---- pipeline mode ----
    def dump_plan_info(self) -> bytes:
        payload = {
            "task_name": self.task_cfg.name,
            "steps": int(self.task_cfg.steps),
            "sequence": list(self._seq),
        }
        return json.dumps(payload).encode("utf-8")

    def dedump_plan_info(self, ser_obj: bytes) -> object:
        try:
            payload = json.loads(ser_obj.decode("utf-8"))
        except Exception:
            payload = {"sequence": []}
        self._seq = list(map(int, payload.get("sequence", [])))
        return payload

    def randomization_from_mem(self, data: object) -> bool:
        # For the mock workflow, any non-None data is considered a successful randomization source
        return data is not None

    def recover_seq_from_mem(self, data: object) -> list:
        seq = data.get("sequence", [])
        self._seq = list(map(int, seq))
        return list(self._seq)

