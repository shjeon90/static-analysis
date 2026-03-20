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
from static_analysis.cfg import CFGBuilder

class AvailableExpressionsAnalyzer:
    """
    Available Expressions Analysis (forward, must)

    - E: 프로그램 내 등장하는 후보 '산술 표현식'(BinOp 노드들)
    - IN[n]  : n에 도달하기 직전에 모든 경로에서 available인 표현식 집합
    - OUT[n] : n의 전이(gen/kill)를 반영한 결과
    """

    def __init__(self, program: Stmt) -> None:
        self.program = program
        self.cfg_builder = CFGBuilder()
        self.entry, self.exit = self.cfg_builder.build(program)

        # universe E: 구조적으로 고유한 BinOp 집합
        self.expr_varset: Dict[BinOp, Set[str]] = {}
        self.E: Set[BinOp] = set()
        self._collect_universe()

        # per-node GEN/KILL
        self.GEN: Dict[int, Set[BinOp]] = {}
        self.KILL: Dict[int, Set[BinOp]] = {}
        self._compute_gen_kill()

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

        raise TypeError(f"지원하지 않는 Stmt 타입: {type(stmt)}")

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

            raise ValueError(f"알 수 없는 node kind: {node.kind}")

    def analyze(self) -> Dict[str, object]:
        nodes = sorted(self.cfg_builder.nodes.keys())

        # preds 계산 (forward analysis이기 때문에 preds 기반으로 계산)
        preds: Dict[int, Set[int]] = {nid: set() for nid in nodes}
        for u, vs in self.cfg_builder.succ.items():
            for v in vs:
                preds[v].add(u)

        # 초기값
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

    def print_result(self, result: Dict[str, object]) -> None:
        print("Universe E =", format_set(result["E"]))
        print("entry =", result["entry"], "exit =", result["exit"])
        for nid in sorted(result["IN"].keys()):
            inn = result["IN"][nid]
            out = result["OUT"][nid]
            node_kind = self.cfg_builder.nodes[nid].kind
            print(f"Node {nid} ({node_kind}): IN={format_set(inn)} OUT={format_set(out)}")


def format_set(s: Set[BinOp]) -> str:
    if not s:
        return "{}"
    return "{" + ", ".join(sorted(expr.to_key() for expr in s)) + "}"

