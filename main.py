import argparse
from static_analysis.available_expressions_analysis import AvailableExpressionsAnalyzer
from static_analysis.live_variables_analysis import LiveVariablesAnalyzer
from static_analysis.reaching_definition_analysis import ReachingDefinitionsAnalyzer
from static_analysis.very_busy_expressions_analysis import VeryBusyExpressionsAnalyzer
from static_analysis.syntax.parser import WhileParser

PROGRAM_SRC = """
x := 1;
y := 2;
while x < 5 do
    a := d + 3;
    b := z + x;
    x := x + 1;
    y := y + x
"""

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=str, required=True, choices=["aea", "rda", "vbea", "lva"])
    return parser.parse_args()

def main():
    args = parse_args()
    ast = WhileParser(PROGRAM_SRC).parse()

    if args.analysis == "aea":
        analyzer = AvailableExpressionsAnalyzer(ast)
    elif args.analysis == "rda":
        analyzer = ReachingDefinitionsAnalyzer(ast)
    elif args.analysis == "vbea":
        analyzer = VeryBusyExpressionsAnalyzer(ast)
    elif args.analysis == "lva":
        analyzer = LiveVariablesAnalyzer(ast)
    else:
        raise ValueError(f"Unknown analysis: {args.analysis}")

    result = analyzer.analyze()
    analyzer.print_result(result)

if __name__ == "__main__":
    main()