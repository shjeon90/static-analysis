from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

from static_analysis.analyzer import Analyzer
from static_analysis.syntax.ast import (
    ArithExpr,
    BoolAnd,
    BoolConst,
    BoolExpr,
    BoolNot,
    BoolOr,
    Compare,
    Stmt,
)


def _vars_in_arith(expr: ArithExpr) -> Set[str]:
    return set(expr.vars())


def _vars_in_bool(b: BoolExpr) -> Set[str]:
    if isinstance(b, BoolConst):
        return set()
    if isinstance(b, Compare):
        return _vars_in_arith(b.left) | _vars_in_arith(b.right)
    if isinstance(b, BoolAnd):
        return _vars_in_bool(b.left) | _vars_in_bool(b.right)
    if isinstance(b, BoolOr):
        return _vars_in_bool(b.left) | _vars_in_bool(b.right)
    if isinstance(b, BoolNot):
        return _vars_in_bool(b.expr)
    raise TypeError(f"Unsupported BoolExpr type: {type(b)}")


@dataclass(frozen=True)
class VarFact:
    name: str

    def to_key(self) -> str:
        return self.name


class LiveVariablesAnalyzer(Analyzer[VarFact]):
    """
    Live Variables Analysis (backward, may)

    - V: all variables appearing in the program
    - OUT[n]: variables live on some path immediately after n
    - IN[n]: variables live immediately before n

    IN[n] = GEN[n] ∪ (OUT[n] − KILL[n]), OUT[n] = ⋃_{s ∈ succ(n)} IN[s]
    """

    def __init__(self, program: Stmt) -> None:
        self.V: Set[VarFact] = set()
        self._name_to_vf: Dict[str, VarFact] = {}
        super().__init__(program)

    @property
    def universe_name(self) -> str:
        return "V"

    def _collect_universe(self) -> None:
        names: Set[str] = set()
        for _, node in self.cfg_builder.nodes.items():
            if node.kind == "assign":
                assert node.assign is not None
                names.add(node.assign.name)
                names |= _vars_in_arith(node.assign.expr)
            elif node.kind == "cond":
                assert node.cond is not None
                names |= _vars_in_bool(node.cond)

        self.V = {VarFact(n) for n in names}
        self._name_to_vf = {vf.name: vf for vf in self.V}

    def _compute_gen_kill(self) -> None:
        for nid, node in self.cfg_builder.nodes.items():
            if node.kind == "skip":
                self.GEN[nid] = set()
                self.KILL[nid] = set()
                continue

            if node.kind == "assign":
                assert node.assign is not None
                a = node.assign
                self.GEN[nid] = {self._name_to_vf[v] for v in _vars_in_arith(a.expr) if v in self._name_to_vf}
                self.KILL[nid] = {self._name_to_vf[a.name]}
                continue

            if node.kind == "cond":
                assert node.cond is not None
                self.GEN[nid] = {self._name_to_vf[v] for v in _vars_in_bool(node.cond) if v in self._name_to_vf}
                self.KILL[nid] = set()
                continue

            raise ValueError(f"Unknown node kind: {node.kind}")

    def analyze(self) -> Dict[str, object]:
        nodes = sorted(self.cfg_builder.nodes.keys())
        succ = self.cfg_builder.succ

        IN: Dict[int, Set[VarFact]] = {}
        OUT: Dict[int, Set[VarFact]] = {}

        for nid in nodes:
            OUT[nid] = set()
            IN[nid] = set(self.GEN[nid]) | (OUT[nid] - self.KILL[nid])

        changed = True
        while changed:
            changed = False
            for nid in nodes:
                if not succ[nid]:
                    newOUT: Set[VarFact] = set()
                else:
                    newOUT = set()
                    for s in succ[nid]:
                        newOUT |= IN[s]

                newIN = set(self.GEN[nid]) | (newOUT - self.KILL[nid])

                if newIN != IN[nid] or newOUT != OUT[nid]:
                    IN[nid] = newIN
                    OUT[nid] = newOUT
                    changed = True

        return {"V": set(self.V), "IN": IN, "OUT": OUT, "entry": self.entry, "exit": self.exit}


def format_set(s: Set[VarFact]) -> str:
    return Analyzer.format_set(s)
