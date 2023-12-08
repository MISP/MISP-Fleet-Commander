<template>
    <div>
        <h1 class="mb-4">Login</h1>
        <b-form-input
            v-model="email"
            v-on:keyup.enter="login"
            size="lg" type="email" class="mb-2" placeholder="Username"
        ></b-form-input>
        <b-form-input
            v-model="password"
            v-on:keyup.enter="login"
            size="lg" type="password" class="mb-2" placeholder="Password"
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
</template>

<script>

export default {
    name: "loginForm",
    components: {
    },
    props: {
        callbackOnLoging: {
            type: Function,
            default: undefined,
        },
    },
    data: function () {
        return {
            email: "",
            password: "",
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
                    if (this.callbackOnLoging) {
                        this.callbackOnLoging(true)
                    } else {
                        this.$router.push(this.$route.query.redirect || '/')
                    }
                })
                .catch((error) => {
                    console.error(error);
                    this.callbackOnLoging(false)
                    this.loginError = true
                })
                .finally(() => {
                    this.postInProgress = false
                })
        }
    }
}
</script>

<style scoped>
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
