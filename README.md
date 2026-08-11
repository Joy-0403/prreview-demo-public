# incident-digest

Turns a list of incidents into the short text an on-call engineer reads in the
morning. Small on purpose: it exists to exercise a code review agent
end to end, so the interesting part is not the feature set but the seams.

```bash
PYTHONPATH=src python -m digest.cli incidents.json
PYTHONPATH=src python -m pytest -q
```

## How it fits together

```
config/categories.json     the controlled vocabulary: key, label, weight
        │
        ├─ digest/categories.py   loads it; refuses unknown keys
        └─ Dockerfile             bakes a copy into the image at build time

digest/severity.py         the one severity ladder (weight + affected users)
        └─ digest/render.py       reads the ladder rather than restating it

digest/summarize.py        the per-incident prompt, sent once per record
digest/llm.py              the Bedrock call: which model, which region
digest/cli.py              wires the four together
```

## Things that have to move together

Kept explicit because they are what a change here is most likely to break,
and none of them are visible in a diff that touches only one side:

- **`config/categories.json` and the image.** The Dockerfile copies it at build
  time, so a running container serves the vocabulary it was built with.
- **The severity ladder and `render.ALERT_FLOOR`.** `render` reads `LADDER`
  rather than naming rungs, so adding or reordering a rung changes what gets a
  siren without anyone editing `render.py`.
- **`summarize.PREAMBLE` and the size of a batch.** It is sent with every
  incident, so a sentence added there is paid once per record, on every run.
- **`llm.MODEL_ID` and what a request costs.** The model is named in one
  place and the region in the same one, so a change to either moves the
  price of every incident in every digest.
- **The tests and the current behaviour.** `test_severity` pins the two cases
  the ladder exists to get right: high weight with nobody affected, and a
  trivial category affecting everybody.

## The synthetic traffic

`tools/traffic.py` calls Bedrock on a schedule. It is not part of the digest
and it is labelled loudly, because usage that looks organic but is not is worse
than no usage at all — somebody eventually reasons from it.

It exists because CloudWatch metrics under `AWS/Bedrock` are written by AWS.
They cannot be backfilled or faked, so a cost monitor cannot be demonstrated
against a repository that has never called a model. A week of history costs a
week of waiting.

```bash
python tools/traffic.py --dry-run     # the plan and the estimate, spends nothing
python tools/traffic.py               # what today's date calls for
python tools/traffic.py --mode balloon
```

**What it costs.** Twelve calls a day of roughly 120 input and 40 output tokens
against a 7B model: about $0.0004 on an ordinary day, and under two cents for a
month including the anomalous ones. The figure is stated because "it's cheap"
is how recurring spend gets approved without anybody knowing the number.

The model is `mistral-7b`, chosen because nothing else in this AWS account
calls it. CloudWatch aggregates per model per region, so sharing one with a
real workload would put synthetic traffic into that workload's monitoring and
bury this one's anomalies under its volume.

**Most days are ordinary on purpose.** The monitor judges a day against the
median of the days around it, so it needs a majority of ordinary days to have a
baseline at all. Making every day anomalous would move the baseline onto the
anomaly and detect nothing — which is worth understanding in its own right: a
system whose normal *is* the problem holds no internal evidence that anything
is wrong.

The bad days model the two ways spend actually goes wrong:

| | |
|---|---|
| `balloon`, days divisible by 5 | something got appended to every prompt — retrieved context, a longer template, a history window that stopped being trimmed |
| `collapse`, days divisible by 7 | the prompt builder returned early and the model got a bare title. Nothing raises, output still arrives, and the bill goes **down**, which is why a ceiling alarm never finds this one |

**Scheduling it.** Two paths, and which is open to you depends on whether
anybody will give you an IAM role:

- `.github/workflows/traffic.yml` — runs in Actions on OIDC, needs no laptop
  and stores no secret, and needs a `DEMO_AWS_ROLE_ARN` that somebody with IAM
  permissions has to create. Without it the job says so once and stops.
- `tools/run-daily.sh` with `tools/com.prreview.demo-traffic.plist` — launchd
  on a Mac, using the credentials already in `~/.aws`. Works today. A sleeping
  laptop means missed days, and a missed day is a gap in the history rather
  than a wrong number: the monitor compares against the days it has, so gaps
  cost resolution and nothing else.
