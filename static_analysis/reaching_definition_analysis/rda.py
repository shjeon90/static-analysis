from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

from static_analysis.analyzer import Analyzer
from static_analysis.syntax.ast import Stmt


@dataclass(frozen=True)
class Definition:
    var: str
    node_id: int

    def to_key(self) -> str:
        return f"{self.var}@{self.node_id}"


class ReachingDefinitionsAnalyzer(Analyzer[Definition]):
    """
    Reaching Definitions Analysis (forward, may)

    - D: 프로그램 내 등장하는 '정의(definition)'의 유니버스
      * 정의는 (변수명, 특정 CFG assign node id)로 고유화합니다.
    - IN[n]: n에 도달하기 직전에, 어떤 경로들에서든 도달 가능한 정의 집합
    - OUT[n]: node n을 실행한 이후 도달 가능한 정의 집합
    """

    def __init__(self, program: Stmt) -> None:
        self.D: Set[Definition] = set()
        self.var_to_defs: Dict[str, Set[Definition]] = {}
        super().__init__(program)

    @property
    def universe_name(self) -> str:
        return "D"

    def _collect_universe(self) -> None:
        self.D = set()
        self.var_to_defs = {}

        for nid, node in self.cfg_builder.nodes.items():
            if node.kind != "assign":
                continue
            assert node.assign is not None
            var = node.assign.name
            definition = Definition(var=var, node_id=nid)
            self.D.add(definition)
            self.var_to_defs.setdefault(var, set()).add(definition)

    def _compute_gen_kill(self) -> None:
        for nid, node in self.cfg_builder.nodes.items():
            self.GEN[nid] = set()
            self.KILL[nid] = set()

            if node.kind != "assign":
                continue

            assert node.assign is not None
            var = node.assign.name
            definition = Definition(var=var, node_id=nid)

            self.GEN[nid].add(definition)
            # 같은 변수를 정의하는 기존 정의들은 죽입니다.
            self.KILL[nid] = set(self.var_to_defs.get(var, set())) - {definition}

    def analyze(self) -> Dict[str, object]:
        nodes = sorted(self.cfg_builder.nodes.keys())

        # preds 계산 (forward analysis)
        preds: Dict[int, Set[int]] = {nid: set() for nid in nodes}
        for u, vs in self.cfg_builder.succ.items():
            for v in vs:
                preds[v].add(u)

        # 초기값: may 분석은 IN을 empty로 두고 fixpoint로 확장합니다.
        IN: Dict[int, Set[Definition]] = {nid: set() for nid in nodes}
        OUT: Dict[int, Set[Definition]] = {nid: set(self.GEN[nid]) for nid in nodes}

        changed = True
        while changed:
            changed = False
            for nid in nodes:
                if preds[nid]:
                    newIN: Set[Definition] = set()
                    for p in preds[nid]:
                        newIN |= OUT[p]
                else:
                    newIN = set()

                newOUT = set(self.GEN[nid]) | (newIN - self.KILL[nid])

                if newIN != IN[nid] or newOUT != OUT[nid]:
                    IN[nid] = newIN
                    OUT[nid] = newOUT
                    changed = True

        return {"D": set(self.D), "IN": IN, "OUT": OUT, "entry": self.entry, "exit": self.exit}

def format_set(s: Set[Definition]) -> str:
    return Analyzer.format_set(s)

