<template>
    <span
        v-if="submodules !== '' && submodules !== undefined && hasSubmodules"
    >
        <span v-if="allValids" class="text-success fas fa-check"></span>
         <b-badge
            v-for="invalidModule in invalidModules"
            v-bind:key="invalidModule.name"
            variant="warning"
        >
            <strong>{{ invalidModule.name }}</strong>
            : <small>{{ invalidModule.error }}</small>
        </b-badge>
    </span>
</template>

<script>
export default {
    name: "submoduleStatus",
    props: {
        submodules: {}
    },
    computed: {
        hasSubmodules() {
            return Object.keys(this.submodules).length > 0
        },
        invalidModules() {
            const moduleErrors = {
                '0': 'OK',
                '1': 'System not enabled',
                '2': 'No modules found',
            }
            if (typeof this.submodules === "string" || this.submodules === undefined) {
                return ""
            } else {
                let invalids = []
                for (const [modulesName, moduleState] of Object.entries(this.submodules)) {
                    if (moduleState != 0) {
                        invalids.push({
                            name: modulesName,
                            error: moduleErrors[moduleState]
                        })
                    }
                }
                return invalids
            }
        },
        allValids() {
            return this.invalidModules.length == 0
        }
    },
    data: function() {
        return {}
    },
    methods: {
    }
}
</script>

<style scoped>

</style>
