<template>
    <div
        :id="`setting-${setting.key}`"
        :class="['setting-row', {
            'is-pending': pending,
            'is-invalid': !!error,
            'is-dimmed': !!dependsOnName,
            'is-locked': locked,
            'is-highlighted': highlighted,
        }]"
    >
        <div class="setting-text">
            <div class="setting-name">
                <label :for="inputId" class="mb-0">{{ label }}</label>
                <span v-if="pending" class="setting-flag">Unsaved</span>
            </div>
            <p v-if="setting.description" class="setting-description">{{ setting.description }}</p>
            <code class="setting-key" title="Name in config.json and the API">{{ setting.key }}</code>
            <p v-if="locked && lockReason" class="setting-note">
                <i class="fas fa-lock" aria-hidden="true"></i>{{ lockReason }}
            </p>
            <p v-else-if="dependsOnName" class="setting-note">
                <i class="fas fa-circle-info" aria-hidden="true"></i>Not used while {{ dependsOnName }} is off.
            </p>
        </div>

        <div class="setting-control">
            <div v-if="setting.type === 'checkbox'" class="control-switch">
                <b-form-checkbox
                    :id="inputId"
                    :checked="isOn"
                    :disabled="readOnly || locked"
                    switch
                    @change="(checked) => $emit('change', checked)"
                >
                    <span :class="['switch-state', { 'is-on': isOn }]">{{ isOn ? "On" : "Off" }}</span>
                </b-form-checkbox>
            </div>

            <b-input-group v-else-if="setting.type === 'number'" class="control-number">
                <b-form-input
                    :id="inputId"
                    :value="value"
                    type="number"
                    :min="setting.min"
                    :max="setting.max"
                    step="1"
                    :state="error ? false : null"
                    :disabled="readOnly || locked"
                    :aria-describedby="`${inputId}-hint`"
                    @input="(input) => $emit('change', input)"
                ></b-form-input>
                <b-input-group-append v-if="setting.unit" is-text>{{ setting.unit }}</b-input-group-append>
            </b-input-group>

            <formInputFromConfig
                v-else
                :type="setting.type"
                :input_key="setting.key"
                :user_value="value"
                :params="{ ...setting, disabled: readOnly || locked, error: false }"
                @input="(key, input) => $emit('change', input)"
            ></formInputFromConfig>

            <div :id="`${inputId}-hint`" class="setting-hint">
                <span v-if="range">{{ range }}</span>
                <span v-if="range && hasDefault" class="hint-sep" aria-hidden="true">·</span>
                <span v-if="hasDefault">Default {{ defaultText }}</span>
            </div>
            <div v-if="zeroText" class="setting-hint is-zero">
                <i class="fas fa-infinity" aria-hidden="true"></i>{{ zeroText }}
            </div>
            <div v-if="error" class="setting-error" role="alert">
                <i class="fas fa-circle-exclamation" aria-hidden="true"></i>{{ error }}
            </div>
            <div v-if="!readOnly && !locked && (pending || !isDefault)" class="setting-actions">
                <button v-if="pending" type="button" class="link-action" @click="$emit('revert')">
                    <i class="fas fa-rotate-left" aria-hidden="true"></i>Undo
                </button>
                <button v-if="!isDefault" type="button" class="link-action" @click="$emit('reset-default')">
                    Use default
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import formInputFromConfig from "@/components/ui/elements/formInputFromConfig.vue"
import { asBoolean, formatValue, isLocked, isSameValue, rangeText, settingLabel } from "./settingsModel"

export default {
    name: "SettingRow",
    components: {
        formInputFromConfig,
    },
    props: {
        setting: { type: Object, required: true },
        // What the field shows: the unsaved change, else the saved value
        value: { required: false, default: null },
        pending: { type: Boolean, default: false },
        error: { type: String, default: null },
        readOnly: { type: Boolean, default: false },
        // Label of the switch that is off and without which this setting is not used
        dependsOnName: { type: String, default: null },
        highlighted: { type: Boolean, default: false },
    },
    computed: {
        inputId() {
            return `setting-input-${this.setting.key}`
        },
        label() {
            return settingLabel(this.setting)
        },
        locked() {
            return isLocked(this.setting)
        },
        lockReason() {
            const error = this.setting.error
            return (error && error.error_message) || "This setting cannot be changed."
        },
        isOn() {
            return asBoolean(this.value)
        },
        range() {
            return rangeText(this.setting)
        },
        hasDefault() {
            return this.setting.default !== undefined && this.setting.default !== null
        },
        defaultText() {
            // The unit is next to the field already
            if (this.setting.type === "number") {
                return String(this.setting.default)
            }
            return formatValue(this.setting, this.setting.default)
        },
        isDefault() {
            return !this.hasDefault || isSameValue(this.setting, this.value, this.setting.default)
        },
        zeroText() {
            if (this.setting.type !== "number" || !this.setting.zero_text) {
                return null
            }
            return isSameValue(this.setting, this.value, 0) ? this.setting.zero_text : null
        },
    },
}
</script>

