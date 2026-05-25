# Install (release tarball — no git clone)

End users install from a **GitHub Release** archive, not from a git clone. No code signing or `.dmg` required.

## Prerequisites

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Python env + CLI install |
| [Homebrew](https://brew.sh/) (optional) | `install.sh` can install `ffmpeg` and `huggingface-cli` if you agree |
| Hugging Face CLI | Model download (prompted or manual) — see [HUGGINGFACE.md](HUGGINGFACE.md) |

## Option 1: Download release and install

1. Open [GitHub Releases](https://github.com/digg-consulting/offline-video-scribe/releases).
2. Download `offline-video-scribe-<version>-macos.tar.gz`.
3. Run:

```bash
tar xzf offline-video-scribe-*-macos.tar.gz
cd offline-video-scribe-*-macos
./install.sh
```

`install.sh` installs the CLI and **asks** before Homebrew packages and model downloads. Skip models during install if you prefer — run `offline-video-scribe check` afterward and follow the printed steps.

Non-interactive: `./install.sh -y`

## Option 2: Bootstrap script (curl)

Pin a version (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/digg-consulting/offline-video-scribe/main/scripts/bootstrap-install.sh | OVS_VERSION=0.1.0 bash
```

Latest release (uses GitHub API):

```bash
curl -fsSL https://raw.githubusercontent.com/digg-consulting/offline-video-scribe/main/scripts/bootstrap-install.sh | bash
```

Extracted under `~/.local/share/digg/offline-video-scribe-releases/` by default.

## Upgrade

Upgrading refreshes the **global CLI** (`~/.local/bin/offline-video-scribe`, `~/.local/share/digg/offline-video-scribe/`). It does **not** re-download Hugging Face models or re-prompt for Homebrew. Your config (`~/.config/digg/offline-video-scribe/config.yaml`) and model cache (`~/.cache/huggingface/hub`) are left as-is.

`update.sh` runs `install.sh --update` (verify-only for prerequisites, refresh `config.yaml.example`).

### Release tarball (typical)

1. Download the newer `offline-video-scribe-<version>-macos.tar.gz` from [GitHub Releases](https://github.com/digg-consulting/offline-video-scribe/releases).
2. Extract and run `update.sh` from **that** folder (any extract path is fine):

```bash
tar xzf offline-video-scribe-0.2.0-macos.tar.gz
cd offline-video-scribe-0.2.0-macos
./update.sh
```

You can remove older extracted folders afterward; the CLI does not depend on them.

### Bootstrap install path

If you installed via `bootstrap-install.sh`, either use a new tarball as above, or download the new release and run `./update.sh` inside the extracted directory. The default extract location is:

```text
~/.local/share/digg/offline-video-scribe-releases/offline-video-scribe-<version>-macos/
```

### Git clone (developers)

```bash
cd ~/github/digg-consulting/offline-video-scribe   # your clone
git pull
./update.sh
```

### Same directory, newer files

If you replaced files in an existing tree (e.g. re-extracted over an old folder):

```bash
./install.sh --update
# equivalent to ./update.sh
```

## Uninstall

From the extracted release directory:

```bash
./uninstall.sh
```

## Developers

From a git clone (same `install.sh`, includes dev dependencies):

```bash
git clone https://github.com/digg-consulting/offline-video-scribe.git
cd offline-video-scribe
./install.sh
```

Build a release tarball locally:

```bash
./scripts/make-release.sh
```

**Publish to GitHub (automated):** see [RELEASE.md](RELEASE.md) — set `version` in `pyproject.toml`, then:

```bash
./scripts/publish-release.sh
```

That pushes tag `v<version>`; GitHub Actions uploads `dist/offline-video-scribe-<version>-macos.tar.gz`.
