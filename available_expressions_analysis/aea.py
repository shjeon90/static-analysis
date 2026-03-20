from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from syntax.ast import (
    ArithExpr,
    Assign,
    BinOp,
    BoolExpr,
    BoolConst,
    Compare,
    If,
    Skip,
    Seq,
    Stmt,
    While,
)


@dataclass(frozen=True)
class CFGNode:
    id: int
    kind: str  # 'skip' | 'assign' | 'cond'
    assign: Optional[Assign] = None
    cond: Optional[BoolExpr] = None


class CFGBuilder:
    def __init__(self) -> None:
        self._next_id = 0
        self.nodes: Dict[int, CFGNode] = {}
        self.succ: Dict[int, List[int]] = {}

    def _new_node(self, kind: str, assign: Optional[Assign] = None, cond: Optional[BoolExpr] = None) -> int:
        nid = self._next_id
        self._next_id += 1
        node = CFGNode(id=nid, kind=kind, assign=assign, cond=cond)
        self.nodes[nid] = node
        self.succ[nid] = []
        return nid

    def _add_edge(self, u: int, v: int) -> None:
        self.succ[u].append(v)

    def build(self, stmt: Stmt) -> Tuple[int, int]: # entry, exit
        if isinstance(stmt, Skip):
            n = self._new_node("skip")
            return n, n

        if isinstance(stmt, Assign):
            n = self._new_node("assign", assign=stmt)
            return n, n

        if isinstance(stmt, Seq):
            e1, x1 = self.build(stmt.first)
            e2, x2 = self.build(stmt.second)
            self._add_edge(x1, e2)
            return e1, x2

        if isinstance(stmt, If):
            cond_node = self._new_node("cond", cond=stmt.cond)
            then_entry, then_exit = self.build(stmt.then_branch)
            else_entry, else_exit = self.build(stmt.else_branch)
            join = self._new_node("skip")

            self._add_edge(cond_node, then_entry)
            self._add_edge(cond_node, else_entry)
            self._add_edge(then_exit, join)
            self._add_edge(else_exit, join)
            return cond_node, join

        if isinstance(stmt, While):
            cond_node = self._new_node("cond", cond=stmt.cond)
            body_entry, body_exit = self.build(stmt.body)
            after = self._new_node("skip")

            self._add_edge(cond_node, body_entry)  # true
            self._add_edge(cond_node, after)  # false
            self._add_edge(body_exit, cond_node)  # back edge
            return cond_node, after

        raise TypeError(f"지원하지 않는 Stmt 타입: {type(stmt)}")


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

        # universe E: 표현식 key -> vars 집합
        self.expr_varset: Dict[str, Set[str]] = {} # 표현식 key -> vars 집합
        self.E: Set[str] = set()    # 표현식 key 집합
        self._collect_universe()

        # per-node GEN/KILL
        self.GEN: Dict[int, Set[str]] = {}
        self.KILL: Dict[int, Set[str]] = {}
        self._compute_gen_kill()

    def _add_expr_candidate(self, binop: BinOp) -> None:
        key = binop.to_key()
        if key not in self.expr_varset:
            self.expr_varset[key] = set(binop.vars())
        self.E.add(key)

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

    def _candidates_in_arith(self, expr: ArithExpr) -> Set[str]:
        return {c.to_key() for c in expr.candidates()}

    def _candidates_in_bool(self, b: BoolExpr) -> Set[str]:
        return {c.to_key() for c in b.candidates()}

    def _compute_gen_kill(self) -> None:
        for nid, node in self.cfg_builder.nodes.items():
            if node.kind == "skip":
                self.GEN[nid] = set()
                self.KILL[nid] = set()
                continue

            if node.kind == "assign":
                assert node.assign is not None
                self.GEN[nid] = self._candidates_in_arith(node.assign.expr)
                kill: Set[str] = set()
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
        IN: Dict[int, Set[str]] = {}
        OUT: Dict[int, Set[str]] = {}

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


def format_set(s: Set[str]) -> str:
    if not s:
        return "{}"
    return "{" + ", ".join(sorted(s)) + "}"

