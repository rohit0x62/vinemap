# Contributing to Vinemap

Thanks for helping improve Vinemap — the local-first code graph and context engine for AI coding agents.

## Quick links

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [GitHub Discussions](https://github.com/rohit0x62/vinemap/discussions)
- [Issue tracker](https://github.com/rohit0x62/vinemap/issues)

## Development setup

```bash
git clone https://github.com/rohit0x62/vinemap.git
cd vinemap/engine
pip install -e ".[dev,treesitter]"
pytest tests -q -m "not slow"
python eval/run_eval.py --all
```

Website (static export):

```bash
cd website
npm install
npm run build
```

## What to work on

Check [docs/ROADMAP.md](docs/ROADMAP.md) and open [good first issues](https://github.com/rohit0x62/vinemap/labels/good%20first%20issue). High-impact areas:

- Retrieval quality (golden eval cases in `engine/eval/golden/`)
- Language parsers (`engine/vinemap/scanner/parsers/`)
- Agent integrations (`engine/vinemap/agents/`)
- Docs and website (`website/app/docs/`)

## Pull request checklist

1. **Tests** — `pytest` passes; add tests for behavior changes.
2. **Eval** — if ranking changes, run `python eval/run_eval.py --all` and update golden sets or `website/app/benchmarks/eval-data.json` via `python eval/export_results.py`.
3. **Scope** — one logical change per PR; avoid drive-by refactors.
4. **Style** — match surrounding code; imports at top of file.

## Code of conduct

Be respectful in issues, discussions, and reviews. We optimize for clarity and user trust — especially around local-first privacy claims.

## License

By contributing, you agree that your contributions are licensed under the [Apache-2.0 License](LICENSE).
