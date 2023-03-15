export const websocketMixin = {
    data: function() {
        return {
            socket_ack_timeout: 10000
        }
    },
    sockets: {
    },
    methods: {
        serverRefresh: function (serverID) {
            this.$socket.emit('refresh_server', serverID);
        },
        fleetRefresh: function (fleetID) {
            this.$socket.emit("refresh_fleet", fleetID);
        },
        serverPing: function (serverID) {
            this.$socket.emit('ping_server', serverID);
        },
        fleetPing: function (fleetID) {
            this.$socket.emit("ping_fleet", fleetID);
        },

        // emit with ack
        serverPingWithAck: async function (serverID, callback) {
            try {
                const response = await socket.timeout(this.socket_ack_timeout).emitWithAck('ping_server', serverID);
                this.handleSuccess(response)
                if (callback !== undefined) {
                    callback(response)
                }
            } catch (err) {
                this.handleError(err)
            }
        },
        fleetPingWithAck: async function (fleetID, callback) {
            try {
                const response = await socket.timeout(this.socket_ack_timeout).emitWithAck('ping_fleet', fleetID);
                this.handleSuccess(response)
                if (callback !== undefined) {
                    callback(response)
                }
            } catch (err) {
                this.handleError(err)
            }
        },
        serverRefreshWithAck: async function (serverID, callback) {
            try {
                const response = await socket.timeout(this.socket_ack_timeout).emitWithAck('refresh_server', serverID);
                this.handleSuccess(response)
                if (callback !== undefined) {
                    callback(response)
                }
            } catch (err) {
                this.handleError(err)
            }
        },
        fleetRefreshWithAck: async function (fleetID, callback) {
            try {
                const response = await socket.timeout(this.socket_ack_timeout).emitWithAck('refresh_fleet', fleetID);
                this.handleSuccess(response)
                if (callback !== undefined) {
                    callback(response)
                }
            } catch (err) {
                this.handleError(err)
            }
        },

        handleSuccess(response) {
            this.$bvToast.toast('The replied in the given delay', {
                title: response,
                variant: 'success',
            })
        },
        handleError(err) {
            this.$bvToast.toast('The server did not acknowledge the event in the given delay', {
                title: err,
                variant: 'danger',
            })
        },
    }
};