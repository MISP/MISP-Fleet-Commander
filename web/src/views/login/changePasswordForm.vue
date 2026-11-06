<template>
    <div class="form-container">
        <h5 class="form-title">Choose a new password</h5>
        <p v-if="forced" class="form-notice">
            <i class="fas fa-shield-halved mr-1"></i>
            <strong>{{ email }}</strong> still uses its default password. Choose a new one to continue.
        </p>

        <label for="current-password">Current password</label>
        <b-form-input
            id="current-password"
            v-model="currentPassword"
            v-on:keyup.enter="submit"
            size="md" type="password" class="mb-4 input-element" autocomplete="current-password"
        ></b-form-input>

        <label for="new-password">New password</label>
        <b-form-input
            id="new-password"
            v-model="newPassword"
            v-on:keyup.enter="submit"
            size="md" type="password" class="input-element" autocomplete="new-password"
        ></b-form-input>
        <small class="field-hint mb-4" :class="{ 'field-hint-ok': longEnough }">
            <i :class="longEnough ? 'fas fa-check' : 'fas fa-circle-info'" class="fa-fw"></i>
            At least {{ minLength }} characters
        </small>

        <label for="confirm-password">Confirm new password</label>
        <b-form-input
            id="confirm-password"
            v-model="confirmation"
            v-on:keyup.enter="submit"
            size="md" type="password" class="mb-4 input-element" autocomplete="new-password"
        ></b-form-input>

        <Transition name="shake-x">
            <b-alert :show="errorMessage !== ''" variant="danger">
                <strong>{{ errorMessage }}</strong>
            </b-alert>
        </Transition>
        <b-button
            @click="submit"
            block variant="primary" class="login-button"
            :disabled="postInProgress"
        >
            <b-spinner small v-if="postInProgress"></b-spinner>
            <span v-else>Change password</span>
        </b-button>
        <div class="text-center mt-3">
            <b-link v-if="forced" class="secondary-link" @click="logout">Log out</b-link>
            <b-link v-else class="secondary-link" @click="leave">Cancel</b-link>
        </div>
    </div>
</template>

<script>
import { mapGetters } from "vuex"

// Mirrors the backend rule, so that most mistakes are caught before submitting
const MIN_PASSWORD_LENGTH = 12

export default {
    name: "changePasswordForm",
    data: function () {
        return {
            currentPassword: "",
            newPassword: "",
            confirmation: "",
            postInProgress: false,
            errorMessage: "",
            minLength: MIN_PASSWORD_LENGTH,
        }
    },
    computed: {
        ...mapGetters({
            user: "auth/user",
            forced: "auth/mustChangePassword",
        }),
        email() {
            return this.user?.email
        },
        longEnough() {
            return this.newPassword.length >= MIN_PASSWORD_LENGTH
        },
    },
    methods: {
        validate() {
            if (this.currentPassword === "") {
                return "Enter your current password"
            }
            if (!this.longEnough) {
                return `The new password must be at least ${MIN_PASSWORD_LENGTH} characters long`
            }
            if (this.newPassword !== this.confirmation) {
                return "The new passwords do not match"
            }
            if (this.newPassword === this.currentPassword) {
                return "The new password must be different from the current one"
            }
            return ""
        },
        submit() {
            if (this.postInProgress) {
                return
            }
            this.errorMessage = this.validate()
            if (this.errorMessage !== "") {
                return
            }
            this.postInProgress = true
            this.$store.dispatch("auth/changePassword", {
                currentPassword: this.currentPassword,
                newPassword: this.newPassword,
            })
                .then(() => {
                    this.$bvToast.toast("Your password has been changed", {
                        title: "Password changed",
                        variant: "success",
                        solid: true,
                    })
                    this.leave()
                })
                .catch((error) => {
                    const response = error.response
                    if (response === undefined) {
                        this.errorMessage = "The server could not be reached"
                    } else if (response.status === 401) {
                        this.$router.push({ name: "login", query: { redirect: this.$route.fullPath } }).catch(() => {})
                    } else {
                        this.errorMessage = response.data?.message || `[${response.status}] ${response.statusText}`
                    }
                })
                .finally(() => {
                    this.postInProgress = false
                })
        },
        leave() {
            // The guards may redirect (e.g. to select a fleet): not an error
            this.$router.push(this.$route.query.redirect || "/").catch(() => {})
        },
        logout() {
            this.$store.dispatch("auth/logout")
        },
    },
}
</script>

<style scoped src="./authForm.css"></style>

<style scoped>
    .form-title {
        color: hsl(200, 83%, 70%);
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .form-notice {
        color: hsl(210, 20%, 85%);
        background-color: hsla(200, 83%, 60%, 0.1);
        border-left: 3px solid hsl(200, 83%, 60%);
        border-radius: 0.25rem;
        padding: 0.6rem 0.75rem;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    .form-notice strong {
        color: white;
        font-weight: 600;
    }
    .field-hint {
        color: hsl(215, 15%, 65%);
        margin-top: 0.35rem;
        transition: color 0.2s;
    }
    .field-hint-ok {
        color: hsl(145, 55%, 55%);
    }
    .secondary-link {
        color: hsl(215, 15%, 70%);
        font-size: 0.9rem;
    }
    .secondary-link:hover {
        color: hsl(200, 83%, 70%);
    }
</style>
