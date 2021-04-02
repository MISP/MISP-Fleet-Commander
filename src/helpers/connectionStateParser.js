export default {
    parse(connection) {
        let parsed = {
            variant: "danger",
            status: { message: "", variant: ""},
            compatibility: {message: "", variant: ""},
            post: { result: "", variant: "", success: false },
            localVersion: "",
            remoteVersion: "",
        }
        switch (connection.status) {
        case 1:
            parsed.variant = "success"
            parsed.status.variant = "success"
            parsed.status.message = "OK"
            parsed.compatibility.variant = "success"
            parsed.compatibility.message = "Compatible"
            parsed.localVersion = connection.local_version
            parsed.remoteVersion = connection.version
            if (connection.mismatch == "hotfix") {
                parsed.compatibility.variant = "warning"
            }
            if (connection.newer == "local") {
                if (connection.mismatch == "minor") {
                    parsed.compatibility.message = "Pull only"
                    parsed.compatibility.variant = "warning"
                    parsed.variant = "warning"
                } else if (connection.mismatch == "major") {
                    parsed.compatibility.message = "Incompatible"
                    parsed.compatibility.variant = "danger"
                    parsed.variant = "danger"
                }
            } else if (connection.newer == "remote") {
                if (connection.mismatch != "hotfix") {
                    parsed.compatibility.message = "Incompatible"
                    parsed.compatibility.variant = "danger"
                    parsed.variant = "danger"
                }
            } else if (connection.mismatch == "proposal") {
                parsed.compatibility.message = "Proposal pull disabled (remote version < v2.4.111)"
                parsed.compatibility.variant = "warning"
                parsed.variant = "warning"
            }
            if (connection.mismatch !== false && connection.mismatch != "proposal") {
                if (connection.newer == "remote") {
                    parsed.status.message = "Local instance outdated, update!"
                    parsed.variant = "danger"
                } else {
                    parsed.status.message = "Remote outdated, notify admin!"
                    parsed.variant = "danger"
                }
            }
            if (connection.post !== false) {
                parsed.post.variant = "danger"
                if (connection.post == 1) {
                    parsed.post.result = "Received sent package"
                    parsed.post.variant = "success"
                    parsed.post.success = true
                } else if (connection.post == 8) {
                    parsed.post.result = "Could not POST message"
                    parsed.post.variant = "danger"
                    parsed.variant = "danger"
                    parsed.post.success = false
                } else if (connection.post == 9) {
                    parsed.post.result = "Invalid body"
                    parsed.post.variant = "danger"
                    parsed.variant = "danger"
                    parsed.post.success = false
                } else if (connection.post == 10) {
                    parsed.post.result = "Invalid headers"
                    parsed.post.variant = "danger"
                    parsed.variant = "danger"
                    parsed.post.success = false
                } else {
                    parsed.post.result = "Remote too old for this test"
                }
            }
            break
        case 2:
            parsed.status.variant = "danger"
            parsed.status.message = "Server unreachable"
            break
        case 3:
            parsed.status.variant = "danger"
            parsed.status.message = "Unexpected error"
            break
        case 4:
            parsed.status.variant = "danger"
            parsed.status.message = "Authentication failed"
            break
        case 5:
            parsed.status.variant = "danger"
            parsed.status.message = "Password change required"
            break
        case 6:
            parsed.status.variant = "danger"
            parsed.status.message = "Terms not accepted"
            break
        case 7:
            parsed.variant = "danger"
            parsed.message = "Remote user is not a sync user"
            break
        case 8:
            parsed.variant = "warning"
            parsed.status.variant = "warning"
            parsed.status.message = "Syncing sightings only"
            break
        }
        return parsed
    },
    parseUser(connectionUser) {
        let parsed = { email: "", role_name: "", sync_flag: "", message: "", role_variant: ""}
        parsed.email = connectionUser["Email"] !== undefined ? connectionUser["Email"] : ""
        parsed.role_name = connectionUser["Role name"] !== undefined ? connectionUser["Role name"] : ""
        parsed.sync_flag = connectionUser["Sync flag"] !== undefined ? connectionUser["Sync flag"] : ""
        parsed.message = connectionUser.message !== undefined ? connectionUser.message : ""
        if (parsed.role_name == "admin") {
            parsed.role_variant = "success"
        } else if (parsed.role_name == "User") {
            parsed.role_variant = "danger"
        } else {
            parsed.role_variant = "danger"
        }
        return parsed
    }
}