import { refreshQuery, request } from "./remoteAdmin"

const base = "/server-management/organisations"

export default {
    // {server_id, fetched_at, cached, organisations}
    index(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}${refreshQuery(refresh)}`)
    },
    // {compared, unavailable, organisations: {uuid: {same, renamed, other_uuid}}}
    fleet(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}/fleet${refreshQuery(refresh)}`)
    },
    add(server_id, fields) {
        return request("post", `${base}/${server_id}/add`, fields)
    },
    edit(server_id, org_id, changes) {
        return request("post", `${base}/${server_id}/edit/${org_id}`, changes)
    },
    // 202 {job_id, job}
    copy(server_id, { uuid, server_ids, local }) {
        return request("post", `${base}/${server_id}/copy`, { uuid, server_ids, local })
    },
}
