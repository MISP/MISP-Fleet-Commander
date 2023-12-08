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
        v-else-if="scope === 'connections'"
        :class="['fas', 'fa-network-wired']"
    ></i>
    <i
        v-else-if="scope === 'strategicView'"
        :class="['fas', 'fa-satellite-dish']"
    ></i>
    <i
        v-else-if="scope === 'users'"
        :class="['fas', 'fa-user-astronaut']"
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
                return ["", "home", "servers", "connections", "strategicView", "users"].indexOf(value) !== -1
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
