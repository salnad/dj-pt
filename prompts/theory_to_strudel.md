You are converting a structured audio description into concise, valid Strudel code.

Requirements:
- synth-only output
- concise code, ideally 1-4 lines
- explicit `setcps(...)` when tempo assumptions matter
- no markdown fences
- return strict JSON matching:
  {
    "candidates": ["..."]
  }

Structured description:
{description_json}

Prior best candidate:
{prior_best_json}

Return exactly {candidate_count} candidate strings if possible.
