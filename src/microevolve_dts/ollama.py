from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Sequence

from .evolve import Candidate
from .program import FEATURE_NAMES, Expr


class OllamaProposalError(RuntimeError):
    pass


def _first_json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise OllamaProposalError("model response did not contain a JSON object")


def extract_expr_from_text(text: str, *, max_depth: int) -> Expr:
    try:
        raw = _first_json_object(text)
        expr = Expr.from_dict(raw)
    except (ValueError, TypeError, OllamaProposalError) as exc:
        if isinstance(exc, OllamaProposalError):
            raise
        raise OllamaProposalError(f"invalid heuristic expression: {exc}") from exc
    if expr.depth > max_depth:
        raise OllamaProposalError(
            f"heuristic expression depth {expr.depth} exceeds limit {max_depth}"
        )
    return expr


def _leaderboard_summary(elites: Sequence[Candidate]) -> str:
    payload = []
    for candidate in elites[:5]:
        payload.append(
            {
                "fitness": candidate.fitness,
                "program": candidate.program.to_dict(),
                "metrics": [metric.to_dict() for metric in candidate.metrics],
            }
        )
    return json.dumps(payload, sort_keys=True)


def build_prompt(elites: Sequence[Candidate], *, max_depth: int) -> str:
    features = ", ".join(sorted(FEATURE_NAMES))
    return f"""You are proposing one search-ranking heuristic for a Difference Triangle Set beam search.
Return exactly one JSON expression object and nothing else.

Allowed terminal forms:
{{"const": NUMBER}}
{{"feature": NAME}}

Allowed operations:
{{"op":"neg","args":[EXPR]}}
{{"op":"abs","args":[EXPR]}}
{{"op":"add","args":[EXPR,EXPR]}}
{{"op":"sub","args":[EXPR,EXPR]}}
{{"op":"mul","args":[EXPR,EXPR]}}
{{"op":"min","args":[EXPR,EXPR]}}
{{"op":"max","args":[EXPR,EXPR]}}

Allowed features: {features}
Maximum expression depth: {max_depth}
Higher expression values are ranked earlier by the beam search.
Try a structurally different idea from the current leaders, not merely tiny constant changes.

Current leaders:
{_leaderboard_summary(elites)}
"""


def propose_program(
    model: str,
    elites: Sequence[Candidate],
    *,
    max_depth: int,
    base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: float = 90.0,
) -> Expr:
    payload = json.dumps(
        {
            "model": model,
            "prompt": build_prompt(elites, max_depth=max_depth),
            "stream": False,
            "options": {"temperature": 0.8},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OllamaProposalError(f"Ollama request failed: {exc}") from exc

    text = body.get("response") if isinstance(body, dict) else None
    if not isinstance(text, str):
        raise OllamaProposalError("Ollama response did not contain a text response")
    return extract_expr_from_text(text, max_depth=max_depth)


@dataclass(frozen=True, slots=True)
class OllamaProposer:
    model: str
    max_depth: int
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 90.0

    def __call__(self, elites: Sequence[Candidate], _rng) -> Expr | None:
        try:
            return propose_program(
                self.model,
                elites,
                max_depth=self.max_depth,
                base_url=self.base_url,
                timeout_seconds=self.timeout_seconds,
            )
        except OllamaProposalError:
            return None
