from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Set


class ArithExpr:
    def vars(self) -> FrozenSet[str]:
        raise NotImplementedError

    def candidates(self) -> Iterable["BinOp"]:
        """표현식 내부의 '후보 가능 표현식'들(BinOp 노드들)을 순회."""
        raise NotImplementedError

    def to_key(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Var(ArithExpr):
    name: str

    def vars(self) -> FrozenSet[str]:
        return frozenset([self.name])

    def candidates(self) -> Iterable["BinOp"]:
        return []

    def to_key(self) -> str:
        return self.name


@dataclass(frozen=True)
class Const(ArithExpr):
    value: int

    def vars(self) -> FrozenSet[str]:
        return frozenset()

    def candidates(self) -> Iterable["BinOp"]:
        return []

    def to_key(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BinOp(ArithExpr):
    op: str  # + - * /
    left: ArithExpr
    right: ArithExpr

    def vars(self) -> FrozenSet[str]:
        return frozenset(set(self.left.vars()) | set(self.right.vars()))

    def candidates(self) -> Iterable["BinOp"]:
        # 이 노드(BinOp) 자체와, 자식 BinOp들도 포함
        yield self
        yield from self.left.candidates()
        yield from self.right.candidates()

    def to_key(self) -> str:
        return f"({self.left.to_key()}{self.op}{self.right.to_key()})"


class BoolExpr:
    def candidates(self) -> Iterable[BinOp]:
        raise NotImplementedError


@dataclass(frozen=True)
class BoolConst(BoolExpr):
    value: bool

    def candidates(self) -> Iterable[BinOp]:
        return []


@dataclass(frozen=True)
class Compare(BoolExpr):
    op: str  # = != < <= > >=
    left: ArithExpr
    right: ArithExpr

    def candidates(self) -> Iterable[BinOp]:
        return list(self.left.candidates()) + list(self.right.candidates())


@dataclass(frozen=True)
class BoolAnd(BoolExpr):
    left: BoolExpr
    right: BoolExpr

    def candidates(self) -> Iterable[BinOp]:
        return list(self.left.candidates()) + list(self.right.candidates())


@dataclass(frozen=True)
class BoolOr(BoolExpr):
    left: BoolExpr
    right: BoolExpr

    def candidates(self) -> Iterable[BinOp]:
        return list(self.left.candidates()) + list(self.right.candidates())


@dataclass(frozen=True)
class BoolNot(BoolExpr):
    expr: BoolExpr

    def candidates(self) -> Iterable[BinOp]:
        return list(self.expr.candidates())


class Stmt:
    pass


@dataclass(frozen=True)
class Skip(Stmt):
    pass


@dataclass(frozen=True)
class Assign(Stmt):
    name: str
    expr: ArithExpr


@dataclass(frozen=True)
class Seq(Stmt):
    first: Stmt
    second: Stmt


@dataclass(frozen=True)
class If(Stmt):
    cond: BoolExpr
    then_branch: Stmt
    else_branch: Stmt


@dataclass(frozen=True)
class While(Stmt):
    cond: BoolExpr
    body: Stmt

