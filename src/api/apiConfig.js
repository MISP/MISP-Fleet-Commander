import store from "@/store/index"

const baseurl = "http://127.0.0.1:5000"

const appendGroupIDIfDefined = (url) => {
    if (store.getters["serverGroups/selectedServerGroup"] !== null) {
        const groupID = store.getters["serverGroups/selectedServerGroup"].id
        url += `/${groupID}`
    }
    return url
}

export {
    baseurl,
    appendGroupIDIfDefined,
}
