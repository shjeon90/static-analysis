## 정적 분석 연습(WHILE 언어)

이 저장소는 `WHILE` 언어를 대상으로 여러 가지 **정적 분석(static analysis)** 알고리즘을 구현해보는 연습용 프로젝트입니다. 현재는 아래 분석이 구현되어 있습니다.

- Available Expressions Analysis (`aea`)
- Reaching Definitions Analysis (`rda`)

## 지원 언어(WHILE)

구현된 파서는 다음 문장/표현식을 지원합니다.

- 문장: `skip`, 대입 `x := <arith>`, 시퀀스(세미콜론), 조건 `if <bool> then <stmt> else <stmt>`, 반복 `while <bool> do <stmt>`
- 불리언: `true/false`, `not`, `and`, `or`, 비교 `(<, <=, >, >=, =, !=)` (양변은 산술식)
- 산술식: 변수/상수, `+ - * /`, 괄호

파서는 `syntax/parser.py`의 `WhileParser`를 사용합니다.

## 현재 구현 1: Available Expressions Analysis (Must, Forward)

`available_expressions_analysis/aea.py`에서 다음과 같은 **전방향(must) 가용 표현식 분석**을 수행합니다.

- `E`: 프로그램 전체에서 등장하는 후보 산술 표현식 집합(분석 유니버스)
  - 후보는 AST 내부의 `BinOp`(중첩 포함)로 정의됩니다.
- `IN[n]`: 노드 `n`에 도달하기 직전에, 모든 경로에서 가용한 표현식 집합
- `OUT[n]`: 노드 `n`의 전이(gen/kill)를 반영한 결과

CFG는 `CFGBuilder`가 생성하며, 노드 종류는 대략 아래와 같습니다.

- `assign`: 대입문 노드
- `cond`: 조건( `if`/`while` ) 노드
- `skip`: join/after 등 보조 노드

분석 결과는 각 노드의 `IN/OUT` 및 분석 유니버스 `E`, entry/exit 노드 id를 함께 반환합니다.

## 현재 구현 2: Reaching Definitions Analysis (May, Forward)

`reaching_definition_analysis/rda.py`에서 다음과 같은 **전방향(may) 도달 정의 분석**을 수행합니다.

- `D`: 프로그램 내 정의(definition)의 유니버스
  - 정의는 `(변수명, assign CFG 노드 id)` 쌍으로 표현합니다. (예: `x@3`)
- `IN[n]`: 노드 `n` 직전에 도달 가능한 정의 집합(경로 합집합)
- `OUT[n]`: 노드 `n`의 전이(gen/kill) 반영 결과

전이 함수는 다음 직관을 따릅니다.

- `GEN[n]`: `assign` 노드인 경우 현재 노드의 새 정의 1개
- `KILL[n]`: 같은 변수를 정의하던 기존 정의들(현재 정의 제외)
- `OUT[n] = GEN[n] ∪ (IN[n] - KILL[n])`

분석 결과는 각 노드의 `IN/OUT` 및 분석 유니버스 `D`, entry/exit 노드 id를 함께 반환합니다.

## 실행 방법

간단히는 다음처럼 실행할 수 있습니다.

```bash
python main.py
```

현재 `main.py`에는 예제 프로그램(문자열)이 하드코딩되어 있으며, 해당 프로그램을 파싱한 뒤 분석기를 실행합니다.

현재 기본 예시는 `ReachingDefinitionsAnalyzer`를 실행하도록 되어 있습니다.

## 프로젝트 구조(개요)

- `syntax/`
  - `ast.py`: `WHILE` 언어 AST 노드 정의
  - `parser.py`: `WhileParser` 구현
  - (토크나이저 등 세부 구현이 있을 수 있음)
- `cfg.py`
  - 공통 CFG 노드/엣지 구성기(`CFGBuilder`)
- `available_expressions_analysis/`
  - `aea.py`: Available Expressions Analysis 구현
  - `__init__.py`: 외부에서 `AvailableExpressionsAnalyzer`로 import 가능
- `reaching_definition_analysis/`
  - `rda.py`: Reaching Definitions Analysis 구현
  - `__init__.py`: 외부에서 `ReachingDefinitionsAnalyzer`로 import 가능
- `__init__.py`
  - `static_analysis` 패키지 루트
- `main.py`
  - 현재 분석을 데모로 실행하는 엔트리 포인트 (기본: RDA)

## 다음에 추가할 것(로드맵)

원하는 순서대로 정적 분석들을 확장할 예정입니다. 예를 들면:

- Live Variables(생존 변수)
- Constant Propagation / Folding(상수 전파)
- Common Subexpression Elimination(CSE)과의 연결(가능 시)
- 분석별 공통 인프라(워크리스트, 데이터플로우 프레임워크) 정리

관심 있는 분석이 있으면 말해주면, 그 분석을 먼저 구현해나가는 방식으로 진행하겠습니다.
