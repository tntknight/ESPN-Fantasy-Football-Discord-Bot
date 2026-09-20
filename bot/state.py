"""Tiny JSON-file-backed key/value store used to remember what's already
been posted (so the bot doesn't spam the channel on every poll / restart).

Not built for concurrent writers -- this bot is single-process, so a plain
JSON file is enough. Note that on Railway the filesystem is ephemeral across
redeploys, so state resets when you push a new version (not on a normal
restart/crash-recovery within the same deploy).
"""

import json
import os
import threading


class State:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def _save(self) -> None:
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
        os.replace(tmp_path, self._path)

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self._save()
