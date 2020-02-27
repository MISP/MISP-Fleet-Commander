<template>
    <span
        v-if="submodules !== ''"
        :class="allValids === true ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', allValids === true ? 'fa-check' : 'fa-times']"></span>
        {{ invalidModuleNames }}
    </span>
</template>

<script>
export default {
    name: "submoduleStatus",
    props: {
        submodules: {}
    },
    computed: {
        invalidModuleNames() {
            if (typeof this.submodules === "string" || this.submodules === undefined) {
                return ""
            } else {
                let invalids = []
                for (const [modulesName, moduleState] of Object.entries(this.submodules)) {
                    if (moduleState !== 1) {
                        invalids.push(modulesName)
                    }
                }
                return invalids.join(", ")
            }
        },
        allValids() {
            return this.invalidModuleNames.length == 0
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