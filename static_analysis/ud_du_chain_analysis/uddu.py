from __future__ import annotations

from typing import Dict, Set, Tuple

from static_analysis.reaching_definition_analysis.rda import (
    Definition,
    ReachingDefinitionsAnalyzer,
)
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

UDKey = Tuple[str, int]  # (variable x, use-label ℓ)
DUKey = Tuple[str, int]  # (variable x, def-label ℓ)


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


class UDDUChainAnalyzer:
    """
    Use-Definition (UD) and Definition-Use (DU) chain analysis.

    Derived from Reaching Definitions Analysis (RDA).

    UD(x, ℓ)  =  { ℓ' | (x, ℓ') ∈ RD_entry(ℓ) }
        for each use of x at block [B]^ℓ  (x ∈ FV(B))

    DU(x, ℓ)  =  { ℓ'' | x ∈ uses([B'']^ℓ'') and (x, ℓ) ∈ RD_entry(ℓ'') }
        for each definition of x at block [x := a]^ℓ
    """

    def __init__(self, program: Stmt) -> None:
        self.program = program
        self._rda = ReachingDefinitionsAnalyzer(program)

    def analyze(self) -> Dict[str, object]:
        rda_result = self._rda.analyze()
        rd_entry: Dict[int, Set[Definition]] = rda_result["IN"]  # type: ignore[assignment]

        nodes = self._rda.cfg_builder.nodes

        # Collect which variables are READ (used) at each node
        uses: Dict[int, Set[str]] = {}
        for nid, node in nodes.items():
            if node.kind == "assign":
                assert node.assign is not None
                uses[nid] = _vars_in_arith(node.assign.expr)
            elif node.kind == "cond":
                assert node.cond is not None
                uses[nid] = _vars_in_bool(node.cond)
            else:
                uses[nid] = set()

        # UD chains: for each (x, ℓ) where x is used at ℓ
        # UD(x, ℓ) = { ℓ' | (x, ℓ') ∈ RD_entry(ℓ) }
        ud: Dict[UDKey, Set[int]] = {}
        for nid in nodes:
            for x in uses[nid]:
                reaching_labels = {d.node_id for d in rd_entry[nid] if d.var == x}
                ud[(x, nid)] = reaching_labels

        # DU chains: for each (x, ℓ) where x is defined at ℓ
        # DU(x, ℓ) = { ℓ'' | x ∈ uses([B'']^ℓ'') and (x, ℓ) ∈ RD_entry(ℓ'') }
        du: Dict[DUKey, Set[int]] = {}
        for nid, node in nodes.items():
            if node.kind != "assign":
                continue
            assert node.assign is not None
            x = node.assign.name
            du_set: Set[int] = set()
            for nid2 in nodes:
                if x in uses[nid2]:
                    if any(d.var == x and d.node_id == nid for d in rd_entry[nid2]):
                        du_set.add(nid2)
            du[(x, nid)] = du_set

        return {
            "UD": ud,
            "DU": du,
            "entry": rda_result["entry"],
            "exit": rda_result["exit"],
        }

    def print_result(self, result: Dict[str, object]) -> None:
        ud: Dict[UDKey, Set[int]] = result["UD"]  # type: ignore[assignment]
        du: Dict[DUKey, Set[int]] = result["DU"]  # type: ignore[assignment]

        print("=== Use-Definition Chains ===")
        if not ud:
            print("  (none)")
        else:
            for (x, label), def_labels in sorted(ud.items()):
                labels_str = "{" + ", ".join(str(l) for l in sorted(def_labels)) + "}"
                print(f"  UD({x}, {label}) = {labels_str}")

        print()
        print("=== Definition-Use Chains ===")
        if not du:
            print("  (none)")
        else:
            for (x, label), use_labels in sorted(du.items()):
                labels_str = "{" + ", ".join(str(l) for l in sorted(use_labels)) + "}"
                print(f"  DU({x}, {label}) = {labels_str}")
