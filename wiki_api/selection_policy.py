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
_GUIDANCE_HEADER = "## Selector Guidance"


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
    trimmed: list[str]
    selector_covered_roles: list[str]


def load_selection_policy(store: WikiStore) -> SelectionPolicy:
    # Re-read from the store on every call (no caching): matches the store's
    # no-caching idiom and keeps the policy live-editable without a restart.
    try:
        page = store.read_page(POLICY_PAGE_NAME)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"{POLICY_PAGE_NAME} could not be read: {exc}") from exc
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


def load_selector_guidance(store: WikiStore) -> str:
    """Extract the Selector Guidance prose from the policy page.

    Re-read per call, matching the module's no-caching idiom.
    """
    try:
        page = store.read_page(POLICY_PAGE_NAME)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"{POLICY_PAGE_NAME} could not be read: {exc}") from exc
    lines = page.content.splitlines()
    collected: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == _GUIDANCE_HEADER:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            collected.append(line)
    guidance = "\n".join(collected).strip()
    if not guidance:
        raise ValueError(f"{POLICY_PAGE_NAME} has no Selector Guidance section")
    return guidance


def enforce_skeleton(
    pages_used: list[str],
    policy: SelectionPolicy,
    *,
    max_pages: int | None = None,
) -> SkeletonResult:
    """Apply structural coverage and, optionally, a strict final-page budget.

    ``max_pages`` applies to the pages returned by this function. The context-pack
    endpoint reserves one additional slot for ``RUNTIME_RULES.md`` before calling
    this function, so its public ``max_pages`` field remains a true response cap.
    Required role coverage wins over optional selector picks when trimming is
    necessary.
    """
    dropped = [
        page
        for page in pages_used
        if any(fnmatch(page, pattern) for pattern in policy.drop_pages)
    ]
    kept = list(dict.fromkeys(page for page in pages_used if page not in dropped))
    backfilled: list[dict[str, str]] = []
    covered: list[str] = []
    for role in policy.required_roles:
        if any(page in role.members for page in kept):
            covered.append(role.name)
        else:
            kept.append(role.default)
            backfilled.append({"role": role.name, "page": role.default})

    trimmed: list[str] = []
    if max_pages is not None:
        if max_pages < len(policy.required_roles):
            raise ValueError(
                "max_pages cannot preserve the required selection skeleton: "
                f"need at least {len(policy.required_roles)}, got {max_pages}"
            )

        protected: set[str] = set()
        for role in policy.required_roles:
            protected.add(next(page for page in kept if page in role.members))

        optional = [page for page in kept if page not in protected]
        trim_count = max(len(kept) - max_pages, 0)
        trim_order = [
            *(["index.md"] if "index.md" in optional else []),
            *reversed([page for page in optional if page != "index.md"]),
        ]
        trimmed = trim_order[:trim_count]
        trimmed_set = set(trimmed)
        kept = [page for page in kept if page not in trimmed_set]

    return SkeletonResult(
        final_pages=kept,
        backfilled=backfilled,
        dropped=dropped,
        trimmed=trimmed,
        selector_covered_roles=covered,
    )
