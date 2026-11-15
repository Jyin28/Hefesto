"""Cache identity and reproducible snapshots (J2.5). Owner: Jacky. [PROPUESTA].

Provider-agnostic, pure stdlib. The adapter (mock now, real later) supplies three hooks:
  manifest_fn(q)  -> versions of every input that can change the result (known before computing)
  normalize_fn(q) -> canonical query (sorted ids, filled defaults)
  freshness_fn(d) -> re-evaluate time-dependent availability of a cached response dict

Rules:
  * Key = source_mode + function + normalized query + only the manifest parts the product depends on.
    source_mode is the key prefix, so mock and real never share an entry.
  * generated_at, checked_at and the hypothesis are never inputs.
  * error and unsupported responses are never cached.
  * Freshness is re-evaluated on every read; the stored snapshot (issued_at, payload) is untouched.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .contracts import canonical_json, sha256_hex, to_json, to_jsonable
from .contracts_ext import PRODUCTS

# Manifest sections each product depends on (F2 spec, "Cache planificada").
_BASE = ("schema", "code", "method", "geo", "family_data")
KEY_PARTS: dict[str, tuple[str, ...]] = {
    "historical": _BASE,
    "event": _BASE + ("event",),
    "forecast": _BASE + ("forecast",),
    "water_distribution": ("schema", "code", "geo", "water", "crosswalk"),
    "service_coverage": ("schema", "code", "geo", "water", "crosswalk", "indicator_definition", "denominator"),
}

# change -> manifest section that carries it
INVALIDATION_MATRIX: dict[str, str] = {
    "zone_version": "geo", "geometry": "geo", "mask": "geo", "grid": "geo",
    "family_data": "family_data", "method": "method", "code": "code", "schema": "schema",
    "baseline": "event", "event_id": "event",
    "model_config": "forecast", "issued_at": "forecast", "data_cutoff": "forecast", "horizon": "forecast",
    "water_dataset": "water", "corrections": "water", "crosswalk": "crosswalk",
    "indicator_definition": "indicator_definition", "denominator": "denominator",
}


def affected_products(change: str) -> tuple[str, ...]:
    """Products whose cache entry is invalidated by `change` (derived from KEY_PARTS)."""
    part = INVALIDATION_MATRIX[change]
    return tuple(p for p in PRODUCTS if part in KEY_PARTS[p])


def cache_key(q: Any, manifest: dict, fn: str = "", normalize_fn: Callable | None = None) -> str:
    """'<source_mode>:<sha256[:32]>'. Same inputs -> same key; any relevant version change -> new key."""
    nq = normalize_fn(q) if normalize_fn else q
    parts = {p: manifest[p] for p in KEY_PARTS[nq.product] if p in manifest}
    payload = {"fn": fn, "query": to_jsonable(nq), "parts": parts}
    return f"{manifest['source_mode']}:{sha256_hex(canonical_json(payload))[:32]}"


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    product: str
    result_id: str | None
    manifest: dict
    response: dict
    created_at: str  # informational; never part of the identity


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SnapshotStore:
    def __init__(self, manifest_fn: Callable, normalize_fn: Callable | None = None,
                 freshness_fn: Callable[[dict], dict] | None = None,
                 clock: Callable[[], str] = _utc_now):
        self._manifest_fn = manifest_fn
        self._normalize_fn = normalize_fn
        self._freshness_fn = freshness_fn
        self._clock = clock
        self._store: dict[str, Snapshot] = {}
        self.hits = 0
        self.misses = 0
        self.uncached = 0

    def key_for(self, q: Any, compute: Callable) -> str:
        return cache_key(q, self._manifest_fn(q), compute.__name__, self._normalize_fn)

    def get_or_compute(self, q: Any, compute: Callable) -> tuple[dict, bool]:
        """(response dict, hit). error/unsupported results are returned but never stored."""
        manifest = self._manifest_fn(q)
        key = cache_key(q, manifest, compute.__name__, self._normalize_fn)
        snap = self._store.get(key)
        if snap is not None:
            self.hits += 1
            resp = copy.deepcopy(snap.response)
            return (self._freshness_fn(resp) if self._freshness_fn else resp), True
        self.misses += 1
        resp = to_jsonable(compute(q))
        if resp["availability"]["status"] in ("error", "unsupported"):
            self.uncached += 1
            return resp, False
        self._store[key] = Snapshot(key, resp["product"], resp.get("result_id"), manifest,
                                    copy.deepcopy(resp), self._clock())
        return (self._freshness_fn(resp) if self._freshness_fn else resp), False

    def __len__(self) -> int:
        return len(self._store)

    def keys(self) -> list[str]:
        return sorted(self._store)

    def save(self, directory: str) -> list[str]:
        os.makedirs(directory, exist_ok=True)
        written = []
        for key, snap in self._store.items():
            name = key.replace(":", "_") + ".json"
            with open(os.path.join(directory, name), "w", encoding="utf-8") as fh:
                fh.write(to_json(snap, indent=2))
            written.append(name)
        return sorted(written)

    def load(self, directory: str) -> int:
        n = 0
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                d = json.load(fh)
            self._store[d["snapshot_id"]] = Snapshot(**d)
            n += 1
        return n
