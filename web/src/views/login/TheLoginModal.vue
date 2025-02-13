<template>
    <div>
        <b-modal ref="login-modal" hide-footer hide-header content-class="login-modal">
            <div class="d-flex flex-column align-items-center py-3">
                <b-alert show variant="warning" style="width: 400px;">
                    <strong class="mb-2">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        Session Expired  
                    </strong>
                    <div>Your session has timed out. Please log in again to continue.</div>
                </b-alert>
                <loginForm
                    :callbackOnLoging="handleLogin"
                ></loginForm>
            </div>
        </b-modal>
    </div>
</template>

<script>
import EventBus from '@/event-bus';
import loginForm from "@/views/login/loginForm.vue"

export default {
    name: "TheLoginModal",
    components: {
        loginForm,
    },
    data: function () {
        return {
            successCB: null,
            errorCB: null,
        }
    },
    methods: {
        showModal() {
            this.$refs['login-modal'].show()
        },
        hideModal() {
            this.$refs['login-modal'].hide()
        },
        handleLogin(success) {
            if (success) {
                this.successCB()
            } else {
                this.errorCB()
            }
            this.hideModal()
        },
    },
    mounted() {
        EventBus.$on('open-login-modal', (successCB, errorCB) => {
            this.showModal()
            this.successCB = successCB
            this.errorCB = errorCB
        });
    }
}
</script>

<style>
    body {
        background-color: var(--var-color-background) !important;
    }
    .login-modal {
        background: hsl(216.8, 18.18%, 19.25%);
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
</style>
