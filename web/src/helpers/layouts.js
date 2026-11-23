// The layout a page is drawn in (the sidebar and navbar around it, or none) comes from its route, so that App draws
// it before the page is created. A page wrapped in <Layout name="…"> told App only once it was created, and App, its
// frame changing around it, created the page a second time: every request a page sends on mount went twice.

import VueRouter from "vue-router"

export const DEFAULT_LAYOUT = "LayoutDefault"
// Before the first route is resolved: nothing to draw a frame around yet (no navbar asking for data before login)
export const NO_LAYOUT = "div"

/** The layout of a route: the `meta.layout` of its deepest record that sets one, else the default */
export function layoutOf(route) {
    if (!route || route === VueRouter.START_LOCATION) {
        return NO_LAYOUT
    }
    const matched = route.matched || []
    for (let index = matched.length - 1; index >= 0; index--) {
        const layout = matched[index].meta && matched[index].meta.layout
        if (layout) {
            return layout
        }
    }
    return DEFAULT_LAYOUT
}
