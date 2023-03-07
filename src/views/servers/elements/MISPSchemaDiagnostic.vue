<template>
    <div>
        <div class="accordion" role="tablist">
            <b-card no-body class="mb-1">
                <b-card-header header-tag="header" class="p-1" role="tab">
                    <b-button block v-b-toggle.accordion-diagnostic variant="primary">Quick diagnostic</b-button>
                </b-card-header>
                <b-collapse id="accordion-diagnostic" visible accordion="my-accordion" role="tabpanel">
                    <b-card-body>
                        <b-badge :variant="schemaDiagnostic.update_locked ? 'danger': 'success'">
                            Updates are {{ !schemaDiagnostic.update_locked ? 'not' : '' }} locked
                            <i :class="['fas', !schemaDiagnostic.update_locked ? 'fa-check' : 'fa-times']"></i>
                        </b-badge>
                        <div v-if="getCriticalRows.length == 0" >
                            <b-badge variant="success">
                                Diagnostic: no errors
                                <i class="fas fa-check"></i>
                            </b-badge>
                        </div>
                        <div v-else>
                            <b-badge variant="danger" class="mb-2">
                                Diagnostic: errors
                                <i class="fas fa-times"></i>
                            </b-badge>
                            <b-table-lite
                                striped
                                table-class="table-no-select mb-0"
                                :fields="getDiagnosticFields"
                                :items="getCriticalRows"
                            ></b-table-lite>
                        </div>
                    </b-card-body>
                </b-collapse>
            </b-card>

            <b-card no-body class="mb-1">
                <b-card-header header-tag="header" class="p-1" role="tab">
                    <b-button block v-b-toggle.accordion-json variant="primary">JSON</b-button>
                </b-card-header>
                <b-collapse id="accordion-json" accordion="my-accordion" role="tabpanel">
                    <b-card-body>
                        <jsonViewer
                            :item="schemaDiagnostic"
                            rootKeyName="Database schema diagnostic"
                            :open="true"
                        ></jsonViewer>
                    </b-card-body>
                </b-collapse>
            </b-card>
        </div>
    </div>
</template>

<script>
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"

export default {
    name: "MISPSchemaDiagnostic",
    components: {
        jsonViewer
    },
    props: {
        schemaDiagnostic: {
            required: true,
            type: Object
        }
    },
    data: function() {
        return {
            getDiagnosticFields: [
                "table_name",
                "column_name",
                "error_type",
                "description",
            ]
        }
    },
    computed: {
        getCriticalRows() {
            let criticalRows = []
            const dbDiagnostic = this.schemaDiagnostic.diagnostic
            for (const table in dbDiagnostic) {
                if (Object.hasOwnProperty.call(dbDiagnostic, table)) {
                    const tableStatus = dbDiagnostic[table]
                    tableStatus.forEach(row => {
                        if (row.is_critical) {
                            criticalRows.push({table_name: table, ...row})
                        }
                    })
                }
            }
            return criticalRows
        }
    },
    methods: {
    }
}
</script>

<style scoped>

</style>