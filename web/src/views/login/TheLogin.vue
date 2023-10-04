<template>
<Layout name="LayoutLogin">
    <div class="page-container">
        <div class="main-container bg-info d-flex justify-content-between">
            <div class="panel-left d-flex align-items-center justify-content-center">
                <div class="">
                    <img src="@/assets/logo.svg" class="logo mb-3" alt="MISP Fleet Commander logo">
                    <h5 class="text-muted fw-light text-center">Manage your MISP communities easily</h5>
                </div>
            </div>
            <div class="panel-right d-flex align-items-center justify-content-center">
                <div class="d-flex flex-column justify-content-center">
                    <h1 class="mb-4">Login Account</h1>
                    <b-form-input
                        v-model="email"
                        size="lg" type="email" class="mb-2" placeholder="Enter your username"
                    ></b-form-input>
                    <b-form-input
                        v-model="password"
                        size="lg" type="password" class="mb-2" placeholder="Enter your password"
                    ></b-form-input>
                    <Transition name="shake-x">
                        <b-alert :show="loginError" variant="danger">{{ errorMessage }}</b-alert>
                    </Transition>
                    <b-button
                        @click="login"
                        block variant="primary" class="login-button"
                    >
                        <b-spinner small v-if="postInProgress"></b-spinner>
                        <span v-if="!postInProgress">Login</span>
                    </b-button>
                </div>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"

export default {
    name: "TheLogin",
    components: {
        Layout,
    },
    data: function () {
        return {
            email: "admin@admin.test",
            password: "Password1234",
            postInProgress: false,
            loginError: null,
            errorMessage: "Invalid username or password",
        }
    },
    methods: {
        login() {
            let credentials = {
                email: this.email,
                password: this.password,
            }
            this.loginError = false
            this.postInProgress = true
            this.$store.dispatch("auth/authenticate", credentials)
                .then(() => {
                    this.$router.push(this.$route.query.redirect || '/')
                })
                .catch((error) => {
                    console.error(error);
                    this.loginError = true
                })
                .finally(() => {
                    this.postInProgress = false
                })
        }
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
        width: 80%;
        height: 90%;
        border-radius: 1rem;
        box-shadow: #32325d40 0px 13px 27px -5px, #0000004d 0px 8px 16px -8px;
        overflow: auto;
        min-width: 800px;
        max-width: 1600px;
    }

    .main-container > div {
        flex: 1;
        min-width: 450px;
    }

    .panel-left {
        background-color: var(--var-color-backgroundsteel);
    }
    .panel-right {
        color: white;
        background-color: var(--var-color-yankeesblue);
    }

    .logo {
        height: auto;
        width: 450px;
    }

    .login-button {
        background-color: var(--var-color-giantorgane);
        border-color: var(--var-color-giantorgane);
    }
    .login-button:hover {
        background-color: var(--var-color-giantorganedarker);
        border-color: var(--var-color-giantorganedarker);
    }
    .login-button:active {
        background-color: #ca4b0c !important;
        border-color: #ca4b0c !important;
    }
    .login-button:active:focus {
        box-shadow: 0 0 0 0.2rem #f2621a80 !important;
    }
    .login-button:focus {
        box-shadow: 0 0 0 0.2rem #f2621a80 !important;
    }

    .shake-x-enter-active {
        animation: shake-x 0.5s;
    }
    .shake-x-leave-active {
        animation: shake-x 0.5s reverse;
    }
    @keyframes shake-x {
         0% { transform: translateX(0) }
        25% { transform: translateX(5px) }
        50% { transform: translateX(-5px) }
        75% { transform: translateX(5px) }
        100% { transform: translateX(0) }
    }
</style>
