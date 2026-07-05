"""Deterministic skeleton failsafe for context-pack page selection.

Policy is defined in markdown (selection-policy.md) and parsed here; this
module encodes general structural invariants only — never case-specific
selection rules. Every backfill is a measured selector miss.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch

import yaml

from .wiki_store import WikiStore

POLICY_PAGE_NAME = "selection-policy.md"
_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class RequiredRole:
    name: str
    members: tuple[str, ...]
    default: str


@dataclass(frozen=True)
class SelectionPolicy:
    skeleton_version: int
    required_roles: tuple[RequiredRole, ...]
    drop_pages: tuple[str, ...]


@dataclass(frozen=True)
class SkeletonResult:
    final_pages: list[str]
    backfilled: list[dict[str, str]]
    dropped: list[str]
    selector_covered_roles: list[str]


def load_selection_policy(store: WikiStore) -> SelectionPolicy:
    page = store.read_page(POLICY_PAGE_NAME)
    match = _YAML_BLOCK_RE.search(page.content)
    if not match:
        raise ValueError(f"{POLICY_PAGE_NAME} has no fenced yaml policy block")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"{POLICY_PAGE_NAME} policy block is not a mapping")
    missing_keys = {"skeleton_version", "required_roles", "drop_pages"} - set(data)
    if missing_keys:
        raise ValueError(f"{POLICY_PAGE_NAME} policy block missing keys: {sorted(missing_keys)}")
    raw_roles = data["required_roles"]
    raw_drop = data["drop_pages"]
    if not isinstance(raw_roles, dict) or not raw_roles:
        raise ValueError(f"{POLICY_PAGE_NAME} required_roles must be a non-empty mapping")
    if not isinstance(raw_drop, list):
        raise ValueError(f"{POLICY_PAGE_NAME} drop_pages must be a list")
    roles: list[RequiredRole] = []
    for role_name, role_data in raw_roles.items():
        members = role_data.get("members") if isinstance(role_data, dict) else None
        default = role_data.get("default") if isinstance(role_data, dict) else None
        if not isinstance(members, list) or not members or not isinstance(default, str):
            raise ValueError(
                f"{POLICY_PAGE_NAME} role {role_name!r} needs a non-empty members list and a default"
            )
        member_names = tuple(str(member) for member in members)
        if default not in member_names:
            raise ValueError(
                f"{POLICY_PAGE_NAME} role {role_name!r} default {default!r} is not among its members"
            )
        roles.append(RequiredRole(name=str(role_name), members=member_names, default=default))
    return SelectionPolicy(
        skeleton_version=int(data["skeleton_version"]),
        required_roles=tuple(roles),
        drop_pages=tuple(str(pattern) for pattern in raw_drop),
    )


def enforce_skeleton(pages_used: list[str], policy: SelectionPolicy) -> SkeletonResult:
    dropped = [
        page
        for page in pages_used
        if any(fnmatch(page, pattern) for pattern in policy.drop_pages)
    ]
    kept = [page for page in pages_used if page not in dropped]
    backfilled: list[dict[str, str]] = []
    covered: list[str] = []
    for role in policy.required_roles:
        if any(page in role.members for page in kept):
            covered.append(role.name)
        else:
            kept.append(role.default)
            backfilled.append({"role": role.name, "page": role.default})
    return SkeletonResult(
        final_pages=kept,
        backfilled=backfilled,
        dropped=dropped,
        selector_covered_roles=covered,
    )
