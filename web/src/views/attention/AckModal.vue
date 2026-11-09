<template>
    <b-modal
        id="modal-ack-issue"
        title="Acknowledge issue"
        ok-title="Acknowledge"
        ok-variant="primary"
        cancel-variant="outline-secondary"
        :ok-disabled="saving"
        @ok="submit"
        @hidden="reset"
        @shown="focusFirstOption"
    >
        <template v-if="issue">
            <p class="mb-3">
                <strong>{{ issue.title }}</strong>
                <span class="text-muted"> on {{ issue.server_name }}</span>
            </p>
            <b-form-group label="Hide it" label-class="font-weight-bold" class="mb-3">
                <b-form-radio-group
                    v-model="duration"
                    :options="durations"
                    stacked
                    name="ack-duration"
                ></b-form-radio-group>
                <small class="form-text text-muted">
                    It shows again sooner if it clears and then comes back.
                </small>
            </b-form-group>
            <b-form-group label="Note" label-for="ack-note" label-class="font-weight-bold" class="mb-0"
                description="Optional. For example, why this is expected.">
                <b-form-textarea
                    id="ack-note"
                    v-model="note"
                    rows="2"
                    maxlength="500"
                ></b-form-textarea>
            </b-form-group>
        </template>
    </b-modal>
</template>

<script>
const HOUR = 3600

export default {
    name: "AckModal",
    props: {
        issue: { type: Object, default: null },
    },
    data() {
        return {
            duration: 24 * HOUR,
            note: "",
            saving: false,
            durations: [
                { value: HOUR, text: "For 1 hour" },
                { value: 24 * HOUR, text: "For 1 day" },
                { value: 7 * 24 * HOUR, text: "For 1 week" },
                { value: 0, text: "Until it clears" },
            ],
        }
    },
    methods: {
        focusFirstOption() {
            const checked = document.querySelector("#modal-ack-issue input[name='ack-duration']:checked")
            if (checked) {
                checked.focus()
            }
        },
        reset() {
            this.duration = 24 * HOUR
            this.note = ""
            this.saving = false
        },
        submit(event) {
            event.preventDefault()
            if (!this.issue) {
                return
            }
            this.saving = true
            const payload = { issue_id: this.issue.id, note: this.note.trim() }
            if (this.duration > 0) {
                payload.until = Math.floor(Date.now() / 1000) + this.duration
            }
            this.$store.dispatch("health/acknowledge", payload)
                .then(() => {
                    this.$bvToast.toast(`${this.issue.title} on ${this.issue.server_name}`, {
                        title: "Issue acknowledged",
                        variant: "success",
                    })
                    this.$bvModal.hide("modal-ack-issue")
                })
                .catch((error) => {
                    this.$bvToast.toast(error, {
                        title: "Could not acknowledge the issue",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.saving = false
                })
        },
    },
}
</script>
