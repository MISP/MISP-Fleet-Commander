<template>
    <div>
        <b-table-simple
            striped small
            class="mb-0"
            :bordered="false"
            :borderless="true"
            :outlined="false"
        >
            <b-tbody>
                <b-tr>
                    <b-th>Name</b-th>
                    <b-td>{{ server.name }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>URL</b-th>
                    <b-td>{{ server.url }}</b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </div>
</template>

<script>
export default {
    name: "ServerNodeStats",
    props: {
        server: {
            type: Object,
            required: true
        }
    }
}
</script>

<style scoped>

</style>