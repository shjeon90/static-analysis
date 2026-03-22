from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from static_analysis.syntax.ast import (
    Assign,
    BoolExpr,
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

    def _new_node(
        self,
        kind: str,
        assign: Optional[Assign] = None,
        cond: Optional[BoolExpr] = None,
    ) -> int:
        nid = self._next_id
        self._next_id += 1
        node = CFGNode(id=nid, kind=kind, assign=assign, cond=cond)
        self.nodes[nid] = node
        self.succ[nid] = []
        return nid

    def _add_edge(self, u: int, v: int) -> None:
        self.succ[u].append(v)

    def build(self, stmt: Stmt) -> Tuple[int, int]:  # entry, exit
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

        raise TypeError(f"Unsupported Stmt type: {type(stmt)}")

