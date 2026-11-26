<template>
    <section class="usage-section fqw" aria-labelledby="fleet-usage-queries-title">
        <header class="section-head">
            <h3 id="fleet-usage-queries-title" class="section-title">Saved queries</h3>
            <span class="section-note">{{ serverId === null ? "what this fleet's servers answer" : `what ${serverName} answers` }} to your saved queries · {{ rangePhrase }}</span>
            <b-button
                v-if="widgets.length > 0"
                size="sm"
                variant="outline-primary"
                class="fqw-add"
                :disabled="widgets.length >= max"
                :title="widgets.length >= max ? `A fleet holds at most ${max} widgets` : null"
                @click="openAdd"
            >
                <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add
            </b-button>
        </header>

        <div v-if="message" class="fqw-message" role="alert">
            <i class="fas fa-fw fa-exclamation-triangle" aria-hidden="true"></i>
            <span>
                {{ message }}
                <button v-if="!loaded" type="button" class="btn btn-link fqw-retry" @click="load">Try again</button>
            </span>
        </div>

        <div v-if="!loaded && loading" class="fqw-skeleton" aria-hidden="true"></div>

        <div v-else-if="loaded && widgets.length === 0" class="fqw-empty">
            <div class="fqw-empty-art" aria-hidden="true">
                <svg width="64" height="40" viewBox="0 0 64 40">
                    <path d="M2 32 L14 26 L24 29 L36 16 L46 20 L62 6" class="fqw-empty-line" />
                    <path d="M2 36 H62" class="fqw-empty-axis" />
                </svg>
            </div>
            <div class="fqw-empty-text">
                <p class="fqw-empty-title">Follow a saved query here</p>
                <p class="fqw-empty-body">
                    See how what this fleet's servers answer to one of your saved queries moves over time: summed over
                    the fleet, or server by server against its expectation.
                </p>
                <b-button size="sm" variant="primary" @click="openAdd">
                    <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add a saved query
                </b-button>
            </div>
        </div>

        <transition-group v-else tag="div" name="fqw-move" class="fqw-grid">
            <QueryWidget
                v-for="(widget, index) in widgets"
                :key="widget.id"
                :fleet-id="fleetId"
                :server-id="serverId"
                :server-name="serverName"
                :widget="widget"
                :range-key="rangeKey"
                :range-phrase="rangePhrase"
                :refresh-key="refreshKey"
                :span="spans[widget.id]"
                :first="index === 0"
                :last="index === widgets.length - 1"
                :busy="Boolean(busy[widget.id])"
                @display="setDisplay(widget, $event)"
                @move="move(widget, $event)"
                @remove="remove(widget)"
            ></QueryWidget>
        </transition-group>

        <AddQueryWidgetModal :modal-id="modalId" :fleet-id="fleetId" :server-id="serverId" @added="onAdded"></AddQueryWidgetModal>
    </section>
</template>

<script>
import api from "@/api/usageWidgets"
import AddQueryWidgetModal from "@/components/usage/AddQueryWidgetModal.vue"
import QueryWidget from "@/components/usage/QueryWidget.vue"
import { movedIds, widgetSpans } from "@/helpers/usageWidgets"

// After a query run ends, the time its answers take to be kept before the widgets read them again
const RELOAD_DELAY = 800

