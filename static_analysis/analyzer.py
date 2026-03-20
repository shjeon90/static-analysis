from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Generic, Set, TypeVar

from static_analysis.cfg import CFGBuilder
from static_analysis.syntax.ast import Stmt

FactT = TypeVar("FactT")


class Analyzer(ABC, Generic[FactT]):
    def __init__(self, program: Stmt) -> None:
        self.program = program
        self.cfg_builder = CFGBuilder()
        self.entry, self.exit = self.cfg_builder.build(program)

        self.GEN: Dict[int, Set[FactT]] = {}
        self.KILL: Dict[int, Set[FactT]] = {}

        self._collect_universe()
        self._compute_gen_kill()

    @property
    @abstractmethod
    def universe_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _collect_universe(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _compute_gen_kill(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def analyze(self) -> Dict[str, object]:
        raise NotImplementedError

    @staticmethod
    def format_set(s: Set[FactT]) -> str:
        if not s:
            return "{}"
        return "{" + ", ".join(sorted(v.to_key() for v in s)) + "}"

    def print_result(self, result: Dict[str, object]) -> None:
        print(f"Universe {self.universe_name} =", self.format_set(result[self.universe_name]))
        print("entry =", result["entry"], "exit =", result["exit"])
        for nid in sorted(result["IN"].keys()):
            inn = result["IN"][nid]
            out = result["OUT"][nid]
            node_kind = self.cfg_builder.nodes[nid].kind
            print(f"Node {nid} ({node_kind}): IN={self.format_set(inn)} OUT={self.format_set(out)}")

