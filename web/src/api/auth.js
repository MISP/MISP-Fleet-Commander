import { baseurl } from "./apiConfig"
import axios from "axios"

const urls = {
    login: `${baseurl}/login`,
    changePassword: `${baseurl}/users/change-password`,
}


function login(credential) {
    const url = `${urls.login}`
    return axios.post(url, credential)
        .then((response) => {
            return response.data
        })
}

// Returns a new login token. Plain axios: the shared client would open the login modal on errors
function changePassword(currentPassword, newPassword) {
    const headers = {
        Authorization: `${localStorage.getItem("access_token_type")} ${localStorage.getItem("access_token")}`,
    }
    return axios.post(urls.changePassword, { current_password: currentPassword, new_password: newPassword }, { headers })
        .then((response) => {
            return response.data
        })
}

export default {
    login,
    changePassword,
}
