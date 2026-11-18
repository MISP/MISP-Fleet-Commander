"""Organisations that do not line up across a fleet: the same UUID under other names, or the same name under other
UUIDs. Read from the digests each listing of a server's organisations leaves (see `models.organisationDigests`).

These matter because of sync: MISP matches organisations by UUID, and when sync brings a UUID it does not know under a
name that is taken, it creates a second organisation named `name_<random>`.
"""

import re
from typing import Optional

from application.health.engine import Finding, rule

# Servers named in an issue's detail before "and N more"
SHOWN_SERVERS = 3


def findingsFor(ctx, server) -> dict:
    """The findings of the server's fleet, computed once per evaluation context"""
    fleet_id = getattr(server, "fleet_id", None)
    cache = ctx.organisation_findings
    if fleet_id not in cache:
        from application.models import organisationDigests
        cache[fleet_id] = organisationDigests.fleetFindings(fleet_id, getattr(server, "user_id", None))
    return cache[fleet_id]


def shortUuid(uuid: str) -> str:
    return f"{uuid[:8]}…"


def looksCaptured(theirName: str, ourName: str) -> bool:
    """MISP's name for an organisation sync brought in while the name was taken"""
    return re.fullmatch(re.escape(" ".join(ourName.split()).lower()) + r"_\d+",
                        " ".join(theirName.split()).lower()) is not None


def where(serverIds, names) -> str:
    if len(serverIds) == 1:
        return names.get(serverIds[0], f"server #{serverIds[0]}")
    return f"{len(serverIds)} servers"


def fragment(kind: str, entry: list, ourName: str, names: dict) -> str:
    server = names.get(entry[0], f"server #{entry[0]}")
    if kind == "other_uuid":
        return f"{server}: another UUID ({shortUuid(entry[1])})"
    if kind == "split_there":
        return f"{server}: named “{entry[1]}”, next to another “{ourName}” ({shortUuid(entry[2])})"
    if kind == "split_here":
        return f"{server}: named “{entry[1]}”, which is another organisation here ({shortUuid(entry[2])})"
    return f"{server}: named “{entry[1]}”"


def mismatchFinding(uuid: str, found: dict, names: dict) -> Optional[Finding]:
    ourName = found.get("name") or uuid
    uuidServers = sorted({entry[0] for kind in ("other_uuid", "split_there", "split_here")
                          for entry in found.get(kind, [])}, key=lambda id: (names.get(id, "").lower(), id))
    nameServers = sorted({entry[0] for entry in found.get("renamed", [])},
                         key=lambda id: (names.get(id, "").lower(), id))
    if not uuidServers and not nameServers:
        return None
    fragments, evidence = [], []
    for kind in ("other_uuid", "split_there", "split_here", "renamed"):
        for entry in sorted(found.get(kind, []), key=lambda entry: (names.get(entry[0], "").lower(), entry[0])):
            fragments.append(fragment(kind, entry, ourName, names))
            item = {"server_id": entry[0], "server": names.get(entry[0]), "kind": kind}
            if kind == "other_uuid":
                item["uuid"] = entry[1]
            else:
                item["name"] = entry[1]
                if kind != "renamed":
                    item["uuid"] = entry[2]
            evidence.append(item)
    shown = "; ".join(fragments[:SHOWN_SERVERS])
    if len(fragments) > SHOWN_SERVERS:
        shown += f"; and {len(fragments) - SHOWN_SERVERS} more"
    if uuidServers:
        captured = any(looksCaptured(entry[1], ourName) for entry in found.get("split_there", []))
        consequence = ("Sync created that copy: MISP matches organisations by UUID, and renames an unknown one whose "
                       "name is taken." if captured else
                       "MISP matches organisations by UUID: synced data creates a second organisation where the name "
                       "is taken by another UUID.")
        return Finding(
            "warning",
            f"Organisation “{ourName}” has another UUID on {where(uuidServers, names)}",
            f"{shown}. {consequence}",
            subject=uuid,
            evidence={"uuid": uuid, "name": ourName, "servers": evidence},
            action={"kind": "open_tab", "target": "organisations", "uuid": uuid},
        )
    return Finding(
        "info",
        f"Organisation “{ourName}” has another name on {where(nameServers, names)}",
        f"{shown}. Sync matches organisations by UUID and keeps each server's name.",
        subject=uuid,
        evidence={"uuid": uuid, "name": ourName, "servers": evidence},
        action={"kind": "open_tab", "target": "organisations", "uuid": uuid},
    )


@rule("organisation_mismatch", "sync")
def organisationMismatch(state, ctx):
    server = state.server
    if getattr(server, "fleet_id", None) is None:
        return
    from application.models import organisationDigests
    if not organisationDigests.hasDigest(server):
        return
    fleet = findingsFor(ctx, server)
    names = fleet["servers"]
    for uuid, found in sorted(fleet["findings"].get(server.id, {}).items(),
                              key=lambda item: ((item[1].get("name") or "").lower(), item[0])):
        finding = mismatchFinding(uuid, found, names)
        if finding is not None:
            yield finding
