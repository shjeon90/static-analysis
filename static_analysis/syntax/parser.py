from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Set

from static_analysis.syntax.ast import (
    ArithExpr,
    Assign,
    BinOp,
    BoolAnd,
    BoolConst,
    BoolExpr,
    BoolNot,
    BoolOr,
    Compare,
    Const,
    If,
    Skip,
    Seq,
    Stmt,
    Var,
    While,
)
from static_analysis.syntax.tokenizer import Token, tokenize


class WhileParser:
    def __init__(self, src: str):
        self.tokens = tokenize(src)
        self.i = 0

    def _peek(self) -> Token:
        return self.tokens[self.i]

    def _consume(self, kind: str) -> Token:
        tok = self._peek()
        if tok.kind != kind:
            raise SyntaxError(
                f"expected {kind}, got {tok.kind} (pos={tok.pos})"
            )
        self.i += 1
        return tok

    def _accept(self, kind: str) -> Optional[Token]:
        tok = self._peek()
        if tok.kind == kind:
            self.i += 1
            return tok
        return None

    def parse(self) -> Stmt:
        stmt = self._parse_stmt(stop_kinds={"EOF"})
        self._consume("EOF")
        return stmt

    def _parse_stmt(self, stop_kinds: Set[str]) -> Stmt:
        # Treat ';' sequences as lowest precedence
        if self._peek().kind in stop_kinds:
            raise SyntaxError(f"not a statement-start token: {self._peek()}")

        first = self._parse_non_seq_stmt(stop_kinds=stop_kinds)
        stmts = [first]

        while self._accept("SEMI") is not None:
            if self._peek().kind in stop_kinds:
                break
            stmts.append(self._parse_non_seq_stmt(stop_kinds=stop_kinds))

        # Left-associative Seq
        out: Stmt = stmts[0]
        for s in stmts[1:]:
            out = Seq(out, s)
        return out

    def _parse_non_seq_stmt(self, stop_kinds: Set[str]) -> Stmt:
        tok = self._peek()
        if tok.kind == "SKIP":
            self._consume("SKIP")
            return Skip()

        if tok.kind == "IF":
            return self._parse_if(stop_kinds=stop_kinds)

        if tok.kind == "WHILE":
            return self._parse_while(stop_kinds=stop_kinds)

        if tok.kind == "IDENT":
            # assignment: IDENT := a
            name = self._consume("IDENT").value
            self._consume("ASSIGN")
            expr = self._parse_arith_expr()
            return Assign(name=name, expr=expr)

        raise SyntaxError(f"unsupported stmt start token: {tok.kind} (pos={tok.pos})")

    def _parse_if(self, stop_kinds: Set[str]) -> Stmt:
        self._consume("IF")
        cond = self._parse_bool_expr()
        self._consume("THEN")
        then_branch = self._parse_stmt(stop_kinds={"ELSE"})
        self._consume("ELSE")
        else_branch = self._parse_stmt(stop_kinds=stop_kinds)
        return If(cond=cond, then_branch=then_branch, else_branch=else_branch)

    def _parse_while(self, stop_kinds: Set[str]) -> Stmt:
        self._consume("WHILE")
        cond = self._parse_bool_expr()
        self._consume("DO")
        body = self._parse_stmt(stop_kinds=stop_kinds)
        return While(cond=cond, body=body)

    def _parse_bool_expr(self) -> BoolExpr:
        return self._parse_or()

    def _parse_or(self) -> BoolExpr:
        left = self._parse_and()
        while self._accept("OR") is not None:
            right = self._parse_and()
            left = BoolOr(left=left, right=right)
        return left

    def _parse_and(self) -> BoolExpr:
        left = self._parse_not()
        while self._accept("AND") is not None:
            right = self._parse_not()
            left = BoolAnd(left=left, right=right)
        return left

    def _parse_not(self) -> BoolExpr:
        if self._accept("NOT") is not None:
            inner = self._parse_not()
            return BoolNot(expr=inner)
        return self._parse_bool_atom()

    def _parse_bool_atom(self) -> BoolExpr:
        if self._accept("LPAREN") is not None:
            b = self._parse_bool_expr()
            self._consume("RPAREN")
            return b

        tok = self._peek()
        if tok.kind == "TRUE":
            self._consume("TRUE")
            return BoolConst(value=True)
        if tok.kind == "FALSE":
            self._consume("FALSE")
            return BoolConst(value=False)

        # Comparison: a <op> a
        left = self._parse_arith_expr()

        op_tok = self._peek()
        if op_tok.kind in {"EQ", "NE", "LT", "LE", "GT", "GE"}:
            self.i += 1
        else:
            raise SyntaxError(f"comparison operator expected (pos={op_tok.pos})")

        # Normalize comparison operator token to string
        op_map = {
            "EQ": "=",
            "NE": "!=",
            "LT": "<",
            "LE": "<=",
            "GT": ">",
            "GE": ">=",
        }
        op = op_map[op_tok.kind]

        right = self._parse_arith_expr()
        return Compare(op=op, left=left, right=right)

    def _parse_arith_expr(self) -> ArithExpr:
        expr = self._parse_term()
        while True:
            if self._accept("PLUS") is not None:
                rhs = self._parse_term()
                expr = BinOp(op="+", left=expr, right=rhs)
                continue
            if self._accept("MINUS") is not None:
                rhs = self._parse_term()
                expr = BinOp(op="-", left=expr, right=rhs)
                continue
            break
        return expr

    def _parse_term(self) -> ArithExpr:
        term = self._parse_factor()
        while True:
            if self._accept("TIMES") is not None:
                rhs = self._parse_factor()
                term = BinOp(op="*", left=term, right=rhs)
                continue
            if self._accept("DIV") is not None:
                rhs = self._parse_factor()
                term = BinOp(op="/", left=term, right=rhs)
                continue
            break
        return term

    def _parse_factor(self) -> ArithExpr:
        tok = self._peek()
        if tok.kind == "NUMBER":
            val = int(self._consume("NUMBER").value)
            return Const(value=val)
        if tok.kind == "IDENT":
            name = self._consume("IDENT").value
            return Var(name=name)
        if self._accept("LPAREN") is not None:
            e = self._parse_arith_expr()
            self._consume("RPAREN")
            return e
        raise SyntaxError(f"arithmetic factor expected: {tok.kind} (pos={tok.pos})")

