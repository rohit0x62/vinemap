## Summary

<!-- What changed and why (1–3 sentences) -->

## Test plan

- [ ] `pytest tests -q -m "not slow"` (engine)
- [ ] `python eval/run_eval.py --all` (if ranking/indexing changed)
- [ ] Manual: `vinemap index .` + `vinemap query "..."` (if user-facing)

## Checklist

- [ ] Focused diff — no unrelated changes
- [ ] Docs/website updated if CLI or install flow changed
