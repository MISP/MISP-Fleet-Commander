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
                <strong>{{ errorMessage }}</strong>
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
                        // The guards may redirect (fleet selection, password change): not an error
                        this.$router.push(this.$route.query.redirect || '/').catch(() => {})
                    }
                })
                .catch((error) => {
                    if (this.callbackOnLoging !== undefined) {
                        this.callbackOnLoging(false)
                    }
                    this.loginError = true
                    const response = error.response
                    if (response === undefined) {
                        this.errorMessage = `${this.baseErrorMessage}: the server could not be reached`
                    } else if (response.status == 401) {
                        this.errorMessage = this.wrongCredentialError
                    } else if (response.status == 429 && response.data?.message) {
                        this.errorMessage = response.data.message
                    } else {
                        this.errorMessage = `${this.baseErrorMessage}: [${response.status}] ${response.statusText}`
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

<style scoped src="./authForm.css"></style>
