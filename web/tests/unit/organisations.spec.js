import { describe, expect, it } from "vitest"
import {
    attentionFlags, baselineRule, changedFields, domainLines, duplicateKey, fleetStanding, listText, matchesSearch,
    nearDuplicates, normalisedName, syncReasons, userCountOf, usersByOrganisation,
} from "@/helpers/organisations"

const CIRCL = {
    id: 9, uuid: "55f6ea5e-2c60-40e5-964f-47a8950d210f", name: "CIRCL", local: true, type: "CSIRT", sector: "",
    nationality: "Luxembourg", description: "", contacts: "", restricted_to_domain: ["circl.lu"], user_count: 3,
}

const COMPARISON = {
    compared: [{ id: 2, name: "misp-b" }, { id: 3, name: "misp-c" }, { id: 4, name: "misp-d" }],
    unavailable: [{ id: 5, name: "misp-e", error: "Timeout" }],
    organisations: {
        [CIRCL.uuid]: { same: [2], renamed: [[3, "Circl Lux"]], other_uuid: [] },
    },
}
const NAMES = { 2: "misp-b", 3: "misp-c", 4: "misp-d", 5: "misp-e" }

describe("names", () => {
    it("compares names like the backend", () => {
        expect(normalisedName("  Acme   Corp ")).toBe("acme corp")
    })

    it("finds likely duplicates on one server", () => {
        expect(duplicateKey("ACME Corp.")).toBe(duplicateKey("acme corp"))
        expect(duplicateKey("Société Générale")).toBe("societegenerale")
        const duplicates = nearDuplicates([
            { id: 1, name: "ACME Corp." }, { id: 2, name: "acme corp" }, { id: 3, name: "CIRCL" }, { id: 4, name: "!!" },
        ])
        expect(duplicates).toEqual({ 1: ["acme corp"], 2: ["ACME Corp."] })
    })
})

describe("standing in the fleet", () => {
    it("places every server once, problems first", () => {
        const standing = fleetStanding(CIRCL, COMPARISON, NAMES)
        expect(standing.rows.map(row => [row.name, row.state])).toEqual([
            ["misp-c", "renamed"], ["misp-d", "missing"], ["misp-e", "unknown"], ["misp-b", "same"],
        ])
        expect(standing.present).toBe(3)
        expect(standing.known).toBe(4)
        expect(standing.unknown).toBe(1)
        expect(standing.missingIds).toEqual([4])
        expect(standing.tone).toBe("warning")
    })

    it("is ok when present everywhere it could be compared, and waits for the comparison", () => {
        const comparison = { compared: [{ id: 2 }], unavailable: [], organisations: { [CIRCL.uuid]: { same: [2], renamed: [], other_uuid: [] } } }
        expect(fleetStanding(CIRCL, comparison).tone).toBe("ok")
        const absent = fleetStanding({ uuid: "x" }, comparison)
        expect(absent.tone).toBe("partial")
        expect(absent.missingIds).toEqual([2])
        expect(fleetStanding(CIRCL, null)).toBe(null)
    })

    it("ranks mismatches before the least present", () => {
        const mismatch = fleetStanding(CIRCL, COMPARISON, NAMES)
        const lonely = fleetStanding({ uuid: "x" }, COMPARISON, NAMES)
        expect(mismatch.rank).toBeLessThan(lonely.rank)
    })
})

describe("users and sync", () => {
    const users = [
        { User: { email: "sync@circl.lu" }, Organisation: { id: "9" }, Role: { perm_sync: true } },
        { User: { email: "analyst@circl.lu" }, Organisation: { id: "9" }, Role: { perm_sync: false } },
        { User: { email: "admin@admin.test" }, Organisation: { id: "1" }, Role: {} },
    ]

    it("counts users per organisation, MISP's count first", () => {
        const counts = usersByOrganisation(users)
        expect(counts).toEqual({ 9: 2, 1: 1 })
        expect(userCountOf(CIRCL, counts)).toBe(3)
        expect(userCountOf({ id: 1, user_count: null }, counts)).toBe(1)
        expect(userCountOf({ id: 7, user_count: null }, counts)).toBe(0)
        expect(userCountOf({ id: 7, user_count: null }, null)).toBe(null)
    })

    it("says why sync relies on an organisation", () => {
        const outgoing = [{ destination: { Server: { name: "Upstream" }, RemoteOrg: { uuid: CIRCL.uuid.toUpperCase() } } }]
        const incoming = [{ source: { id: 2 }, destination: { connectionUser: { email: "SYNC@circl.lu" } } }]
        expect(syncReasons(CIRCL, { outgoing, incoming, users, serverNames: NAMES }).map(reason => reason.code))
            .toEqual(["remote_org", "sync_user"])
        expect(syncReasons(CIRCL, { users })).toEqual([
            { code: "sync_permission", text: "1 user has the sync permission" },
        ])
        expect(syncReasons({ id: 1, uuid: "y" }, { users })).toEqual([])
    })

    it("names every sync connection an organisation represents once", () => {
        const outgoing = ["Training", "loopback", "dev"].map(name => ({
            destination: { Server: { name }, RemoteOrg: { uuid: CIRCL.uuid } },
        }))
        expect(syncReasons(CIRCL, { outgoing })).toEqual([{
            code: "remote_org", text: "Represents Training, loopback and dev in this server's sync connections",
        }])
        expect(listText(["a"])).toBe("a")
        expect(listText(["a", "b"])).toBe("a and b")
    })
})

describe("attention", () => {
    it("lists fleet mismatches, empty local organisations and duplicates", () => {
        const standing = fleetStanding(CIRCL, COMPARISON, NAMES)
        expect(attentionFlags(CIRCL, { standing, userCount: 3 }).map(flag => flag.text))
            .toEqual(["Named “Circl Lux” on misp-c"])
        expect(attentionFlags(CIRCL, { userCount: 0, duplicates: ["circl"] }).map(flag => flag.code))
            .toEqual(["no_users", "duplicate"])
        expect(attentionFlags({ ...CIRCL, local: false }, { userCount: 0 })).toEqual([])
        expect(attentionFlags(CIRCL, { userCount: null })).toEqual([])
    })
})

describe("forms", () => {
    it("searches the visible fields", () => {
        expect(matchesSearch(CIRCL, "lux")).toBe(true)
        expect(matchesSearch(CIRCL, "55F6EA5E")).toBe(true)
        expect(matchesSearch(CIRCL, "energy")).toBe(false)
        expect(matchesSearch(CIRCL, "  ")).toBe(true)
    })

    it("builds the baseline rule from the chosen checks", () => {
        expect(baselineRule(CIRCL, { checkType: true, checkSector: true, checkNationality: false }))
            .toEqual({ type: "organisation", key: CIRCL.uuid, expected: { name: "CIRCL", type: "CSIRT" } })
        expect(baselineRule(CIRCL, { checkLocal: true }).expected).toEqual({ name: "CIRCL", local: true })
    })

    it("sends only what changed", () => {
        const form = {
            name: "CIRCL", local: true, uuid: CIRCL.uuid.toUpperCase(), type: "CSIRT ", sector: "Security",
            nationality: "Luxembourg", description: "", contacts: "", restricted_to_domain: "circl.lu\n",
        }
        expect(changedFields(CIRCL, form)).toEqual({ sector: "Security" })
        expect(changedFields(CIRCL, { ...form, local: false, restricted_to_domain: "" }))
            .toEqual({ sector: "Security", local: false, restricted_to_domain: [] })
        expect(domainLines(" a.test, b.test\n\n c.test ")).toEqual(["a.test", "b.test", "c.test"])
    })
})
