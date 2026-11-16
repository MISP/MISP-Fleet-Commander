<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <div class="container">
            <div class="mt-1 mb-4 text-center">
                <img src="@/assets/logo.png" class="logo mb-3" alt="MISP Fleet Commander logo">
                <h5 class="text-muted fw-light">Manage your MISP communities easily</h5>
            </div>
            <div class="row">
                <div class="col">
                    <b-alert show variant="primary" dismissible>
                        <h5 class="alert-heading"><i class="fa fa-puzzle-piece"></i> Simplify server enrolment</h5>
                        <p class="mb-1">
                            With the MISP Fleet Commander browser extension (Chrome), open a page of a MISP instance and click the extension to add it to one of your fleets.
                        </p>
                        <a href="https://github.com/mokaddem/MISP-Fleet-Commander-Browser-Extension" target="_blank" rel="noopener">
                            <i class="fas fa-external-link-alt"></i>
                            MISP Fleet Commander Browser Extension
                        </a>
                    </b-alert>
                </div>
            </div>
            <div class="row">
                <div class="col">
                    <HealthOverview class="mt-2"></HealthOverview>
                </div>
            </div>
            <div class="row">
                <div class="col">
                    <Fleet class="mt-3"></Fleet>
                </div>
                <div class="col">
                    <PluginIndex class="mt-3"></PluginIndex>
                </div>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import Fleet from "@/views/fleets/index.vue"
import PluginIndex from "@/views/plugins/PluginIndex.vue"
import HealthOverview from "@/components/health/HealthOverview.vue"

export default {
    name: "TheHome",
    components: {
        Layout,
        Fleet,
        PluginIndex,
        HealthOverview,
    },
}
</script>

<style scoped>
    .logo {
        height: auto;
        max-width: 400px;
    }
    .page-container {
        padding-bottom: 3em;
    }
</style>
