<template>
    <div :class="['server-picker', { 'is-filtered': value !== null }]">
        <label class="picker-field" :title="value === null ? 'Show one server only' : `Showing ${selectedName} only`">
            <i class="fas fa-server picker-icon" aria-hidden="true"></i>
            <span class="sr-only">Servers shown</span>
            <select v-model="selected" class="picker-select">
                <option value="">All servers</option>
                <option v-for="server in servers" :key="server.id" :value="String(server.id)">{{ server.name }}</option>
            </select>
            <i class="fas fa-chevron-down picker-caret" aria-hidden="true"></i>
        </label>
        <button
            v-if="value !== null"
            type="button"
            class="picker-clear"
            title="Show all servers"
            @click="pick('')"
        >
            <i class="fas fa-times" aria-hidden="true"></i><span class="sr-only">Show all servers</span>
        </button>
    </div>
</template>

<script>
// Which servers of the fleet the Usage tab shows: all of them, or one. `v-model` holds the server ID or null
export default {
    name: "ServerPicker",
    props: {
        value: { type: Number, default: null },
        // `[{ id, name }]`, in the order to list them
        servers: { type: Array, required: true },
    },
    computed: {
        // Through `v-model`: a plain `:value` is set before the options exist, and a picked server opened from a
        // link would show as "All servers"
        selected: {
            get() {
                return this.value === null ? "" : String(this.value)
            },
            set(text) {
                this.pick(text)
            },
        },
        selectedName() {
            const server = this.servers.find((item) => item.id === this.value)
            return server ? server.name : "one server"
        },
    },
    methods: {
        pick(text) {
            const id = text === "" ? null : Number.parseInt(text, 10)
            if (id !== this.value) {
                this.$emit("input", id)
            }
        },
    },
}
</script>

<style scoped>
/* Same height and frame as the range picker beside it */
.server-picker {
    display: inline-flex;
    align-items: stretch;
    max-width: 100%;
    padding: 2px;
    border: 1px solid #d5dbe3;
    border-radius: 6px;
    background: #f4f6f9;
}

.picker-field {
    position: relative;
    display: inline-flex;
    align-items: center;
    min-width: 0;
    margin: 0;
    border-radius: 4px;
}

.picker-icon {
    position: absolute;
    left: 0.55rem;
    color: #9aa1a7;
    font-size: 0.75rem;
    pointer-events: none;
}

.picker-caret {
    position: absolute;
    right: 0.5rem;
    color: #6c757d;
    font-size: 0.625rem;
    pointer-events: none;
}

.picker-select {
    max-width: 16rem;
    min-width: 0;
    padding: 0.2rem 1.6rem 0.2rem 1.7rem;
    border: 0;
    border-radius: 4px;
    background: none;
    color: #52514e;
    font-size: 0.8125rem;
    font-weight: 500;
    line-height: 1.4;
    text-overflow: ellipsis;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
}

.picker-select:hover {
    color: #212d40;
    background: rgba(255, 255, 255, 0.7);
}

.picker-select:focus {
    outline: none;
}

.picker-select:focus-visible {
    outline: 2px solid rgba(41, 120, 160, 0.5);
    outline-offset: 1px;
}

/* One server picked: the whole tab is about it, the picker says so like a selected range */
.is-filtered .picker-select {
    background: #fff;
    color: #212d40;
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.15);
}

.is-filtered .picker-icon {
    color: #2978a0;
}

.picker-clear {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.6rem;
    margin-left: 2px;
    padding: 0;
    border: 0;
    border-radius: 4px;
    background: none;
    color: #6c757d;
    font-size: 0.75rem;
}

.picker-clear:hover {
    color: #212d40;
    background: rgba(255, 255, 255, 0.7);
}

.picker-clear:focus-visible {
    outline: 2px solid rgba(41, 120, 160, 0.5);
    outline-offset: 1px;
}

@media (max-width: 480px) {
    .picker-select {
        max-width: 14rem;
    }
}
</style>
