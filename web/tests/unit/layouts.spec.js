import { describe, expect, it } from "vitest"
import VueRouter from "vue-router"
import { DEFAULT_LAYOUT, layoutOf, NO_LAYOUT } from "@/helpers/layouts"

// A route as vue-router gives it: its matched records, root first
const route = (...metas) => ({ matched: metas.map((meta) => ({ meta })) })

describe("layoutOf", () => {
    it("takes the deepest record's layout, else the default", () => {
        expect(layoutOf(route({}, { layout: "LayoutStretch" }))).toBe("LayoutStretch")
        expect(layoutOf(route({ layout: "LayoutStretch" }, { requiresFleet: true }))).toBe("LayoutStretch")
        expect(layoutOf(route({ layout: "LayoutStretch" }, { layout: "LayoutLogin" }))).toBe("LayoutLogin")
        expect(layoutOf(route({}, {}))).toBe(DEFAULT_LAYOUT)
        expect(layoutOf({ matched: [{}] })).toBe(DEFAULT_LAYOUT)
    })

    it("draws no frame before the first route is resolved, and the default one for an unknown address", () => {
        expect(layoutOf(VueRouter.START_LOCATION)).toBe(NO_LAYOUT)
        expect(layoutOf(null)).toBe(NO_LAYOUT)
        expect(layoutOf(route())).toBe(DEFAULT_LAYOUT)
    })
})
