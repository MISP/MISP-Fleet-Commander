<template>
    <i
        v-if="scope === 'home'"
        :class="['fa', 'fa-home']"
    ></i>
    <i
        v-else-if="scope === 'servers'"
        :class="['fa', 'fa-server']"
    ></i>
    <i
        v-else-if="scope === 'serverNetwork'"
        :class="['fa', 'fa-project-diagram']"
    ></i>
     <i
        v-else
        :class="['fa', 'fa-question']"
    ></i>
</template>

<script>
export default {
    name: "iconForScope",
    props: {
        scope: {
            type: String,
            required: true,
            validator: function (value) {
                return ["", "home", "servers", "serverNetwork"].indexOf(value) !== -1
            }
        },
        forceBlack: {
            type: Boolean,
            required: false,
            default: false
        }
    }
}
</script>

<style scoped>
</style>
