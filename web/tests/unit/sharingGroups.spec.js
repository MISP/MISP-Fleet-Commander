import { describe, expect, it } from "vitest"
import {
    addPayload, attentionFlags, baselineRule, changeCount, differenceTexts, editPayload, extendCount, fleetStanding, formFrom,
    matchesSearch, namesBeforeRenames, namesText, nameTaken, nearDuplicateGroups, serversSummary,
} from "@/helpers/sharingGroups"

const ADMIN = { uuid: "5705de1d-143c-4637-959f-016e291a0265", name: "ADMIN", extend: true }
const CIRCL = { uuid: "55f6ea5e-2c60-40e5-964f-47a8950d210f", name: "CIRCL", extend: false }
const GROUP = {
    id: 42, uuid: "a1b2c3d4-0000-4000-8000-00000000f002", name: "Benelux", description: "BE, NL, LU",
    releasability: "TLP:AMBER", active: true, roaming: false, local: true,
    creator: { id: 1, uuid: ADMIN.uuid, name: "ADMIN" },
    members: [ADMIN, CIRCL],
    servers: [{ server_id: 0, name: "Local instance", all_orgs: false }, { server_id: 3, name: "Training", all_orgs: true }],
    editable: true, deletable: true,
}
const COMPARISON = {
    compared: [{ id: 2, name: "misp-b" }, { id: 3, name: "misp-c" }, { id: 4, name: "misp-d" }, { id: 6, name: "misp-f" }],
    unavailable: [{ id: 5, name: "misp-e", error: "Timeout" }],
    sharing_groups: {
        [GROUP.uuid]: {
            same: [2],
            differs: [{ server_id: 3, active: false, members_missing: [CIRCL.uuid], members_extra: [["x", "Other org"]] }],
            other_uuid: [[6, "ffffffff-0000-4000-8000-000000000001"]],
        },
    },
}
const NAMES = { 2: "misp-b", 3: "misp-c", 4: "misp-d", 5: "misp-e", 6: "misp-f" }

describe("fleet standing", () => {
    it("says what differs, with names", () => {
        expect(differenceTexts({ name: "Benelux 2", roaming: true }, GROUP)).toEqual(["named “Benelux 2”", "roaming there"])
        expect(differenceTexts(COMPARISON.sharing_groups[GROUP.uuid].differs[0], GROUP))
            .toEqual(["inactive there", "lacks 1 member: CIRCL", "also has Other org"])
        expect(namesText(["a", "b", "c", "d", "e", "f", "g"])).toBe("a, b, c, d, e and 2 more")
    })

    it("lists every server, worst first, and which ones a copy would change", () => {
        const standing = fleetStanding(GROUP, COMPARISON, NAMES)
        expect(standing.rows.map(row => [row.name, row.state])).toEqual([
            ["misp-c", "differs"], ["misp-f", "other_uuid"], ["misp-d", "missing"], ["misp-e", "unknown"], ["misp-b", "same"],
        ])
        expect(standing.present).toBe(3)
        expect(standing.known).toBe(5)
        expect(standing.tone).toBe("warning")
        expect(standing.mismatches).toBe(2)
        expect(standing.copyIds.sort()).toEqual([3, 4, 5])
        expect(standing.rows[0].lacking).toBe(1)
    })

    it("is ok when every server has the same group", () => {
        const comparison = { compared: [{ id: 2 }], unavailable: [], sharing_groups: { [GROUP.uuid]: { same: [2], differs: [], other_uuid: [] } } }
        const standing = fleetStanding(GROUP, comparison, NAMES)
        expect(standing.tone).toBe("ok")
        expect(standing.copyIds).toEqual([])
        expect(fleetStanding(GROUP, null)).toBe(null)
    })

    it("counts a group the comparison does not mention as missing everywhere", () => {
        const standing = fleetStanding(GROUP, { compared: [{ id: 2 }], unavailable: [], sharing_groups: {} }, NAMES)
        expect(standing.tone).toBe("partial")
        expect(standing.missingIds).toEqual([2])
    })
})

