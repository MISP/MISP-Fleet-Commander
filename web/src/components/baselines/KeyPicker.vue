<template>
    <div class="key-picker" @focusout="onFocusOut">
        <b-form-input
            :id="inputId"
            ref="input"
            :value="value"
            :placeholder="placeholder"
            :disabled="disabled"
            :state="state"
            autocomplete="off"
            spellcheck="false"
            role="combobox"
            aria-autocomplete="list"
            :aria-expanded="open ? 'true' : 'false'"
            :aria-controls="listId"
            :aria-activedescendant="activeId"
            :class="{ 'key-mono': mono }"
            @input="onInput"
            @focus="openList"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter="onEnter"
            @keydown.esc="onEscape"
        ></b-form-input>
        <ul
            v-show="open && (matches.length > 0 || loading) && !exactOnly"
            :id="listId"
            class="key-picker-list"
            role="listbox"
            tabindex="-1"
        >
            <li v-if="loading" class="key-picker-state" aria-live="polite">
                <b-spinner small class="mr-1"></b-spinner> {{ loadingText }}
            </li>
            <li
                v-for="(item, index) in matches"
                :id="`${listId}-${index}`"
                :key="item.value"
                role="option"
                :aria-selected="index === active ? 'true' : 'false'"
                :class="['key-picker-option', { active: index === active, taken: item.taken }]"
                @mousedown.prevent="choose(item)"
                @mousemove="active = index"
            >
                <span :class="['key-picker-label', { 'key-mono': mono }]">{{ item.label }}</span>
                <span v-if="item.taken" class="key-picker-taken">In the baseline</span>
                <span v-if="item.hint" class="key-picker-hint">{{ item.hint }}</span>
            </li>
            <li v-if="!loading && hiddenCount > 0" class="key-picker-state">
                {{ hiddenCount }} more: type to narrow down
            </li>
        </ul>
    </div>
</template>

<script>
const SHOWN = 60
let uid = 0

// A text input that suggests names from a list (settings, taxonomies, …). Free text stays allowed
export default {
    name: "KeyPicker",
    props: {
        value: { type: String, default: "" },
        // [{ value, label, hint, search, taken }]
        items: { type: Array, default: () => [] },
        placeholder: { type: String, default: "" },
        disabled: { type: Boolean, default: false },
        loading: { type: Boolean, default: false },
        loadingText: { type: String, default: "Loading…" },
        state: { type: Boolean, default: null },
        mono: { type: Boolean, default: false },
        inputId: { type: String, default: null },
    },
    data() {
        uid += 1
        return {
            listId: `key-picker-${uid}`,
            open: false,
            active: -1,
        }
    },
    computed: {
        allMatches() {
            const search = this.value.trim().toLowerCase()
            if (search === "") {
                return this.items
            }
            const starts = []
            const contains = []
            this.items.forEach((item) => {
                const haystack = item.search || `${item.value} ${item.label}`.toLowerCase()
                if (item.label.toLowerCase().startsWith(search) || String(item.value).toLowerCase().startsWith(search)) {
                    starts.push(item)
                } else if (haystack.includes(search)) {
                    contains.push(item)
                }
            })
            return starts.concat(contains)
        },
        matches() {
            return this.allMatches.slice(0, SHOWN)
        },
        hiddenCount() {
            return Math.max(this.allMatches.length - SHOWN, 0)
        },
        // The name is typed in full: nothing left to suggest
        exactOnly() {
            return this.allMatches.length === 1 && String(this.allMatches[0].value) === this.value.trim()
        },
        activeId() {
            return this.open && this.active >= 0 ? `${this.listId}-${this.active}` : null
        },
    },
    watch: {
        value() {
            this.active = -1
        },
    },
    methods: {
        focus() {
            this.$refs.input.focus()
        },
        openList() {
            if (!this.disabled) {
                this.open = true
            }
        },
        onInput(text) {
            this.$emit("input", text)
            this.open = true
        },
        move(step) {
            if (!this.open) {
                this.open = true
                return
            }
            if (this.matches.length === 0) {
                return
            }
            this.active = (this.active + step + this.matches.length) % this.matches.length
            this.$nextTick(() => {
                const element = document.getElementById(this.activeId)
                if (element) {
                    element.scrollIntoView({ block: "nearest" })
                }
            })
        },
        onEnter(event) {
            if (this.open && this.active >= 0 && this.matches[this.active]) {
                event.preventDefault()
                this.choose(this.matches[this.active])
            }
        },
        onEscape(event) {
            if (this.open) {
                event.stopPropagation()
                this.open = false
            }
        },
        choose(item) {
            this.$emit("input", String(item.value))
            this.$emit("select", item)
            this.open = false
            this.active = -1
        },
        onFocusOut(event) {
            if (!this.$el.contains(event.relatedTarget)) {
                this.open = false
            }
        },
    },
}
</script>

<style scoped>
.key-picker {
    position: relative;
}

.key-mono {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.85rem;
}

.key-picker-list {
    position: absolute;
    z-index: 1060;
    top: calc(100% + 2px);
    left: 0;
    right: 0;
    max-height: 18rem;
    overflow-y: auto;
    margin: 0;
    padding: 0.25rem 0;
    list-style: none;
    background: #fff;
    border: 1px solid #ced4da;
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(16, 24, 40, 0.14);
}

.key-picker-option {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.3rem 0.75rem;
    cursor: pointer;
}

.key-picker-option.active {
    background: var(--health-focus-bg);
}

.key-picker-label {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--var-color-yankeesblue);
}

.key-picker-hint {
    flex: 0 1 auto;
    max-width: 45%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.78rem;
    color: #5a6270;
}

.key-picker-taken {
    flex: 0 0 auto;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    color: #5a6270;
}

.key-picker-option.taken .key-picker-label {
    color: #5a6270;
}

.key-picker-state {
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    color: #5a6270;
}
</style>
