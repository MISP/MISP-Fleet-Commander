<template>
    <div class="d-flex flex-column container">
        <div class="text-muted">
            <i class="fa fa-envelope fa-fw"></i> Events: {{ events.length }}
        </div>
        <div>
            <span v-for="entry in events" :key="entry.id" @click="setSelectedEntry(entry)" v-b-modal="`modal-entry-data-${server.id}`">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted">
            <i class="fa fa-cube fa-fw"></i> Attributes: {{ attributes.length }}
        </div>
        <div>
            <span v-for="entry in attributes" :key="entry.id" @click="setSelectedEntry(entry)" v-b-modal="`modal-entry-data-${server.id}`">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-users fa-fw"></i> Sharing Groups: {{ sharinggroups.length }}
        </div>
        <div>
            <span v-for="entry in sharinggroups" :key="entry.id" @click="setSelectedEntry(entry)" v-b-modal="`modal-entry-data-${server.id}`">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-eye fa-fw"></i> Sightings: {{ sightings.length }}
        </div>
        <div>
            <span v-for="entry in sightings" :key="entry.id" @click="setSelectedEntry(entry)" v-b-modal="`modal-entry-data-${server.id}`">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>
        <div class="text-muted mt-1">
            <i class="fa fa-sticky-note fa-fw"></i> Analyst Data: {{ analystdata.length }}
        </div>
        <div>
            <span v-for="entry in analystdata" :key="entry.id" @click="setSelectedEntry(entry)" v-b-modal="`modal-entry-data-${server.id}`">
                <AvatarActions :server_id="server.id" :pinlist_id="entry.pinlist_id" :pinlist_model="entry.model" width="32" height="32"></AvatarActions>
            </span>
        </div>

        <b-modal
            :id="`modal-entry-data-${server.id}`"
            :title="`Pinned entry for \`${selectedEntryModel}\` in server ${server.id}`"
            size="lg"
            scrollable
        >
            <b-button
                variant="link"
                @click="toggleRulesTreeMode"
            >
                <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
            </b-button>
            <jsonViewer 
                :tree="rulesTreeMode"
                :item="sortedSelectedEntryData"
                rootKeyName="Data"
                :open="true"
            ></jsonViewer>
        </b-modal>
    </div>
</template>

<script>
import Vue from "vue"
import { mapGetters } from "vuex"
import AvatarActions from "@/views/strategicView/elements/avatar/AvatarActions.vue";
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"


export default {
    name: "ServerNodePinnedContent",
    components: {
        AvatarActions,
        jsonViewer,
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            selectedEntry: {},
            rulesTreeMode: true,
            modalActive: true,
        }
    },
    computed: {
        ...mapGetters({
            entriesByServerID: "pinlists/entriesByServerID",
            pinnedByID: "pinlists/pinnedByID",
        }),
        entries() {
            let tmp =  this.entriesByServerID[this.server.id] || []
            tmp.map(e => {
                e.model = this.pinnedByID[e.pinlist_id].model
                return e
            })
            return tmp
        },
        events() {
            return this.entries.filter(e => e.model == 'event')
        },
        attributes() {
            return this.entries.filter(e => e.model == 'attribute')
        },
        sharinggroups() {
            return this.entries.filter(e => e.model == 'sharinggroup')
        },
        sightings() {
            return this.entries.filter(e => e.model == 'sighting')
        },
        analystdata() {
            return this.entries.filter(e => e.model == 'analystdata')
        },
        selectedEntryModel() {
            return this.selectedEntry.model ? this.selectedEntry.model : '?'
        },
        selectedEntryData() {
            if (!this.selectedEntry.data) {
                return {}
            }
            const keyContainingData = Object.keys(this.selectedEntry.data).filter((k) => k != 'server_id' && k != 'timestamp')[0]
            return this.selectedEntry.data[keyContainingData]
        },
        sortedSelectedEntryData() {
            const sortedObject = {}
            const sortedKeys = Object.keys(this.selectedEntryData).sort((a, b) => {
                const isALower = /^[a-z]/.test(a);
                const isBLower = /^[a-z]/.test(b);
                
                if (isALower && !isBLower) return -1;
                if (!isALower && isBLower) return 1;
                return a.localeCompare(b);
            })
            sortedKeys.forEach((k) => {
                sortedObject[k] = this.selectedEntryData[k]
            })
            console.log(sortedKeys);
            
            return sortedObject
        },
    },
    methods: {
        toggleRulesTreeMode() {
            this.rulesTreeMode = !this.rulesTreeMode
        },
        setSelectedEntry(entry) {
            this.selectedEntry = entry
        },
    },
}
</script>

<style scoped>
.container {
    min-height: 180px;
}

</style>