describe("table", () => {
    it("sums up the servers", () => {
        expect(serversSummary(GROUP)).toBe("Local instance + 1 server")
        expect(serversSummary({ ...GROUP, roaming: true })).toBe("Roaming")
        expect(serversSummary({ ...GROUP, servers: [GROUP.servers[0]] })).toBe("Local instance")
        expect(serversSummary({ ...GROUP, servers: [] })).toBe("No server")
        expect(serversSummary({ ...GROUP, servers: [GROUP.servers[1], { server_id: 4, name: "x", all_orgs: false }] })).toBe("2 servers")
        expect(extendCount(GROUP)).toBe(1)
    })

    it("searches names, texts, the creator and members", () => {
        expect(matchesSearch(GROUP, "amber")).toBe(true)
        expect(matchesSearch(GROUP, "circl")).toBe(true)
        expect(matchesSearch(GROUP, "a1b2c3d4")).toBe(true)
        expect(matchesSearch(GROUP, "nato")).toBe(false)
        expect(matchesSearch(GROUP, "  ")).toBe(true)
    })

    it("finds a name already taken, except by the group itself", () => {
        expect(nameTaken([GROUP], "  benelux ")).toBe(GROUP)
        expect(nameTaken([GROUP], "Benelux", GROUP.uuid)).toBe(null)
        expect(nameTaken([GROUP], "")).toBe(null)
    })
})

describe("baseline rule", () => {
    it("checks name, roaming and, by default, members, texts and the active flag", () => {
        expect(baselineRule(GROUP)).toEqual({
            type: "sharing_group",
            key: GROUP.uuid,
            expected: {
                name: "Benelux", roaming: false, active: true, releasability: "TLP:AMBER", description: "BE, NL, LU",
                members: [{ uuid: ADMIN.uuid, name: "ADMIN", extend: true }, { uuid: CIRCL.uuid, name: "CIRCL", extend: false }],
            },
        })
    })

    it("leaves out what is not chosen or empty", () => {
        const rule = baselineRule({ ...GROUP, description: "" }, { checkMembers: false, checkReleasability: false, checkActive: false })
        expect(rule.expected).toEqual({ name: "Benelux", roaming: false })
    })
})

describe("forms", () => {
    it("starts a new group with the API user's organisation and the Local instance", () => {
        const form = formFrom(null, { uuid: ADMIN.uuid.toUpperCase(), name: "ADMIN" })
        expect(form.members).toEqual([{ uuid: ADMIN.uuid, name: "ADMIN", extend: true }])
        expect(form.servers).toEqual([{ server_id: 0, name: "Local instance", all_orgs: false }])
        expect(formFrom(null).members).toEqual([])
    })

    it("adds with its members, and servers only when it does not roam", () => {
        const form = { ...formFrom(null, ADMIN), name: " NATO ", releasability: " " }
        expect(addPayload(form)).toEqual({
            name: "NATO", active: true, roaming: false,
            members: [{ uuid: ADMIN.uuid, name: "ADMIN", extend: true }],
            servers: [{ server_id: 0, all_orgs: false, name: "Local instance" }],
        })
        expect(addPayload({ ...form, roaming: true }).servers).toBeUndefined()
    })

    it("edits only what changed", () => {
        const form = formFrom(GROUP)
        expect(editPayload(GROUP, form)).toEqual({})
        form.description = "Benelux countries"
        form.active = false
        form.members[1].extend = true
        const changes = editPayload(GROUP, form)
        expect(changes).toEqual({
            description: "Benelux countries",
            active: false,
            members: [{ uuid: ADMIN.uuid, name: "ADMIN", extend: true }, { uuid: CIRCL.uuid, name: "CIRCL", extend: true }],
        })
        expect(changeCount(GROUP, changes)).toBe(3)
    })

    it("sends the whole server list when it changes, never for a roaming group", () => {
        const form = formFrom(GROUP)
        form.servers = form.servers.filter(server => server.server_id !== 3)
        form.servers[0].all_orgs = true
        const changes = editPayload(GROUP, form)
        expect(changes.servers).toEqual([{ server_id: 0, all_orgs: true, name: "Local instance" }])
        expect(changeCount(GROUP, changes)).toBe(2)
        expect(editPayload(GROUP, { ...form, roaming: true })).toEqual({ roaming: true })
    })
})

