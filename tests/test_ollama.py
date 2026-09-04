import pytest

from microevolve_dts.ollama import OllamaProposalError, extract_expr_from_text


def test_extracts_expression_from_fenced_json():
    text = '''Here is a candidate:\n```json\n{"op":"add","args":[{"feature":"prefix_fill"},{"const":0.5}]}\n```'''
    expr = extract_expr_from_text(text, max_depth=4)
    assert expr.evaluate({"prefix_fill": 0.25}) == pytest.approx(0.75)


def test_extracts_expression_from_plain_text_with_surrounding_words():
    text = 'candidate = {"feature":"lower_fill"} because it rewards coverage'
    expr = extract_expr_from_text(text, max_depth=3)
    assert expr.features_used() == ("lower_fill",)


def test_rejects_invalid_or_unsupported_dsl():
    with pytest.raises(OllamaProposalError):
        extract_expr_from_text('{"feature":"not_allowed"}', max_depth=3)
    with pytest.raises(OllamaProposalError):
        extract_expr_from_text('{"op":"divide","args":[{"const":1},{"const":2}]}', max_depth=3)
