def main():
    from available_expressions_analysis import AvailableExpressionsAnalyzer
    from available_expressions_analysis.aea import format_set
    from syntax.parser import WhileParser

    program_src = """
    x := 1;
    y := 2;
    while x < 5 do
      x := x + 1;
      y := y + x
    """

    ast = WhileParser(program_src).parse()
    analyzer = AvailableExpressionsAnalyzer(ast)
    result = analyzer.analyze()

    print("Universe E =", format_set(result["E"]))
    print("entry =", result["entry"], "exit =", result["exit"])

    for nid in sorted(result["IN"].keys()):
        inn = result["IN"][nid]
        out = result["OUT"][nid]
        node_kind = analyzer.cfg_builder.nodes[nid].kind
        print(f"Node {nid} ({node_kind}): IN={format_set(inn)} OUT={format_set(out)}")

if __name__ == "__main__":
    main()