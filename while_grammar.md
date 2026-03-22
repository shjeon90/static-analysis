## WHILE grammar (simple EBNF)

The grammar below is the WHILE syntax used in this project.

Program
```
prog   ::= stmt EOF
```

Statements
```
stmt   ::= nonseq ( ";" nonseq )*
nonseq ::= "skip"
         | IDENT ":=" aexpr
         | "if" bexpr "then" stmt "else" stmt
         | "while" bexpr "do" stmt
```

Arithmetic expressions
```
aexpr  ::= term ( ("+"|"-") term )*
term   ::= factor ( ("*"|"/") factor )*
factor ::= NUMBER | IDENT | "(" aexpr ")"
```

Boolean expressions
```
bexpr  ::= orexpr
orexpr ::= andexpr ( "or" andexpr )*
andexpr::= notexpr ( "and" notexpr )*
notexpr::= "not" notexpr | atom
atom   ::= "true" | "false"
         | "(" bexpr ")"
         | aexpr ( "=" | "!=" | "<" | "<=" | ">" | ">=" ) aexpr
```
