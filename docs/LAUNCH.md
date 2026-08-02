# Launch checklist — Vinemap

Use this when publishing the public repo and announcing v0.1.x.

## Pre-launch (code & infra)

- [x] Apache-2.0 LICENSE at repo root
- [x] CONTRIBUTING.md + issue/PR templates
- [x] CI: pytest + eval on mac/linux/windows
- [x] Docs site: [vinemap.xyz/docs](https://vinemap.xyz/docs)
- [x] Benchmarks: [vinemap.xyz/benchmarks](https://vinemap.xyz/benchmarks) (exported from eval harness)
- [x] Deploy workflow: `.github/workflows/deploy-website.yml` → GitHub Pages
- [x] Website hosted on AWS S3 + CloudFront at vinemap.xyz (private website repo deploys via `winklogiq` profile)
- [x] PyPI v0.1.2 published (see `engine/PUBLISH.md` for trusted publisher setup)
- [x] GitHub Discussions enabled — categories: General, Q&A, Show and tell

## Launch day posts (drafts)

### Show HN — title

**Show HN: Vinemap – local code graph + MCP context for AI coding agents**

Body sketch:

> Vinemap indexes your repo into a structural code graph (imports, symbols, call edges) and injects token-budgeted context into Cursor, Claude Code, Codex, etc. via MCP — before the agent starts grepping.
>
> - 100% local, stdlib-only core
> - `pip install vinemap` → `vinemap cursor .`
> - Open eval harness: 100% precision@5 on 24 golden queries
>
> Site: https://vinemap.xyz  
> Repo: https://github.com/rohit0x62/vinemap  
> Benchmarks: https://vinemap.xyz/benchmarks

### r/ClaudeAI / r/cursor

Same hook — emphasize pre-injection hooks for Claude and MCP for Cursor. Link `/docs` agent guides.

### X / Product Hunt

One-liner: *"Give your codebase a brain — local graph context for AI agents."*  
Screenshot: dashboard or `vinemap query` output. Link benchmarks for credibility.

## Post-launch

- [ ] Monitor GitHub Issues + Discussions daily (first week)
- [ ] Triage feedback via `vinemap feedback` and issue templates
- [ ] Weekly eval export to keep benchmarks page honest
- [ ] Discord (optional) — link from community section when ready

## Feedback channels

- CLI: `vinemap feedback "your message"`
- GitHub Issues (bug/feature templates)
- GitHub Discussions (questions)
- Email: winklogiq@gmail.com
