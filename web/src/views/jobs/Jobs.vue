<template>
<Layout name="LayoutDefault">
    <div class="page-container jobs-page">
        <header class="jobs-header">
            <h1 class="jobs-title">Jobs</h1>
            <p class="jobs-lede">
                Every change sent to MISP servers from here, with who started it, its parameters and its result on
                each server. Jobs are kept {{ retentionLabel }}.
            </p>
        </header>
        <JobList global></JobList>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import JobList from "@/components/jobs/JobList.vue"

export default {
    name: "JobsIndex",
    components: {
        Layout,
        JobList,
    },
    computed: {
        retentionLabel() {
            const days = Number(this.$store.getters["settings/settingValues"].job_retention_days) || null
            return days ? `for ${days} day${days === 1 ? "" : "s"}` : "for the retention period set in the settings"
        },
    },
}
</script>

<style scoped>
.jobs-page {
    max-width: 1180px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.jobs-header {
    margin-bottom: 1rem;
}

.jobs-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0;
}

.jobs-lede {
    color: #5a6270;
    margin: 0.25rem 0 0;
    max-width: 720px;
    font-size: 0.92rem;
}
</style>
