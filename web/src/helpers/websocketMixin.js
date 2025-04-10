export const websocketMixin = {
    data: function() {
        return {
            socket_ack_timeout: 10000
        }
    },
    sockets: {
    },
    methods: {
        wsServerRefresh: function (serverID) {
            this.$socket.emit('refresh_server', serverID);
        },
        wsFleetRefresh: function (fleetID) {
            this.$socket.emit("refresh_fleet", fleetID);
        },
        wsServerConnectionTest: function (serverID) {
            this.$socket.emit('server_connection_test', serverID);
        },
        wsFleetConnectionTest: function (fleetID) {
            this.$socket.emit('fleet_connection_test', fleetID);
        },
        wsServerPing: function (serverID) {
            this.$socket.emit('ping_server', serverID);
        },
        wsFleetPing: function (fleetID) {
            this.$socket.emit("ping_fleet", fleetID);
        },
        wsServerGraphsRefresh: function (serverID) {
            this.$socket.emit('refresh_server_graphs', serverID);
        },

        // emit with ack
        wsServerRefreshWithAck: async function (serverID, callback) {
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
        wsFleetRefreshWithAck: async function (fleetID, callback) {
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