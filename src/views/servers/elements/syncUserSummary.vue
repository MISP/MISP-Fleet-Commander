<template>
    <span>
        <b-badge
            :id="`user-badge-${randomid}`"
            ref="userbadge"
            :variant="getVariant"
            rounded
        >
            {{ user.role_name }}
        </b-badge>

        <b-popover
            custom-class="mw-25"
            :target="`user-badge-${randomid}`"
            :variant="user.role_color"
            triggers="hover" placement="auto" boundary="viewport"
        >
            <pre>{{ user.email }}</pre>
        </b-popover>
    </span>
</template>

<script>
export default {
    name: "syncUserSummary",
    props: {
        user: {
            type: Object,
            required: true
        }
    },
    computed: {
        getVariant() {
            return this.user.role_color
        },
    },
    data: function() {
        return {
            randomid: Math.ceil(Math.random()*1000000),
        }
    },
    methods: {
    }
}
</script>

<style scoped>

</style>