// The saved queries followed on a fleet's Usage tab, in their owner's order; drawn for one server of the fleet when
// the tab is limited to it
export default {
    name: "FleetQueryWidgets",
    components: { AddQueryWidgetModal, QueryWidget },
    props: {
        fleetId: { type: Number, required: true },
        // The server the tab is limited to, or null for all of them
        serverId: { type: Number, default: null },
        serverName: { type: String, default: "" },
        rangeKey: { type: String, required: true },
        rangePhrase: { type: String, default: "" },
    },
    data() {
        return {
            widgets: [],
            max: 20,
            loaded: false,
            loading: false,
            message: "",
            busy: {},
            refreshKey: 0,
        }
    },
    computed: {
        modalId() {
            return `fqw-add-${this.fleetId}`
        },
        spans() {
            return widgetSpans(this.widgets)
        },
    },
    watch: {
        fleetId() {
            this.widgets = []
            this.loaded = false
            this.load()
        },
        serverId() {
            // The servers' last answers and problems, for that server alone; each widget reloads its points
            this.load()
        },
    },
    created() {
        this.load()
        this.unsubscribe = this.$store.subscribeAction({ after: this.onJobEvent })
    },
    beforeDestroy() {
        if (this.unsubscribe) {
            this.unsubscribe()
        }
        clearTimeout(this.reloadTimer)
    },
    methods: {
        load() {
            const fleetId = this.fleetId
            const serverId = this.serverId
            this.loading = true
            return api.list(fleetId, serverId).then((answer) => {
                if (fleetId === this.fleetId && serverId === this.serverId) {
                    this.widgets = answer.widgets || []
                    this.max = answer.max || this.max
                    this.loaded = true
                    this.message = ""
                }
            }).catch((error) => {
                if (fleetId === this.fleetId && serverId === this.serverId) {
                    this.message = `Could not load the saved queries followed here: ${error}`
                }
            }).finally(() => {
                if (fleetId === this.fleetId && serverId === this.serverId) {
                    this.loading = false
                }
            })
        },
        onJobEvent(action) {
            const payload = action.payload || {}
            if (action.type === "jobs/SOCKET_JOB_DONE" && payload.kind === "mispql_query" && this.widgets.length > 0) {
                clearTimeout(this.reloadTimer)
                this.reloadTimer = setTimeout(() => {
                    // The servers' last answers, then each widget's points
                    this.load().then(() => {
                        this.refreshKey += 1
                    })
                }, RELOAD_DELAY)
            }
        },
        openAdd() {
            this.$bvModal.show(this.modalId)
        },
        onAdded(widget) {
            this.widgets = this.widgets.concat([widget])
        },
        replace(widget) {
            this.widgets = this.widgets.map((item) => (item.id === widget.id ? widget : item))
        },
        withBusy(widget, change) {
            this.$set(this.busy, widget.id, true)
            this.message = ""
            return change().then((answer) => {
                if (!answer.ok) {
                    this.message = answer.message
                    return this.load().then(() => null)
                }
                return answer
            }).catch((error) => {
                this.message = String(error)
                return null
            }).finally(() => {
                this.$delete(this.busy, widget.id)
            })
        },
        setDisplay(widget, display) {
            if (widget.display === display) {
                return
            }
            // Both displays come from the history the widget holds: switch at once
            this.replace(Object.assign({}, widget, { display }))
            this.withBusy(widget, () => api.setDisplay(this.fleetId, widget.id, display, this.serverId)).then((answer) => {
                if (answer) {
                    this.replace(answer)
                }
            })
        },
        move(widget, delta) {
            const ids = movedIds(this.widgets.map((item) => item.id), widget.id, delta)
            const byId = new Map(this.widgets.map((item) => [item.id, item]))
            this.widgets = ids.map((id) => byId.get(id))
            this.withBusy(widget, () => api.reorder(this.fleetId, ids))
        },
        remove(widget) {
            const kept = this.widgets.filter((item) => item.id !== widget.id)
            this.widgets = kept
            this.withBusy(widget, () => api.remove(this.fleetId, widget.id))
        },
    },
}
</script>

<style scoped src="@/components/ui/charts/usageLayout.css"></style>

<style scoped>
.fqw-add {
    margin-left: auto;
    align-self: center;
}

.fqw-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.75rem;
}

@media (min-width: 1100px) {
    .fqw-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .fqw-grid > .is-full {
        grid-column: 1 / -1;
    }
}

.fqw-move-move {
    transition: transform 0.2s ease;
}

@media (prefers-reduced-motion: reduce) {
    .fqw-move-move {
        transition: none;
    }
}

.fqw-message {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    margin-bottom: 0.6rem;
    padding: 0.55rem 0.75rem;
    border: 1px solid #e4e7ec;
    border-left: 3px solid var(--health-critical);
    border-radius: 4px;
    background: var(--health-critical-tint);
    font-size: 0.8125rem;
}

.fqw-message > i {
    color: var(--health-critical-ink);
}

.fqw-retry {
    padding: 0;
    margin-left: 0.3rem;
    font-size: inherit;
    font-weight: 600;
    vertical-align: baseline;
}

.fqw-skeleton {
    height: 9rem;
    border-radius: 6px;
    background: linear-gradient(90deg, #f0f2f5 25%, #e6e9ee 37%, #f0f2f5 63%);
    background-size: 400% 100%;
    animation: shimmer 1.4s ease infinite;
}

.fqw-empty {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 0.9rem 1rem;
    border: 1px dashed #d5dbe3;
    border-radius: 6px;
    background: #fafbfc;
}

.fqw-empty-art {
    flex: none;
    padding-top: 0.15rem;
}

.fqw-empty-line {
    fill: none;
    stroke: #9aa6b5;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.fqw-empty-axis {
    stroke: #d5dbe3;
    stroke-width: 1.5;
}

.fqw-empty-title {
    margin: 0 0 0.2rem;
    font-weight: 600;
    color: #212d40;
}

.fqw-empty-body {
    margin: 0 0 0.6rem;
    max-width: 44rem;
    color: #52514e;
    font-size: 0.8125rem;
    line-height: 1.5;
}

@media (max-width: 480px) {
    .fqw-empty-art {
        display: none;
    }
}
</style>
