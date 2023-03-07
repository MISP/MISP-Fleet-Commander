<template>
    <div>
        <div class="d-flex flex-row-reverse">
            <b-button-toolbar class="justify-content-end flex-nowrap w-50">
                <b-input-group size="sm" class="px-0 col" style="min-width: 150px;">
                    <b-form-input
                        v-model="filter"
                        debounce="200"
                        type="search"
                        id="filterInput"
                        placeholder="Type to Search"
                        class="border-bottom-0 rounded-top align-self-end"
                        style="border-radius: 0"
                    ></b-form-input>
                </b-input-group>
            </b-button-toolbar>
        </div>
        <b-table
            striped
            table-class="table-auto-hide-action mb-0"
            selected-variant="table-none"
            :fields="fields"
            :items="getRawFinalSettings"
            :filter="filter"
            @row-clicked="rowClickHandler"
        ></b-table>
        <SettingsAdministrationModal
            v-if="selectedItem !== null"
            ref="modal-settings-administration"
            :setting="selectedItem"
            :server="server"
        ></SettingsAdministrationModal>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import SettingsAdministrationModal from "@/views/servers/elements/mispRemoteAdministration/SettingsAdministrationModal.vue"

export default {
    name: "settingsAdministration",
    components: {
        SettingsAdministrationModal
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            filter: "",
            fields: [
                {key: "setting", },
                {key: "value", },
                {key: "description", },
                {key: "errorMessage", },
            ],
            tabs: [],
            //settings: [],
            selectedItem: null
        }
    },
    computed: {
        ...mapState({
            raw_final_settings: state => state.servers.raw_final_settings,
        }),
        getRawFinalSettings: function() {
            return Object.values(this.raw_final_settings[this.server.id])
        },
    },
    methods: {
        getVariantFromError(setting) {
            if (setting.error) {
                return this.getVariantFromLevel(setting.level)
            } else {
                return ""
            }
        },
        getVariantFromLevel(level) {
            if (level == 0) {
                return "danger"
            } else if (level == 1) {
                return "warning"
            } else if (level == 2) {
                return "success"
            } else {
                return "info"
            }
        },
        rowClickHandler(item) {
            this.selectedItem = item
            this.$nextTick(() => {
                this.$bvModal.show("modal-settings-administration")
            })
        }
    },
    created: function() {
        this.getRawFinalSettings.forEach(setting => {
            if (!this.tabs.includes(setting.tab)) {
                this.tabs.push(setting.tab)
            }
            setting._rowVariant = this.getVariantFromError(setting)
        })
    }
}
</script>
