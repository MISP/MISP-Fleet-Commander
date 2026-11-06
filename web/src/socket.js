import SocketIO from "socket.io-client"
import { baseurl } from "@/api/apiConfig"

// The backend refuses socket connections without a valid token. The `auth` callback runs on every
// (re)connection, so reconnecting after a login picks up the new token.
// Without an explicit base URL, socket.io connects to the page's origin.
export const socket = SocketIO(baseurl || undefined, {
    auth: (cb) => cb({ token: localStorage.getItem("access_token") }),
})

// Reconnect with the current token, e.g. after logging in as possibly another user
export function reconnectSocket() {
    socket.disconnect()
    socket.connect()
}

export function disconnectSocket() {
    socket.disconnect()
}
