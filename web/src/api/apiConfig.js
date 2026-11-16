// The UI is served by the backend, so the API lives on the same origin by default.
// Set VUE_APP_API_BASE (e.g. in web/.env.local) to target a backend on another origin.
const baseurl = process.env.VUE_APP_API_BASE || ""

export {
    baseurl,
}
