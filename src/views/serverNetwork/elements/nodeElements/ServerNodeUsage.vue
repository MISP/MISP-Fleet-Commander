<template>
    <div v-if="usage.stats">
        <table class="table table-sm table-borderless table-striped ">
            <tbody>
                <tr>
                    <td>Events</td>
                    <th>{{ usage.stats.event_count}}</th>
                </tr>
                <tr>
                    <td scope="row">Attributes</td>
                    <th>{{ usage.stats.attribute_count }}</th>
                </tr>
                <tr>
                    <td scope="row">Correlations</td>
                    <th>{{ usage.stats.correlation_count }}</th>
                </tr>
                <tr>
                    <td scope="row">Proposals active</td>
                    <th>{{ usage.stats.proposal_count }}</th>
                </tr>
                <tr>
                    <td scope="row">Users</td>
                    <th>{{ usage.stats.user_count }}</th>
                </tr>
                <tr>
                    <td scope="row">Organisations</td>
                    <th>{{ usage.stats.org_count }}</th>
                </tr>
            </tbody>
        </table>
        <simpleBarChart
            :data="dataOvertime"
        ></simpleBarChart>
        <span class="font-italic text-muted footer-comment">
            {{ server.comment }}
        </span>
    </div>
    <div v-else>
        <b-alert variant="danger" class="mb-0 mx-1" show>Cannot access usage data on this server</b-alert>
    </div>
</template>

<script>
import simpleBarChart from "@/components/ui/elements/simpleBarChart.vue"

export default {
    name: "ServerNodeUsage",
    components: {
        simpleBarChart
    },
    props: {
        server: {
            type: Object,
            required: true
        },
        usage: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            dataOvertime: [[0, 21], [1, 29], [2, 6], [3, 19], [4, 23], [5, 26], [6, 15], [7, 26], [8, 16], [9, 14], [10, 28], [11, 23], [12, 25], [13, 11], [14, 8], [15, 10], [16, 11], [17, 11], [18, 27], [19, 28]]
            // dataOvertime: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9], [10, 10], [11, 11], [12, 12], [13, 13], [14, 14], [15, 15], [16, 16], [17, 17], [18, 18], [19, 19]]
        }
    }
}
</script>

<style scoped>

</style>