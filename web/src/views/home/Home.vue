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
                    <b-alert show variant="primary">
                        <h5 class="alert-heading">Quick import!</h5>
                        Drag and Drop this link as a bookmark, Go to a MISP instance and click on the link.
                        <hr>
                        <b-alert show variant="light" class="d-flex justify-content-center mb-0 p-2">
                            <b-button :href="bookmarkJS" variant="primary">
                                <i class="fas fa-link"></i>
                                Import to MFC
                            </b-button>
                        </b-alert>
                    </b-alert>
                </div>
            </div>
            <div class="row">
                <div class="col">
                    <ServerGroup class="mt-3"></ServerGroup>
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
import ServerGroup from "@/views/serverGroups/index.vue"
import PluginIndex from "@/views/plugins/PluginIndex.vue"
import { baseurl } from "@/api/apiConfig"

export default {
    name: "TheHome",
    components: {
        Layout,
        ServerGroup,
        PluginIndex
    },
    data: function () {
        return {
            bookmarkJS: `javascript: (function () {if (window.bookmarkletMFC !== undefined) {bookmarkletMFC();} else {localStorage.setItem("MFM_token", "fmf_54e1836c_6225_4c50_9e68_40ded4c1ed21");document.body.appendChild(document.createElement("script")).src = "${baseurl}/static/bookmarklet.js?r=" + Math.floor(Math.random() * 999999999)}})()`,
        }
    }
}
</script>

<style scoped>
    .logo {
        height: auto;
        max-width: 400px;
    }
</style>
