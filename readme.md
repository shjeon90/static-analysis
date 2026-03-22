## Static Analysis on the WHILE Language

This repository implements several **dataflow analysis** algorithms for the `WHILE` language, following the formal framework of:

> Nielson, Nielson & Hankin, *Principles of Program Analysis*, Springer, 2nd ed.

- Available Expressions Analysis (`aea`)
- Reaching Definitions Analysis (`rda`)
- Very Busy Expressions Analysis (`vbea`)
- Live Variables Analysis (`lva`)
- Use-Definition / Definition-Use Chain Analysis (`uddu`)

---

## WHILE Language

The supported syntax is defined in `while_grammar.md`. The grammar covers statements $S$, arithmetic expressions $a \in \mathbf{AExp}$, and boolean expressions $b \in \mathbf{BExp}$.

Each **elementary block** is a maximal syntactic unit that executes atomically and carries a unique **label** $\ell \in \mathbf{Lab}$. For a program $S_\star$:

| Notation | Meaning |
|---|---|
| $\mathbf{Lab}_\star$ | set of all labels occurring in $S_\star$ |
| $\mathbf{Var}_\star$ | set of all variables occurring in $S_\star$ |
| $\mathit{init}(S_\star)$ | label of the first block executed |
| $\mathit{final}(S_\star)$ | set of labels of blocks that may execute last |
| $\mathit{flow}(S_\star)$ | set of edges $(\ell, \ell') \in \mathbf{Lab}_\star \times \mathbf{Lab}_\star$ (control flow) |
| $\mathit{flow}^R(S_\star)$ | reverse flow: $\{(\ell', \ell) \mid (\ell, \ell') \in \mathit{flow}(S_\star)\}$ |
| $[B]^\ell$ | the elementary block with label $\ell$ and body $B$ |

The parser is implemented in `syntax/parser.py` as `WhileParser`.

---

## Analysis 1: Available Expressions Analysis (Forward, Must)

**File:** `available_expressions_analysis/aea.py`

An expression $a$ is **available** at a program point if every path from $\mathit{init}(S_\star)$ to that point evaluates $a$ and does not subsequently modify any variable in $\mathit{FV}(a)$.

### Universe

$$\mathbf{AExp}_\star \;=\; \{ a \in \mathbf{AExp} \mid a \text{ is a non-trivial sub-expression (BinOp) occurring in } S_\star \}$$

### gen and kill

For each labeled block $[B]^\ell$:

$$\mathit{gen}_{AE}([B]^\ell) = \begin{cases} \mathbf{AExp}(a) & \text{if } B \equiv x := a \\ \mathbf{AExp}(b) & \text{if } B \equiv b \text{ (cond)} \\ \emptyset & \text{if } B \equiv \mathbf{skip} \end{cases}$$

$$\mathit{kill}_{AE}([B]^\ell) = \begin{cases} \{ a' \in \mathbf{AExp}_\star \mid x \in \mathit{FV}(a') \} & \text{if } B \equiv x := a \\ \emptyset & \text{otherwise} \end{cases}$$

