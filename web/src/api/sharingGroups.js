import { refreshQuery, request } from "./remoteAdmin"

const base = "/server-management/sharing-groups"

export default {
    // {server_id, fetched_at, cached, sharing_groups}
    index(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}${refreshQuery(refresh)}`)
    },
    // {compared, unavailable, sharing_groups: {uuid: {same, differs, other_uuid}}}
    fleet(server_id, { refresh = false } = {}) {
        return request("get", `${base}/${server_id}/fleet${refreshQuery(refresh)}`)
    },
    // {group_id, events}: events shared with the group (null when MISP does not say)
    usage(server_id, group_id) {
        return request("get", `${base}/${server_id}/usage/${group_id}`)
    },
    // {SharingGroup, done, failed}
    add(server_id, fields) {
        return request("post", `${base}/${server_id}/add`, fields)
    },
    edit(server_id, uuid, changes) {
        return request("post", `${base}/${server_id}/edit/${uuid}`, changes)
    },
    remove(server_id, uuid, name) {
        return request("post", `${base}/${server_id}/delete/${uuid}`, { name })
    },
    // 202 {job_id, job}
    copy(server_id, { uuid, server_ids }) {
        return request("post", `${base}/${server_id}/copy`, { uuid, server_ids })
    },
}
