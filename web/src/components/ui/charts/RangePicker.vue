<template>
    <div class="range-picker" role="group" aria-label="Range of the charts">
        <button
            v-for="option in RANGES"
            :key="option.key"
            type="button"
            :class="['range-option', { 'is-selected': option.key === value }]"
            :aria-pressed="option.key === value ? 'true' : 'false'"
            :title="`Show ${option.phrase}`"
            @click="pick(option.key)"
        >{{ option.label }}</button>
    </div>
</template>

<script>
import { RANGES } from "@/helpers/metrics"

// The range of the Usage tabs' charts (24 h … 1 y); `v-model` holds the range key
export default {
    name: "RangePicker",
    props: {
        value: { type: String, required: true },
    },
    data() {
        return { RANGES }
    },
    methods: {
        pick(key) {
            if (key !== this.value) {
                this.$emit("input", key)
            }
        },
    },
}
</script>

<style scoped>
.range-picker {
    display: inline-flex;
    padding: 2px;
    border: 1px solid #d5dbe3;
    border-radius: 6px;
    background: #f4f6f9;
}

.range-option {
    min-width: 3rem;
    padding: 0.2rem 0.6rem;
    border: 0;
    border-radius: 4px;
    background: none;
    color: #52514e;
    font-size: 0.8125rem;
    font-weight: 500;
    line-height: 1.4;
    white-space: nowrap;
}

.range-option:hover {
    color: #212d40;
    background: rgba(255, 255, 255, 0.7);
}

.range-option:focus-visible {
    outline: 2px solid rgba(41, 120, 160, 0.5);
    outline-offset: 1px;
}

.range-option.is-selected {
    background: #fff;
    color: #212d40;
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.15);
}
</style>
