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
- **The tests and the current behaviour.** `test_severity` pins the two cases
  the ladder exists to get right: high weight with nobody affected, and a
  trivial category affecting everybody.
