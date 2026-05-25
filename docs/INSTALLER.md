# macOS distribution

**Shipped today:** unsigned **release tarball** (option B) — no `.dmg`, no Apple code signing.

| Audience | How |
|----------|-----|
| End users | [INSTALL.md](INSTALL.md) — GitHub Release `.tar.gz` or bootstrap `curl` script |
| Developers | `git clone` + `./install.sh` |
| Future | Signed `.pkg` / `.dmg` (optional; see below) |

## Release tarball (option B)

`./scripts/make-release.sh` produces:

```text
dist/offline-video-scribe-<version>-macos.tar.gz
  install.sh
  update.sh
  uninstall.sh
  VERSION
  INSTALL.txt
  pyproject.toml, uv.lock, src/, config/, docs/, …
```

Publish by creating a GitHub Release tagged `v<version>` and attaching the tarball (`.github/workflows/release.yml` does this on tag push).

**Not bundled:** Hugging Face model weights (prerequisite; `install.sh` asks or user follows [HUGGINGFACE.md](HUGGINGFACE.md)).

**Requires on PATH:** `uv`. Optional: Homebrew for `ffmpeg` / `huggingface-cli`.

## Layout after install

| Data | Location |
|------|----------|
| Config | `~/.config/digg/offline-video-scribe/` |
| Model cache | `~/.cache/huggingface/hub` |
| uv tool | `~/.local/share/digg/offline-video-scribe/` |
| CLI | `~/.local/bin/offline-video-scribe` (`ovs` → symlink) |
| Bootstrap extract (optional) | `~/.local/share/digg/offline-video-scribe-releases/` |

## Future: `.pkg` / `.dmg` (optional)

Not required. Unsigned packages trigger Gatekeeper warnings; the tarball + Terminal install avoids that.

If added later, payload could mirror the release tree under `/opt/offline-video-scribe` with the same `install.sh` logic.
