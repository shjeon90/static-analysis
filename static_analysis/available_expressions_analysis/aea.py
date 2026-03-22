from __future__ import annotations

from typing import Dict, Set

from static_analysis.syntax.ast import (
    ArithExpr,
    Assign,
    BinOp,
    BoolExpr,
    If,
    Skip,
    Seq,
    Stmt,
    While,
)
from static_analysis.analyzer import Analyzer

class AvailableExpressionsAnalyzer(Analyzer[BinOp]):
    """
    Available Expressions Analysis (forward, must)

    - E: candidate arithmetic expressions (BinOp nodes) appearing in the program
    - IN[n]: expressions available on all paths immediately before n
    - OUT[n]: result after n's transfer function (gen/kill)
    """

    def __init__(self, program: Stmt) -> None:
        self.expr_varset: Dict[BinOp, Set[str]] = {}
        self.E: Set[BinOp] = set()
        super().__init__(program)

    @property
    def universe_name(self) -> str:
        return "E"

    def _add_expr_candidate(self, binop: BinOp) -> None:
        if binop not in self.expr_varset:
            self.expr_varset[binop] = set(binop.vars())
        self.E.add(binop)

    def _collect_universe_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, Skip):
            return

        if isinstance(stmt, Assign):
            for c in stmt.expr.candidates():
                self._add_expr_candidate(c)
            return

        if isinstance(stmt, Seq):
            self._collect_universe_stmt(stmt.first)
            self._collect_universe_stmt(stmt.second)
            return

        if isinstance(stmt, If):
            for c in stmt.cond.candidates():
                self._add_expr_candidate(c)
            self._collect_universe_stmt(stmt.then_branch)
            self._collect_universe_stmt(stmt.else_branch)
            return

        if isinstance(stmt, While):
            for c in stmt.cond.candidates():
                self._add_expr_candidate(c)
            self._collect_universe_stmt(stmt.body)
            return

        raise TypeError(f"Unsupported Stmt type: {type(stmt)}")

    def _collect_universe(self) -> None:
        self.expr_varset = {}
        self.E = set()
        self._collect_universe_stmt(self.program)

    def _candidates_in_arith(self, expr: ArithExpr) -> Set[BinOp]:
        return set(expr.candidates())

    def _candidates_in_bool(self, b: BoolExpr) -> Set[BinOp]:
        return set(b.candidates())

    def _compute_gen_kill(self) -> None:
        for nid, node in self.cfg_builder.nodes.items():
            if node.kind == "skip":
                self.GEN[nid] = set()
                self.KILL[nid] = set()
                continue

            if node.kind == "assign":
                assert node.assign is not None
                self.GEN[nid] = self._candidates_in_arith(node.assign.expr)
                kill: Set[BinOp] = set()
                for key, varset in self.expr_varset.items():
                    if node.assign.name in varset:
                        kill.add(key)
                self.KILL[nid] = kill
                continue

            if node.kind == "cond":
                assert node.cond is not None
                self.GEN[nid] = self._candidates_in_bool(node.cond)
                self.KILL[nid] = set()
                continue

            raise ValueError(f"Unknown node kind: {node.kind}")

    def analyze(self) -> Dict[str, object]:
        nodes = sorted(self.cfg_builder.nodes.keys())

        # Compute preds (forward analysis is phrased in terms of preds)
        preds: Dict[int, Set[int]] = {nid: set() for nid in nodes}
        for u, vs in self.cfg_builder.succ.items():
            for v in vs:
                preds[v].add(u)

        # Initial values
        IN: Dict[int, Set[BinOp]] = {}
        OUT: Dict[int, Set[BinOp]] = {}

        for nid in nodes:
            if not preds[nid]:
                IN[nid] = set()
            else:
                IN[nid] = set(self.E)

            OUT[nid] = self.GEN[nid] | (IN[nid] - self.KILL[nid])

        # fixpoint
        changed = True
        while changed:
            changed = False
            for nid in nodes:
                # meet: intersection over OUT[p]
                if not preds[nid]:
                    newIN = set()
                else:
                    it = iter(preds[nid])
                    first = next(it)
                    newIN = set(OUT[first])
                    for p in it:
                        newIN &= OUT[p]

                newOUT = self.GEN[nid] | (newIN - self.KILL[nid])
                if newIN != IN[nid] or newOUT != OUT[nid]:
                    IN[nid] = newIN
                    OUT[nid] = newOUT
                    changed = True

        return {"E": set(self.E), "IN": IN, "OUT": OUT, "entry": self.entry, "exit": self.exit}

def format_set(s: Set[BinOp]) -> str:
    return Analyzer.format_set(s)

