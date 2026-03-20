from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    pos: int

    def __repr__(self) -> str:  # 디버깅용
        return f"Token({self.kind!r}, {self.value!r}, pos={self.pos})"


KEYWORDS = {
    "skip": "SKIP",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "while": "WHILE",
    "do": "DO",
    "true": "TRUE",
    "false": "FALSE",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
}


def tokenize(src: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(src)

    def push(kind: str, value: str, pos: int) -> None:
        tokens.append(Token(kind=kind, value=value, pos=pos))

    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue

        # multi-char operators
        if src.startswith(":=", i):
            push("ASSIGN", ":=", i)
            i += 2
            continue
        if src.startswith("<=", i):
            push("LE", "<=", i)
            i += 2
            continue
        if src.startswith(">=", i):
            push("GE", ">=", i)
            i += 2
            continue
        if src.startswith("!=", i):
            push("NE", "!=", i)
            i += 2
            continue

        # single-char punctuation/operators
        if c == ";":
            push("SEMI", ";", i)
            i += 1
            continue
        if c == "(":
            push("LPAREN", "(", i)
            i += 1
            continue
        if c == ")":
            push("RPAREN", ")", i)
            i += 1
            continue
        if c == "+":
            push("PLUS", "+", i)
            i += 1
            continue
        if c == "-":
            push("MINUS", "-", i)
            i += 1
            continue
        if c == "*":
            push("TIMES", "*", i)
            i += 1
            continue
        if c == "/":
            push("DIV", "/", i)
            i += 1
            continue
        if c == "<":
            push("LT", "<", i)
            i += 1
            continue
        if c == ">":
            push("GT", ">", i)
            i += 1
            continue
        if c == "=":
            push("EQ", "=", i)
            i += 1
            continue

        # number
        if c.isdigit():
            j = i + 1
            while j < n and src[j].isdigit():
                j += 1
            push("NUMBER", src[i:j], i)
            i = j
            continue

        # identifier/keyword
        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            kind = KEYWORDS.get(word, "IDENT")
            push(kind, word, i)
            i = j
            continue

        raise SyntaxError(f"알 수 없는 문자 {c!r} (pos={i})")

    tokens.append(Token(kind="EOF", value="", pos=n))
    return tokens

