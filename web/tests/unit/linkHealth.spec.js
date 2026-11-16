import { describe, expect, it } from "vitest"
import {
    compareVersions, linkHealthRank, linkLevel, linkReasons, linkTestedAt, linkVersionReasons,
} from "@/helpers/linkHealth"

function link(level, extra = {}) {
    return { health: { level, reasons: [], ...extra } }
}

describe("link health", () => {
    it("treats a link without a known level as not tested", () => {
        expect(linkLevel(link("broken"))).toBe("broken")
        expect(linkLevel(link("bogus"))).toBe("unknown")
        expect(linkLevel({})).toBe("unknown")
        expect(linkLevel(null)).toBe("unknown")
    })

    it("sorts the most severe first, links in use before unused ones", () => {
        const links = [link("ok"), link("broken", { disabled: true }), link("degraded"), link("broken")]
        const sorted = links.slice().sort((a, b) => linkHealthRank(a) - linkHealthRank(b))
        expect(sorted.map(l => `${l.health.level}${l.health.disabled ? "-unused" : ""}`))
            .toEqual(["broken", "degraded", "ok", "broken-unused"])
    })

    it("lists the reasons that are not OK, and the ones about versions", () => {
        const reasons = [
            { level: "ok", code: "tested" },
            { level: "broken", code: "auth_failed" },
            { level: "degraded", code: "remote_outdated" },
        ]
        expect(linkReasons(link("broken", { reasons })).map(r => r.code)).toEqual(["auth_failed", "remote_outdated"])
        expect(linkVersionReasons(link("broken", { reasons })).map(r => r.code)).toEqual(["remote_outdated"])
    })

    it("reads the test time from the link or its health", () => {
        expect(linkTestedAt({ tested_at: 5, health: { tested_at: 3 } })).toBe(5)
        expect(linkTestedAt({ health: { tested_at: 3 } })).toBe(3)
        expect(linkTestedAt({})).toBe(null)
    })

    it("compares MISP versions numerically, missing ones last", () => {
        expect(compareVersions("2.5.9", "2.5.10")).toBeLessThan(0)
        expect(compareVersions("3.0.0", "2.5.51")).toBeGreaterThan(0)
        expect(compareVersions("3.0.0", "3.0.0")).toBe(0)
        expect(compareVersions("3.0.0", null)).toBe(-1)
        expect(compareVersions(null, "3.0.0")).toBe(1)
    })
})
