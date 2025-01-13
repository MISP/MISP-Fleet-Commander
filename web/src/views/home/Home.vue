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
                        <h5 class="alert-heading text-center">Simplify server enrolment</h5>
                        <div class="row">
                            <div class="col">
                                <h6><i class="fa fa-bookmark"></i> Browser Bookmark</h6>
                                <p class="m-0">
                                    <i class="fa fa-info-circle"></i>
                                    Drag and Drop this import link as a browser bookmark, Go to a MISP instance and click on your bookmarked link.
                                </p>
                                <small class="text-danger">
                                    <i class="fa fa-warning"></i>
                                    Temporarily disabling Content Security Policy headers may be necessary for the bookmark to execute.
                                </small>
                                <div class="d-flex justify-content-center bg-">
                                    <b-button :href="bookmarkJS" variant="outline-primary" style="cursor: grab;">
                                        <i class="fas fa-link"></i>
                                        Import to MFC
                                    </b-button>
                                </div>
                            </div>
                            <div class="col border-left border-primary">
                                <h6><i class="fa fa-puzzle-piece"></i> Browser Extension</h6>
                                <p class="m-0">
                                    <i class="fa fa-info-circle"></i>
                                    Install the MISP Fleet Commander Chrome Extension, Go to a MISP instance and click on the extension.
                                </p>
                                <p class="text-center mt-2">
                                    <a class="" href="https://github.com/mokaddem/MISP-Fleet-Commander-Browser-Extension">
                                        <i class="fas fa-link"></i>
                                        https://github.com/mokaddem/MISP-Fleet-Commander-Browser-Extension
                                    </a>
                                </p>
                            </div>
                        </div>
                    </b-alert>
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
import { baseurl } from "@/api/apiConfig"

export default {
    name: "TheHome",
    components: {
        Layout,
        Fleet,
        PluginIndex
    },
    data: function () {
        const token_type = this.$store.getters["auth/access_token_type"];
        const token = this.$store.getters["auth/access_token"];
        const location = window.location.origin
        return {
            bookmarkJS: `javascript: (function () {if (window.bookmarkletMFC !== undefined) {bookmarkletMFC();} else {localStorage.setItem("MFM_token", "${token}");localStorage.setItem("MFM_token_type", "${token_type}");localStorage.setItem("MFM_baseurl", "${location}");document.body.appendChild(document.createElement("script")).src = "${baseurl}/static/bookmarklet.js?r=" + Math.floor(Math.random() * 999999999)}})()`,
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
