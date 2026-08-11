"""The model call, behind one function.

One place decides which model runs and in which region, so that changing
either is a single edit and reading the cost of a request means reading one
file. Everything else takes `call` as an argument, which is what lets the
digest be rendered in tests and offline without credentials.
"""

from __future__ import annotations

import os

# Bedrock, on-demand. Region and model are read from the environment with a
# default here rather than scattered across call sites: a model id in three
# places is three things to update and two of them will be missed.
AWS_REGION = os.environ.get("AWS_REGION", "ca-central-1")
MODEL_ID = os.environ.get("DIGEST_MODEL", "mistral.mistral-7b-instruct-v0:2")

# Summaries are one sentence. Asking for more than that costs output tokens on
# every incident and gets truncated by the renderer anyway.
MAX_TOKENS = 120


def call(prompt: str) -> str:
    """Send one prompt, return the text. Raises if there are no credentials --
    the caller decides whether to degrade, because a summariser that silently
    returns nothing produces a digest that looks complete and says nothing."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
    )
    return response["output"]["message"]["content"][0]["text"]
