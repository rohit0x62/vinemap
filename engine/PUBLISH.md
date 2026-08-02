# Publishing Vinemap to PyPI

Secure options — **never commit your API token** to git.

## Token setup (pick one)

### Option A — environment variable (recommended for MCP / CI)

```bash
export PYPI_API_TOKEN="pypi-AgEI..."   # from https://pypi.org/manage/account/token/
export TWINE_USERNAME="__token__"      # optional; script sets this automatically
```

### Option B — local file (recommended for terminal)

```bash
mkdir -p ~/.config/vinemap
chmod 700 ~/.config/vinemap
echo "pypi-AgEI..." > ~/.config/vinemap/pypi-token
chmod 600 ~/.config/vinemap/pypi-token
```

The publish script refuses to read token files that are group/world readable.

---

## CLI publish (local)

```bash
cd engine
pip install build twine

# Check local vs PyPI version + token source (no secrets printed)
python tools/pypi_publish.py status

# Build only
python tools/pypi_publish.py build

# Build + upload (must confirm exact version string)
python tools/pypi_publish.py publish --confirm 0.1.2
```

Or use the wrapper:

```bash
./scripts/publish.sh status
./scripts/publish.sh publish --confirm 0.1.2
```

Safety gates:

- Token never accepted on the command line or in MCP tool args
- `--confirm` must match `version` in `pyproject.toml` exactly
- Upload blocked if that version already exists on PyPI
- `twine check` runs before every upload

---

## MCP publish (Cursor)

Use the dedicated **vinemap-publish** MCP server so the agent can build/upload without seeing your token in chat.

1. Copy `.cursor/mcp.publish.json.example` → merge into **`~/.cursor/mcp.json`** (user-level, not the repo)
2. Set absolute path to `engine/tools/publish_mcp.py`
3. Put `PYPI_API_TOKEN` in the `env` block of that server only

Example `~/.cursor/mcp.json` fragment:

```json
{
  "mcpServers": {
    "vinemap": { "...": "..." },
    "vinemap-publish": {
      "command": "python3",
      "args": ["/Users/you/vinemap/engine/tools/publish_mcp.py"],
      "env": {
        "PYPI_API_TOKEN": "pypi-AgEI..."
      }
    }
  }
}
```

MCP tools:

| Tool | Description |
|------|-------------|
| `pypi_status` | Local vs PyPI version; token configured (yes/no) |
| `pypi_build` | Build wheel/sdist + `twine check` |
| `pypi_publish` | Upload with `confirm: "0.1.2"` matching pyproject |

Reload Cursor → Settings → MCP after editing.

---

## GitHub Actions (no token in repo)

### Trusted publishing (best)

PyPI → Account settings → Publishing → add GitHub repo `owner/vinemap`, workflow `publish.yml`.

### API token fallback

Repo secret: `PYPI_API_TOKEN` = your `pypi-…` token.

Actions → **Publish PyPI** → Run workflow → type `publish` to confirm.

---

## Version bump checklist

1. Bump `version` in `engine/pyproject.toml` and `engine/vinemap/__init__.py`
2. Bump `website/app/links.ts` `VERSION` if shipping site too
3. `python tools/pypi_publish.py status`
4. `python tools/pypi_publish.py publish --confirm X.Y.Z`
5. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`

---

## What NOT to do

- Do not put tokens in `.cursor/mcp.json` inside the git repo
- Do not pass `--token` or paste tokens into agent prompts
- Do not use `twine upload` with password in shell history — use the script or env