where $\mathbf{AExp}(e)$ denotes the set of non-trivial arithmetic sub-expressions of $e$, and $\mathit{FV}(a')$ is the set of free variables of $a'$.

### Dataflow Equations

$$AE_{\mathit{entry}}(\ell) = \begin{cases} \emptyset & \text{if } \ell = \mathit{init}(S_\star) \\ \displaystyle\bigcap_{\,(\ell',\,\ell)\,\in\,\mathit{flow}(S_\star)} AE_{\mathit{exit}}(\ell') & \text{otherwise} \end{cases}$$

$$AE_{\mathit{exit}}(\ell) \;=\; \bigl(AE_{\mathit{entry}}(\ell) \setminus \mathit{kill}_{AE}([B]^\ell)\bigr) \;\cup\; \mathit{gen}_{AE}([B]^\ell)$$

The **maximum** fixed point (MFP) is computed by initialising $AE_{\mathit{entry}}(\ell) = \mathbf{AExp}_\star$ for all $\ell \neq \mathit{init}(S_\star)$ and iterating until convergence.

---

## Analysis 2: Reaching Definitions Analysis (Forward, May)

**File:** `reaching_definition_analysis/rda.py`

A definition $(x, \ell)$ **reaches** a program point if there exists a path from the block $[x := a]^\ell$ to that point along which $x$ is not redefined. The token $(x, ?)$ denotes the possibility that $x$ was defined before the program started.

### Universe

$$\mathbf{RD}_\star \;=\; \bigl(\mathbf{Var}_\star \times (\mathbf{Lab}_\star \cup \{?\})\bigr)$$

### gen and kill

For each labeled block $[B]^\ell$:

$$\mathit{gen}_{RD}([B]^\ell) = \begin{cases} \{(x, \ell)\} & \text{if } B \equiv x := a \\ \emptyset & \text{otherwise} \end{cases}$$

$$\mathit{kill}_{RD}([B]^\ell) = \begin{cases} \{(x, \ell') \mid \ell' \in \mathbf{Lab}_\star \cup \{?\}\} & \text{if } B \equiv x := a \\ \emptyset & \text{otherwise} \end{cases}$$

### Dataflow Equations

$$RD_{\mathit{entry}}(\ell) = \begin{cases} \{(x, ?) \mid x \in \mathbf{Var}_\star\} & \text{if } \ell = \mathit{init}(S_\star) \\ \displaystyle\bigcup_{\,(\ell',\,\ell)\,\in\,\mathit{flow}(S_\star)} RD_{\mathit{exit}}(\ell') & \text{otherwise} \end{cases}$$

$$RD_{\mathit{exit}}(\ell) \;=\; \bigl(RD_{\mathit{entry}}(\ell) \setminus \mathit{kill}_{RD}([B]^\ell)\bigr) \;\cup\; \mathit{gen}_{RD}([B]^\ell)$$

> **Implementation note:** The implementation initialises $RD_{\mathit{entry}}(\mathit{init}(S_\star)) = \emptyset$ (omitting the $(x,?)$ tokens) as a simplification.

The **minimum** fixed point (MFP) is computed by initialising $RD_{\mathit{entry}}(\ell) = \emptyset$ for all nodes and iterating until convergence.

---

## Analysis 3: Very Busy Expressions Analysis (Backward, Must)

**File:** `very_busy_expressions_analysis/vbea.py`

An expression $a$ is **very busy** at a program point if on every path from that point to the end of the program, $a$ is evaluated before any variable in $\mathit{FV}(a)$ is modified.

### Universe

$$\mathbf{AExp}_\star \;=\; \{ a \in \mathbf{AExp} \mid a \text{ is a non-trivial sub-expression (BinOp) occurring in } S_\star \}$$

### gen and kill

For each labeled block $[B]^\ell$:

$$\mathit{gen}_{VB}([B]^\ell) = \begin{cases} \mathbf{AExp}(a) & \text{if } B \equiv x := a \\ \mathbf{AExp}(b) & \text{if } B \equiv b \text{ (cond)} \\ \emptyset & \text{if } B \equiv \mathbf{skip} \end{cases}$$

$$\mathit{kill}_{VB}([B]^\ell) = \begin{cases} \{ a' \in \mathbf{AExp}_\star \mid x \in \mathit{FV}(a') \} & \text{if } B \equiv x := a \\ \emptyset & \text{otherwise} \end{cases}$$

### Dataflow Equations

$$VB_{\mathit{exit}}(\ell) = \begin{cases} \emptyset & \text{if } \ell \in \mathit{final}(S_\star) \\ \displaystyle\bigcap_{\,(\ell,\,\ell')\,\in\,\mathit{flow}(S_\star)} VB_{\mathit{entry}}(\ell') & \text{otherwise} \end{cases}$$

$$VB_{\mathit{entry}}(\ell) \;=\; \bigl(VB_{\mathit{exit}}(\ell) \setminus \mathit{kill}_{VB}([B]^\ell)\bigr) \;\cup\; \mathit{gen}_{VB}([B]^\ell)$$

The **maximum** fixed point (MFP) is computed by initialising $VB_{\mathit{exit}}(\ell) = \mathbf{AExp}_\star$ for all $\ell \notin \mathit{final}(S_\star)$ and iterating until convergence.

---

## Analysis 4: Live Variables Analysis (Backward, May)

**File:** `live_variables_analysis/lva.py`

A variable $x$ is **live** at a program point if there exists a path from that point to a use of $x$ along which $x$ is not redefined.

### Universe

$$\mathbf{Var}_\star \;=\; \{ x \mid x \text{ is a variable occurring in } S_\star \}$$

### gen and kill

For each labeled block $[B]^\ell$:

$$\mathit{gen}_{LV}([B]^\ell) = \begin{cases} \mathit{FV}(a) & \text{if } B \equiv x := a \\ \mathit{FV}(b) & \text{if } B \equiv b \text{ (cond)} \\ \emptyset & \text{if } B \equiv \mathbf{skip} \end{cases}$$

$$\mathit{kill}_{LV}([B]^\ell) = \begin{cases} \{x\} & \text{if } B \equiv x := a \\ \emptyset & \text{otherwise} \end{cases}$$

where $\mathit{FV}(e)$ denotes the set of all variables (free variables) occurring in $e$.

### Dataflow Equations

$$LV_{\mathit{exit}}(\ell) = \begin{cases} \emptyset & \text{if } \ell \in \mathit{final}(S_\star) \\ \displaystyle\bigcup_{\,(\ell,\,\ell')\,\in\,\mathit{flow}(S_\star)} LV_{\mathit{entry}}(\ell') & \text{otherwise} \end{cases}$$

$$LV_{\mathit{entry}}(\ell) \;=\; \mathit{gen}_{LV}([B]^\ell) \;\cup\; \bigl(LV_{\mathit{exit}}(\ell) \setminus \mathit{kill}_{LV}([B]^\ell)\bigr)$$

The **minimum** fixed point (MFP) is computed by initialising $LV_{\mathit{exit}}(\ell) = \emptyset$ for all nodes and iterating until convergence.

---
## Usage

```bash
python main.py --analysis aea
python main.py --analysis rda
python main.py --analysis vbea
python main.py --analysis lva
python main.py --analysis uddu
```

`main.py` contains a hard-coded example program. The `--analysis` flag selects the analysis to run.

---

## Analysis 5: Use-Definition and Definition-Use Chains (Derived from RDA)

**File:** `ud_du_chain_analysis/uddu.py`

UD and DU chains are **derived analyses** built on top of Reaching Definitions Analysis. They do not have their own gen/kill functions or fixpoint equations; instead they are computed directly from $RD_{\mathit{entry}}$.

### Auxiliary definition: uses

$$\mathit{uses}([B]^\ell) = \begin{cases} \mathit{FV}(a) & \text{if } B \equiv x := a \\ \mathit{FV}(b) & \text{if } B \equiv b \text{ (cond)} \\ \emptyset & \text{if } B \equiv \mathbf{skip} \end{cases}$$

### Use-Definition Chain

For each block $[B]^\ell$ and each variable $x \in \mathit{uses}([B]^\ell)$, the UD chain gives the set of definition labels that can reach this use:

$$\mathit{UD}(x, \ell) \;=\; \bigl\{\, \ell' \;\big|\; (x, \ell') \in RD_{\mathit{entry}}(\ell) \,\bigr\}$$

### Definition-Use Chain

For each assignment block $[x := a]^\ell$, the DU chain gives the set of use labels reachable from this definition:

$$\mathit{DU}(x, \ell) \;=\; \bigl\{\, \ell'' \;\big|\; x \in \mathit{uses}([B'']^{\ell''}) \;\text{ and }\; (x, \ell) \in RD_{\mathit{entry}}(\ell'') \,\bigr\}$$

---

## Roadmap

- Constant Propagation / Folding
- Common Subexpression Elimination
- Generic worklist-based dataflow framework
