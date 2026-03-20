## WHILE 문법 (간단 EBNF)

아래 문법은 이 프로젝트에서 사용할 WHILE 구문입니다.

프로그램
```
prog   ::= stmt EOF
```

문장
```
stmt   ::= nonseq ( ";" nonseq )*
nonseq ::= "skip"
         | IDENT ":=" aexpr
         | "if" bexpr "then" stmt "else" stmt
         | "while" bexpr "do" stmt
```

산술식
```
aexpr  ::= term ( ("+"|"-") term )*
term   ::= factor ( ("*"|"/") factor )*
factor ::= NUMBER | IDENT | "(" aexpr ")"
```

부울식
```
bexpr  ::= orexpr
orexpr ::= andexpr ( "or" andexpr )*
andexpr::= notexpr ( "and" notexpr )*
notexpr::= "not" notexpr | atom
atom   ::= "true" | "false"
         | "(" bexpr ")"
         | aexpr ( "=" | "!=" | "<" | "<=" | ">" | ">=" ) aexpr
```

