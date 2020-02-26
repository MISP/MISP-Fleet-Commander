<template>
    <span
        v-if="submodules !== false"
        :class="allValids === true ? 'text-success' : 'text-danger'"
    >
        <span :class="['fas', allValids === true ? 'fa-check' : 'fa-times']"></span>
        {{ invalidModules }}
    </span>
</template>

<script>
export default {
    name: "submoduleStatus",
    props: {
        submodules: {
            default: function() {return false}
        }
    },
    computed: {
        invalidModules() {
            if (typeof this.submodules === "string") {
                return this.submodules
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