<style scoped>
.setting-row {
    position: relative;
    display: flex;
    gap: 1.5rem;
    padding: 0.9rem 1.1rem 0.9rem 1.25rem;
    border-top: 1px solid var(--health-rule);
    transition: background-color 0.2s ease;
}

.setting-row:first-child {
    border-top: none;
}

.setting-row::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 3px;
    background: transparent;
    transition: background-color 0.2s ease;
}

.setting-row.is-pending {
    background: var(--health-focus-bg);
}

.setting-row.is-pending::before {
    background: var(--var-color-lapislazuli);
}

.setting-row.is-invalid::before {
    background: var(--health-critical);
}

.setting-row.is-highlighted {
    animation: setting-highlight 2.4s ease-out;
}

@keyframes setting-highlight {
    0%, 35% { background-color: var(--health-warning-tint); }
    100% { background-color: transparent; }
}

.setting-text {
    flex: 1 1 auto;
    min-width: 0;
}

.setting-name {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    line-height: 1.3;
}

.setting-flag {
    padding: 0.05rem 0.4rem;
    border-radius: 0.25rem;
    background: #dbe9f4;
    color: #1f5f80;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

.setting-description {
    max-width: 64ch;
    margin: 0.25rem 0 0;
    color: #5b636b;
    font-size: 0.84rem;
    line-height: 1.45;
}

.setting-key {
    display: inline-block;
    margin-top: 0.35rem;
    padding: 0;
    background: none;
    color: #8a939b;
    font-size: 0.72rem;
    user-select: all;
}

.setting-note {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0.4rem 0 0;
    color: #6c757d;
    font-size: 0.8rem;
}

.setting-note i {
    color: #9aa1a7;
}

.setting-row.is-dimmed .setting-name,
.setting-row.is-dimmed .setting-description,
.setting-row.is-dimmed .setting-control {
    opacity: 0.6;
}

.setting-control {
    flex: 0 0 14rem;
    width: 14rem;
    padding-top: 0.1rem;
}

.control-switch {
    display: flex;
    align-items: center;
    min-height: calc(1.5em + 0.75rem + 2px);
}

.switch-state {
    color: #6c757d;
    font-weight: 500;
    user-select: none;
}

.switch-state.is-on {
    color: var(--var-color-yankeesblue);
}

.control-number ::v-deep .form-control {
    font-variant-numeric: tabular-nums;
}

/* The message under the field says what is wrong: no icon over the number's arrows */
.control-number ::v-deep .form-control.is-invalid {
    padding-right: 0.75rem;
    background-image: none;
}

.control-number ::v-deep .input-group-text {
    min-width: 4.75rem;
    justify-content: center;
    background: #f4f6f8;
    color: #5b636b;
    font-size: 0.85rem;
}

.setting-hint {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.3rem;
    margin-top: 0.3rem;
    color: #7a838b;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
}

.setting-hint.is-zero {
    color: var(--health-info-ink);
}

.setting-hint.is-zero i {
    font-size: 0.7rem;
}

.hint-sep {
    color: #b8bec4;
}

.setting-error {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    margin-top: 0.35rem;
    color: var(--health-critical-ink);
    font-size: 0.8rem;
    line-height: 1.35;
}

.setting-actions {
    display: flex;
    gap: 0.9rem;
    margin-top: 0.3rem;
}

.link-action {
    display: inline-flex;
    align-items: baseline;
    gap: 0.3rem;
    padding: 0;
    border: none;
    background: none;
    color: var(--var-color-lapislazuli);
    font-size: 0.78rem;
    font-weight: 500;
    cursor: pointer;
}

.link-action:hover,
.link-action:focus-visible {
    color: #1d5a7a;
    text-decoration: underline;
}

.link-action i {
    font-size: 0.72rem;
}

@media (max-width: 767.98px) {
    .setting-row {
        flex-direction: column;
        gap: 0.75rem;
    }

    .setting-control {
        flex-basis: auto;
        width: 100%;
        max-width: 18rem;
    }
}
</style>
