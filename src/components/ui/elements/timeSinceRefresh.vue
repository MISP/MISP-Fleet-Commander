<template>
    <span class="mr-1 text-muted" style="cursor: auto;">
        <template v-if="validTimestamp !== false">
            <i class="far fa-clock mr-1"></i>
            <small class="align-middle">
                    {{ validTimestamp | moment(type) }}
            </small>
        </template>
    </span>
</template>

<script>
export default {
    name: "timeSinceRefresh",
    props: {
        timestamp: {
        },
        type: {
            default: "from"
        }
    },
    computed: {
        validTimestamp() {
            return Number.isInteger(this.timestamp) ? this.timestamp : false
        }
    }
}
</script>

<style scoped>

</style>