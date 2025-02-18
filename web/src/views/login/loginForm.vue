<template>
    <div class="form-container">
        <label>Email</label>
        <b-form-input
            v-model="email"
            v-on:keyup.enter="login"
            size="md" type="email" class="mb-4 input-element" placeholder="Username"
        ></b-form-input>

        <label>Password</label>
        <b-form-input
            v-model="password"
            v-on:keyup.enter="login"
            size="md" type="password" class="mb-4 input-element" placeholder="Password"
        ></b-form-input>
        <Transition name="shake-x">
            <b-alert :show="loginError" variant="danger">
                {{ baseErrorMessage }}: <strong>{{ errorMessage }}</strong>
            </b-alert>
        </Transition>
        <b-button
            @click="login"
            block variant="primary" class="login-button"
        >
            <b-spinner small v-if="postInProgress"></b-spinner>
            <span v-if="!postInProgress">Log in</span>
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
            wrongCredentialError: "Invalid username or password",
            baseErrorMessage: "Something went wrong",
            errorMessage: "",
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
                    if (this.callbackOnLoging !== undefined) {
                        this.callbackOnLoging(true)
                    } else {
                        this.$router.push(this.$route.query.redirect || '/')
                    }
                })
                .catch((error) => {
                    if (this.callbackOnLoging !== undefined) {
                        this.callbackOnLoging(false)
                    }
                    this.loginError = true
                    if (error.response.status == 401) {
                        this.errorMessage = this.wrongCredentialError
                    } else {
                        this.errorMessage = `[${error.response.status}] ${error.response.statusText}`
                    }
                })
                .finally(() => {
                    this.postInProgress = false
                })
        }
    }
}
</script>


<style>
    .input-element {
        border-color: hsl(200, 83%, 60%);
        box-shadow: hsl(216.77, 31.96%, 19.02%) 0px 4px 12px;
        background-color: hsl(216.77, 31.96%, 19.02%);
        color: white;
    }
    .input-element:focus,
    input:-webkit-autofill {
        box-shadow: hsl(216.77, 31.96%, 19.02%) 0px 4px 12px;
        background-color: hsl(216.77, 31.96%, 19.02%) !important;
        color: white !important;
        transition: all 0s 50000s;
    }
</style>

<style scoped>
    label{
        color: hsl(200, 83%, 70%);
        font-weight: 500;
        margin-bottom: 0.35rem;
        user-select: none;
    }
    .form-container {
        width: 400px;
        display: flex;
        flex-direction: column;
        justify-items: center;
    }
    .login-button {
        background-color: hsl(217, 32%, 13%);
        border-color: hsl(220, 5%, 51%);
        color: hsl(200, 83%, 60%);
    }
    .login-button:hover {
        background-color: var(--var-color-giantorganedarker);
        border-color: var(--var-color-giantorganedarker);
        color: white;
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
