import store from "@/store/index"
import { baseurl } from "./apiConfig"
import axios from "axios"

const urls = {
    login: `${baseurl}/login`,
}


function login(credential) {
    const url = `${urls.login}`
    return axios.post(url, credential)
        .then((response) => {
            return response.data
        })
}

export default {
    login,
}