describe("attention flags", () => {
    const standing = fleetStanding(GROUP, COMPARISON, NAMES)
    const codes = flags => flags.map(flag => flag.code)

    it("strips MISP's rename suffixes one after the other", () => {
        expect(namesBeforeRenames("X_4821")).toEqual(["X"])
        expect(namesBeforeRenames("CIRCL + ORG_6 - [2]")).toEqual(["CIRCL + ORG_6", "CIRCL + ORG"])
        expect(namesBeforeRenames("Benelux")).toEqual([])
        expect(namesBeforeRenames("_2")).toEqual([])
    })

    it("groups look-alikes and renamed copies of a group still there", () => {
        const groups = [
            { uuid: "a", name: "X" }, { uuid: "b", name: "X_4821" }, { uuid: "c", name: "x. - [3]" },
            { uuid: "d", name: "Y" }, { uuid: "e", name: "y" },
            { uuid: "f", name: "ORG_6" }, { uuid: "g", name: "ORG_7" },
            { uuid: "h", name: "CIRCL + ORG_6" }, { uuid: "i", name: "CIRCL + ORG_6 - [2]" },
        ]
        expect(nearDuplicateGroups(groups)).toEqual({
            a: ["X_4821", "x. - [3]"], b: ["X", "x. - [3]"], c: ["X", "X_4821"],
            d: ["y"], e: ["Y"],
            h: ["CIRCL + ORG_6 - [2]"], i: ["CIRCL + ORG_6"],
        })
    })

    it("flags nothing for a healthy group", () => {
        expect(attentionFlags(GROUP)).toEqual([])
    })

    it("flags what differs in the fleet first", () => {
        const flags = attentionFlags(GROUP, { standing, duplicates: ["Benelux_2"] })
        expect(codes(flags)).toEqual(["other_uuid", "differs", "duplicate"])
        expect(flags[0]).toMatchObject({ tone: "warning", text: "Another UUID on misp-f" })
        expect(flags[1].text.startsWith("On misp-c: ")).toBe(true)
        expect(flags[2]).toMatchObject({ tone: "info", text: "Looks like “Benelux_2”" })
    })

    it("names every look-alike in one flag", () => {
        expect(attentionFlags(GROUP, { duplicates: ["A", "B"] })).toEqual([{ code: "duplicate", tone: "info", text: "Looks like “A” and “B”" }])
        expect(attentionFlags(GROUP, { duplicates: ["A", "B", "C"] })[0].text).toBe("Looks like “A”, “B” and 1 more")
    })

    it("flags a group without member, unless a server takes every organisation", () => {
        const empty = { ...GROUP, members: [], creator: null }
        expect(codes(attentionFlags(empty))).toEqual([])
        expect(codes(attentionFlags({ ...empty, servers: [{ server_id: 0, name: "Local instance", all_orgs: false }] }))).toEqual(["no_members"])
        expect(codes(attentionFlags({ ...empty, servers: [{ server_id: 0, name: "Local instance", all_orgs: true }] }))).toEqual([])
    })

    it("flags a creator that is not a member", () => {
        const group = { ...GROUP, creator: { id: 9, uuid: ADMIN.uuid.toUpperCase(), name: "ADMIN" }, members: [CIRCL] }
        expect(attentionFlags(group)[0]).toMatchObject({ code: "creator_not_member", text: "Its creator, ADMIN, is not a member" })
        expect(codes(attentionFlags({ ...group, members: [ADMIN] }))).toEqual([])
        const everyone = { ...group, servers: [{ server_id: 0, name: "Local instance", all_orgs: true }] }
        expect(codes(attentionFlags(everyone))).toEqual([])
        const nobody = { ...group, members: [], servers: [{ server_id: 0, name: "Local instance", all_orgs: false }] }
        expect(codes(attentionFlags(nobody))).toEqual(["no_members"])
    })

    it("flags an inactive group that still syncs", () => {
        const inactive = { ...GROUP, active: false }
        expect(codes(attentionFlags(inactive))).toEqual(["inactive_syncs"])
        expect(codes(attentionFlags({ ...inactive, servers: [{ server_id: 0, name: "Local instance", all_orgs: false }] }))).toEqual([])
        expect(codes(attentionFlags({ ...inactive, servers: [], roaming: false }))).toEqual(["inactive_syncs"])
        expect(codes(attentionFlags({ ...inactive, roaming: true, servers: [{ server_id: 0, name: "Local instance", all_orgs: false }] }))).toEqual(["inactive_syncs"])
    })
})
