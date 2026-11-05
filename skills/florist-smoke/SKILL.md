---
name: florist-smoke
description: "Loop step 4 (optional smoke check): write a tiny, safe Python test of one key assumption. Runs only after user approval, with a hard timeout. Returns SmokeOutput."
step: smoke
output: SmokeOutput
---

# Smoke check — is the key assumption true?

The context lists the top directions with their `smoke_worthy` assumptions. Propose **at most two**
smoke checks (zero is fine if nothing is cheap to test).

A smoke check is small and cheap:

- one self-contained Python file, standard library preferred;
- finishes in under 60 seconds on a laptop CPU, no GPU, no large downloads (≤ 20 MB);
- no writes outside the current directory, no credentials, no network except a single
  public download or HTTP GET when the assumption is literally "this dataset / API is reachable";
- never installs packages. If a third-party library is needed, test it with
  `importlib.util.find_spec` and report availability as the result instead of importing it blindly.

The code **must** end by printing exactly one line:

```
SMOKE_RESULT {"metric_name": number, ...}
```

with numeric values only (use 1/0 for yes/no). Florist parses this line into a chart.

Fields: `direction_ref` (direction id), `assumption` (one sentence), `rationale` (why it matters),
`code`, `expected` (what result would confirm it), `timeout_s`.

Nothing runs until the user approves it.
