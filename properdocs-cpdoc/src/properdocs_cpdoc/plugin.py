# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""ProperDocs plugin which mounts a standalone cpdoc API site."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

from properdocs.config import config_options as c
from properdocs.plugins import BasePlugin

from cpdoc.build import build_versions
from cpdoc.config import CpdocConfig, load_config

from .core import (
    default_issue_url,
    edit_url,
    publish_api,
    repository_provider,
    resolve_api_references,
    source_url,
)


class CpdocPlugin(BasePlugin):
    """Build cpdoc before ProperDocs and mount it into the final static site."""

    config_scheme = (
        ("config", c.Type(str, default="cpdoc.yml")),
        ("mount", c.Type(str, default="reference/api")),
    )

    def __init__(self) -> None:
        self._project_root: Path | None = None
        self._cpdoc: CpdocConfig | None = None
        self._last_fingerprint: tuple[tuple[str, int, int], ...] | None = None
        self._serve_active = False

    @property
    def mount(self) -> str:
        value = str(self.config.get("mount", "reference/api")).strip("/")
        if not value:
            raise RuntimeError("properdocs-cpdoc: mount must not be the site root")
        return value

    def on_startup(self, *, command: str, dirty: bool = False) -> None:
        del dirty
        self._serve_active = command == "serve"

    def _config_file(self, config) -> Path:
        value = getattr(config, "config_file_path", None)
        if value:
            return Path(value).resolve()
        return (Path.cwd() / "properdocs.yml").resolve()

    def on_config(self, config):
        config_file = self._config_file(config)
        self._project_root = config_file.parent
        cpdoc_file = Path(str(self.config.get("config", "cpdoc.yml")))
        if not cpdoc_file.is_absolute():
            cpdoc_file = self._project_root / cpdoc_file
        self._cpdoc = load_config(cpdoc_file)

        extra = dict(config.get("extra", {}) or {})
        repo_url = str(config.get("repo_url") or "").strip()
        if repo_url:
            provider = repository_provider(repo_url, extra)
            extra["besa_repo_provider"] = provider
            extra["besa_source_ref"] = os.environ.get("BESA_SOURCE_REF") or self._source_ref()
            if not extra.get("besa_issue_url"):
                extra["besa_issue_url"] = default_issue_url(repo_url, provider)
        config["extra"] = extra
        return config

    def _source_ref(self) -> str:
        assert self._project_root is not None
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=self._project_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=self._project_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return result.stdout.strip() if result.returncode == 0 else "main"

    def _fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        assert self._project_root is not None and self._cpdoc is not None
        roots = [self._project_root / "src", self._project_root / "test" / "base", self._project_root / ".git" / "refs"]
        files = [self._project_root / "besa.toml", self._cpdoc.config_file]
        values: list[tuple[str, int, int]] = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    stat = path.stat()
                    values.append((str(path), stat.st_mtime_ns, stat.st_size))
        for path in files:
            if path.is_file():
                stat = path.stat()
                values.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(sorted(values))

    def on_pre_build(self, *, config) -> None:
        del config
        assert self._cpdoc is not None
        fingerprint = self._fingerprint()
        if self._serve_active and fingerprint == self._last_fingerprint and self._cpdoc.output_versions.is_dir():
            return
        build_versions(
            self._cpdoc,
            project_docs_root_depth=len(PurePosixPath(self.mount).parts),
        )
        self._last_fingerprint = fingerprint

    def on_page_markdown(self, markdown, page, config, files=None):
        del config, files
        assert self._cpdoc is not None
        return resolve_api_references(
            markdown,
            page_dest_uri=page.file.dest_uri,
            mount=self.mount,
            default_version=self._cpdoc.default_version,
        )

    def on_page_context(self, context, page, config, nav=None):
        del nav
        assert self._project_root is not None
        repo_url = str(config.get("repo_url") or "").strip()
        extra = config.get("extra", {}) or {}
        ref = extra.get("besa_source_ref")
        if not repo_url or not ref:
            context["besa_source_url"] = None
            context["besa_edit_url"] = None
            return context
        source = Path(page.file.abs_src_path).resolve()
        try:
            relative_source = source.relative_to(self._project_root).as_posix()
        except ValueError:
            context["besa_source_url"] = None
            context["besa_edit_url"] = None
            return context
        provider = repository_provider(repo_url, extra)
        context["besa_source_url"] = source_url(repo_url, provider, str(ref), relative_source)
        context["besa_edit_url"] = edit_url(repo_url, provider, str(ref), relative_source)
        return context

    def on_post_build(self, *, config) -> None:
        assert self._cpdoc is not None
        publish_api(self._cpdoc.output_versions, Path(config["site_dir"]).resolve(), self.mount)
