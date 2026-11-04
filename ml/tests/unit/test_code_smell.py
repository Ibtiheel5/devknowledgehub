from dkh_ml.models.code_smell import detect_smells, iter_functions


def _long_function(body_lines: int = 45) -> str:
    body = "\n".join(f"    value_{i} = {i}" for i in range(body_lines))
    return f"def long_function(a, b, c, d, e, f):\n{body}\n    return value_0\n"


def test_detects_long_method_and_parameter_list():
    smells = detect_smells(_long_function())
    names = {smell["smell"] for smell in smells}
    assert "long_method" in names
    assert "long_parameter_list" in names


def test_detects_deep_nesting():
    source = (
        "def nested(value):\n"
        "    if value:\n"
        "        if value > 1:\n"
        "            if value > 2:\n"
        "                if value > 3:\n"
        "                    if value > 4:\n"
        "                        return value\n"
        "    return 0\n"
    )
    smells = detect_smells(source)
    assert any(smell["smell"] == "deep_nesting" for smell in smells)


def test_clean_function_has_no_smell():
    assert detect_smells("def add(a, b):\n    return a + b\n") == []


def test_brace_language_function_is_parsed():
    body = "\n".join(f"        int value{i} = {i};" for i in range(45))
    source = f"public class Sample {{\n    public void run(int a) {{\n{body}\n    }}\n}}\n"
    functions = iter_functions(source, "java")
    assert functions
    assert functions[0]["name"] == "run"
    assert any(smell["smell"] == "long_method" for smell in detect_smells(source, "java"))
