You are refining concise Strudel code so that rendered audio better matches the target.

Return strict JSON:
{
  "candidates": ["..."]
}

Rules:
- synth-only Strudel code
- concise, no markdown fences
- keep it within 4 lines max
- prefer explicit `setcps(...)` when tempo is important
- improve based on the score breakdowns and critiques in the candidate JSON

Target description JSON:
{description_json}

Current top candidates JSON:
{candidates_json}

Generate exactly {candidate_count} improved candidates.
