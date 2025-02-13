<template>
<Layout name="LayoutLogin">
    <div class="page-container">
        <div class="main-container d-flex flex-column">
            <div class="d-flex align-items-start justify-content-center pt-5 gradient">
                <div class="d-flex flex-column align-items-center">
                    <img src="@/assets/logo.svg" class="logo" alt="MISP Fleet Commander logo">
                    <loginForm></loginForm>
                </div>
            </div>
            <div class="logo-text-bottom">
                <h5 class="fw-light text-center logo-text">Manage your MISP communities easily</h5>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import loginForm from "@/views/login/loginForm.vue"

export default {
    name: "TheLogin",
    components: {
        Layout,
        loginForm,
    },
    data: function () {
        return {
        }
    },
    methods: {
    }
}
</script>

<style>
    body {
        background-color: var(--var-color-background) !important;
    }
</style>

<style scoped>
    .page-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100vh;
    }

    .main-container {
        border-radius: 0.5rem;
        box-shadow: rgba(0, 0, 0, 0.19) 0px 10px 20px, rgba(0, 0, 0, 0.23) 0px 6px 6px;
        overflow: auto;
        min-width: 500px;
        max-width: 1600px;
        position: relative;
    }

    .main-container > div {
        z-index: 1;
    }

    .gradient::before {
        background: radial-gradient(circle at 50% 0%, hsl(216.8, 17.48%, 40.39%) 15%, hsl(216.8, 18.18%, 19.25%) 70%);
        content: '';
        width: 100%;
        height: calc(100% + 5em);
        position: absolute;
        top: -5em;
        opacity: 0.6;
        z-index: 0;
    }
    .gradient {
        padding-bottom: 8em;
        --s: 28px; /* control the size */
        --c:#0000,var(--var-color-yankeesblue) /* first color */ .5deg 119.5deg,#0000 120deg;
        --g1:conic-gradient(from  60deg at 56.25% calc(425%/6),var(--c));
        --g2:conic-gradient(from 180deg at 43.75% calc(425%/6),var(--c));
        --g3:conic-gradient(from -60deg at 50%   calc(175%/12),var(--c));
        background:
            var(--g1),var(--g1) var(--s) calc(1.73*var(--s)),
            var(--g2),var(--g2) var(--s) calc(1.73*var(--s)),
            var(--g3) var(--s) 0,var(--g3) 0 calc(1.73*var(--s)) 
            #2b3447; /* second color */
        background-size: calc(2*var(--s)) calc(3.46*var(--s));
    }

    .gradient > div {
        z-index: 1;
    }

    .logo-text-bottom {
        border-top: 2px solid hsl(220, 5%, 51%);
        width: 100%;
        background-color: hsl(216.8, 18.18%, 17.25%);
        padding: 1em 0;
    }

    .panel-right {
        color: white;
        background-color: var(--var-color-yankeesblue);
    }

    .logo {
        height: auto;
        width: 450px;
        margin-bottom: 4rem;
        user-select: none;
    }
    .logo, .logo-text {
        filter: drop-shadow(0.25rem 0.25rem 0.3rem rgba(0, 0, 0, 0.55))
    }

    .logo-text {
        color: #bcbcbc;
        font-weight: 300;
    }
</style>
