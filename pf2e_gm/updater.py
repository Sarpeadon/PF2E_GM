"""Automatic download of Foundry pf2e compendium data from GitHub releases.

Streams the release source tarball and writes only the packs/ folder to disk,
so nothing else from the repo is stored. Uses the standard library only.
"""
import json
import re
import os
import shutil
import stat
import tarfile
import time
import urllib.request
from pathlib import PurePosixPath, Path

REPO = "foundryvtt/pf2e"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
TARBALL = "https://codeload.github.com/" + REPO + "/tar.gz/refs/tags/{tag}"
HEADERS = {"User-Agent": "pf2e-gm-tool", "Accept": "application/vnd.github+json"}

# The repo also ships Starfinder 2e and module releases; only accept pf2e system tags.
PF2E_TAG = re.compile(r"^pf2e-(\d+)\.(\d+)\.(\d+)$")
STARFINDER = re.compile(r"(^|[/_\-.])(sf2e|starfinder)([/_\-.]|$)", re.IGNORECASE)


def latest_pf2e_tag(timeout=20):
    req = urllib.request.Request(RELEASES_API, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        releases = json.load(r)
    tags = []
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        m = PF2E_TAG.match(rel.get("tag_name", ""))
        if m:
            tags.append((tuple(int(x) for x in m.groups()), rel["tag_name"]))
    if not tags:
        raise RuntimeError("No pf2e release found on GitHub.")
    return max(tags)[1]


def installed_tag(dest):
    p = Path(dest) / "version.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("tag", "")
    return ""


class _Progress:
    """File-like wrapper that reports bytes read."""
    def __init__(self, f, cb):
        self.f, self.cb, self.n = f, cb, 0

    def read(self, size=-1):
        chunk = self.f.read(size)
        self.n += len(chunk)
        if self.cb:
            self.cb(self.n)
        return chunk


LANG_FILE = re.compile(r"(^|[-_])en\.json$")


def _safe_rel(member_name):
    """Map a tarball member to packs/... or lang/... (English language files), else None."""
    parts = PurePosixPath(member_name).parts
    if parts and parts[0] == ".":
        parts = parts[1:]
    if any(p in ("..", "") for p in parts):
        return None
    if len(parts) >= 3 and parts[1] == "packs":
        rel = PurePosixPath("packs", *parts[2:])
        return rel if rel.suffix in (".json", ".db") else None
    if len(parts) == 4 and parts[1:3] == ("static", "lang") and LANG_FILE.search(parts[3]):
        return PurePosixPath("lang", parts[3])
    return None


def _on_rm_error(func, path, exc_info):
    """rmtree helper: clear read-only flags and retry (Windows)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def _rmtree(path, attempts=8):
    """Remove a folder, retrying while Windows (Defender, indexer) still holds files open."""
    path = Path(path)
    for i in range(attempts):
        if not path.exists():
            return True
        shutil.rmtree(path, onerror=_on_rm_error)
        if not path.exists():
            return True
        time.sleep(min(0.5 * (i + 1), 3))
    return not path.exists()


def _swap_in(staging, dest, progress=None, attempts=10):
    """Replace dest with staging. Retries the rename, then falls back to copying.

    On Windows a folder rename fails with Access Denied while antivirus or the search indexer is
    still scanning the thousands of files just written, so we wait and retry before copying.
    """
    staging, dest = Path(staging), Path(dest)
    old = dest.with_name(dest.name + "_old")
    if dest.exists():
        _rmtree(old)
        try:
            dest.rename(old)          # move old data aside first so a failure can be rolled back
        except OSError:
            if not _rmtree(dest):
                raise RuntimeError(f"Could not remove the old data folder: {dest}. "
                                   "Close anything using it and try again.")
    last_err = None
    for i in range(attempts):
        try:
            staging.rename(dest)
            _rmtree(old)
            return
        except OSError as e:
            last_err = e
            if progress:
                progress(f"Waiting for Windows to release the new files (attempt {i + 1}/{attempts})...")
            time.sleep(min(0.5 * (i + 1), 3))
    # Rename never succeeded: copy instead (slower, but doesn't need the folder unlocked).
    if progress:
        progress("Rename blocked; copying data into place instead (this takes a minute)...")
    try:
        _rmtree(dest)
        shutil.copytree(staging, dest)
    except OSError as e:
        _rmtree(dest)
        if old.exists():
            try:
                old.rename(dest)      # roll back to previous data
            except OSError:
                pass
        raise RuntimeError(f"Could not move downloaded data into place ({e}). The download is kept in "
                           f"{staging}; close the app, rename that folder to '{dest.name}', then use "
                           f"Build / Rebuild Index.") from last_err
    _rmtree(staging)
    _rmtree(old)


def recover_staging(dest):
    """If a previous run downloaded fully but failed to swap, finish the swap. Returns the tag or ''."""
    dest = Path(dest)
    staging = dest.with_name(dest.name + "_staging")
    if (staging / "version.json").exists() and (staging / "packs").is_dir():
        _swap_in(staging, dest)
        return installed_tag(dest)
    return ""


def download(dest, tag=None, include_starfinder=False, progress=None, source=None):
    """Download pf2e packs for `tag` (latest if None) into dest/packs. Returns the tag.

    `source` lets tests pass a local tarball path instead of hitting the network.
    """
    dest = Path(dest)
    tag = tag or latest_pf2e_tag()
    staging = dest.with_name(dest.name + "_staging")
    if installed_tag(staging) == tag and (staging / "packs").is_dir():
        # A previous run finished downloading this release but couldn't move it into place.
        if progress:
            progress(f"Found a completed {tag} download from last time. Moving into place...")
        _swap_in(staging, dest, progress)
        return tag
    _rmtree(staging)
    staging.mkdir(parents=True)

    if source:
        raw = open(source, "rb")
    else:
        req = urllib.request.Request(TARBALL.format(tag=tag), headers={"User-Agent": HEADERS["User-Agent"]})
        raw = urllib.request.urlopen(req, timeout=60)
    files = 0
    last = [0]

    def report(n):
        if progress and n - last[0] > 2_000_000:
            last[0] = n
            progress(f"Downloading {tag}: {n / 1_048_576:.0f} MB read, {files} data files")
    try:
        with raw, tarfile.open(fileobj=_Progress(raw, report), mode="r|gz") as tar:
            for m in tar:
                if not m.isfile():
                    continue
                rel = _safe_rel(m.name)
                if rel is None:
                    continue
                if not include_starfinder and STARFINDER.search(str(rel)):
                    continue
                out = staging / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                files += rel.parts[0] == "packs"
    except Exception:
        _rmtree(staging)
        raise
    if files == 0:
        _rmtree(staging)
        raise RuntimeError("Download finished but no pack files were found. Repo layout may have changed.")

    (staging / "version.json").write_text(json.dumps({"tag": tag, "files": files}), encoding="utf-8")
    # Swap only after a complete download so a failure never leaves you with half the data.
    if progress:
        progress(f"Downloaded {files} data files. Moving into place...")
    _swap_in(staging, dest, progress)
    return tag
