"""One-line summaries for the digest.

The preamble below is sent with *every* incident, so its length is multiplied
by the size of the batch. A nightly digest over a busy week is a few thousand
calls; anything added here is paid on all of them.
"""

from __future__ import annotations

PREAMBLE = """\
Summarise the incident in one sentence for an on-call engineer.
State what broke and who noticed. Do not speculate about the cause.
Do not repeat the severity or the category; the digest prints those already.
"""


def build_prompt(title: str, body: str) -> str:
    return f"{PREAMBLE}\nTitle: {title}\n\n{body.strip()}\n"


def summarise(title: str, body: str, *, call) -> str:
    """`call` takes a prompt and returns text. Injected so the digest can be
    rendered in tests and offline without a model."""
    return call(build_prompt(title, body)).strip().splitlines()[0]
