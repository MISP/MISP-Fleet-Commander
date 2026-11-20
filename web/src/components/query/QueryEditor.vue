<template>
<div :class="['qe', { 'qe-focused': focused, 'qe-disabled': disabled }]">
    <div class="qe-field">
        <pre ref="highlight" class="qe-text qe-highlight" aria-hidden="true"><template v-for="(piece, index) in pieces"><span
            v-if="piece.caret" :key="`c${index}`" class="qe-caret-mark"></span><span
            v-else :key="index" :class="[piece.cls, { 'qe-mark': piece.mark }]">{{ piece.text }}</span></template>{{ trailing }}</pre>
        <textarea
            :id="inputId"
            ref="input"
            class="qe-text qe-input"
            :value="value"
            :disabled="disabled"
            :placeholder="placeholder"
            :aria-label="label"
            :aria-describedby="describedby"
            aria-autocomplete="list"
            :aria-expanded="open ? 'true' : 'false'"
            :aria-controls="listId"
            :aria-activedescendant="open ? optionId(active) : null"
            spellcheck="false"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="off"
            @input="onInput"
            @keydown="onKeydown"
            @scroll="syncScroll"
            @click="close"
            @focus="focused = true"
            @blur="onBlur"
        ></textarea>
        <div ref="mirror" class="qe-text qe-mirror" aria-hidden="true"></div>

        <ul
            v-show="open"
            :id="listId"
            ref="list"
            class="qe-completions"
            role="listbox"
            :aria-label="`Completions for ${label}`"
            :style="popupStyle"
        >
            <li
                v-for="(item, index) in items"
                :id="optionId(index)"
                :key="`${item.kind}-${item.label}`"
                role="option"
                :aria-selected="index === active ? 'true' : 'false'"
                :class="['qe-option', { active: index === active }]"
                @mousedown.prevent="accept(index)"
                @mousemove="active = index"
            >
                <span :class="['qe-option-kind', `qe-kind-${item.kind}`]" aria-hidden="true">{{ kindMark(item.kind) }}</span>
                <span class="qe-option-label">{{ item.label }}</span>
                <span v-if="item.detail" class="qe-option-detail">{{ item.detail }}</span>
            </li>
        </ul>
    </div>
</div>
</template>

<script>
import {
    applyCompletion, completionContext, completionItems, segments, tokenize,
} from "@/helpers/mispql"

// Kinds of names that are worth offering as soon as a space is typed (keywords alone wait for a letter)
const NAME_KINDS = ["statement", "table", "field", "column", "sort", "format", "operator", "star"]
const KIND_MARKS = { keyword: "K", table: "T", column: "C", field: "F", operator: "=", sort: "S", format: "◆" }
let uid = 0

// A MispQL statement editor: the text coloured as mispql reads it, mistakes underlined, completion of keywords,
// tables, columns, fields and operators. Ctrl/⌘+Enter asks to run
export default {
    name: "QueryEditor",
    props: {
        value: { type: String, default: "" },
        // GET /queries/language
        language: { type: Object, default: null },
        // unionFields() of the statement's table on the chosen servers
        described: { type: Object, default: null },
        // Ranges to underline: [{start, end}]
        marks: { type: Array, default: () => [] },
        disabled: { type: Boolean, default: false },
        label: { type: String, default: "MispQL statement" },
        placeholder: { type: String, default: "" },
        describedby: { type: String, default: null },
    },
    data() {
        uid += 1
        return {
            uid,
            focused: false,
            open: false,
            items: [],
            active: 0,
            context: null,
            popup: { top: 0, left: 0 },
        }
    },
    computed: {
        inputId() {
            return `query-editor-${this.uid}`
        },
        listId() {
            return `query-editor-${this.uid}-completions`
        },
        keywords() {
            return this.language && this.language.keywords ? new Set(this.language.keywords) : undefined
        },
        tokens() {
            return tokenize(this.value, this.keywords)
        },
        pieces() {
            return segments(this.value, this.tokens, this.marks)
        },
        // A last empty line has no height in a <pre> unless something follows it
        trailing() {
            return this.value.endsWith("\n") || this.value === "" ? " " : ""
        },
        popupStyle() {
            return { top: `${this.popup.top}px`, left: `${this.popup.left}px` }
        },
    },
    watch: {
        value() {
            this.$nextTick(() => {
                this.autosize()
                this.syncScroll()
            })
        },
        described() {
            if (this.open) {
                this.refresh(false)
            }
        },
    },
    mounted() {
        this.autosize()
    },
    methods: {
        focus() {
            this.$refs.input.focus()
        },
        // As tall as its text, between the CSS min and max heights; it scrolls beyond
        autosize() {
            const input = this.$refs.input
            if (input) {
                input.style.height = "auto"
                input.style.height = `${input.scrollHeight}px`
            }
        },
        optionId(index) {
            return `${this.listId}-${index}`
        },
        kindMark(kind) {
            return KIND_MARKS[kind] || "·"
        },
        syncScroll() {
            const input = this.$refs.input
            const highlight = this.$refs.highlight
            if (input && highlight) {
                highlight.scrollTop = input.scrollTop
                highlight.scrollLeft = input.scrollLeft
            }
        },
        onInput(event) {
            this.$emit("input", event.target.value)
            const data = event.data || ""
            const last = data.slice(-1)
            if (event.inputType === "insertText" || event.inputType === "insertReplacementText") {
                if (/[A-Za-z0-9_.]/.test(last)) {
                    this.$nextTick(() => this.refresh(true))
                } else if (/[\s,(]/.test(last)) {
                    this.$nextTick(() => this.refresh(true, NAME_KINDS))
                } else {
                    this.close()
                }
            } else if (this.open) {
                this.$nextTick(() => this.refresh(false))
            }
        },
        // Recompute the completions at the caret. `opening`: may open the list; `onlyKinds`: open only when names of
        // these kinds may follow
        refresh(opening, onlyKinds) {
            const input = this.$refs.input
            if (!input || this.disabled || input.selectionStart !== input.selectionEnd) {
                this.close()
                return
            }
            const context = completionContext(input.value, input.selectionStart, this.keywords)
            if (!context || (onlyKinds && !this.open && !context.kinds.some(kind => onlyKinds.includes(kind)))) {
                this.close()
                return
            }
            const items = completionItems(context, { language: this.language, described: this.described })
            if (items.length === 0 || (!opening && !this.open)) {
                this.close()
                return
            }
            this.context = context
            this.items = items
            this.active = 0
            this.place(context.from)
            this.open = true
            this.$nextTick(this.scrollActive)
        },
        // The list opens under the start of the word being completed
        place(offset) {
            const input = this.$refs.input
            const mirror = this.$refs.mirror
            mirror.style.width = `${input.offsetWidth}px`
            mirror.textContent = input.value.slice(0, offset)
            const marker = document.createElement("span")
            marker.textContent = "​"
            mirror.appendChild(marker)
            const lineHeight = marker.offsetHeight || 20
            const width = Math.min(360, input.clientWidth)
            this.popup = {
                top: marker.offsetTop - input.scrollTop + lineHeight + 4,
                left: Math.max(0, Math.min(marker.offsetLeft - input.scrollLeft, input.clientWidth - width)),
            }
        },
        close() {
            this.open = false
            this.context = null
        },
        onBlur() {
            this.focused = false
            this.close()
        },
        move(step) {
            if (this.items.length === 0) {
                return
            }
            this.active = (this.active + step + this.items.length) % this.items.length
            this.$nextTick(this.scrollActive)
        },
        scrollActive() {
            const list = this.$refs.list
            const option = list && list.children[this.active]
            if (option) {
                const top = option.offsetTop
                const bottom = top + option.offsetHeight
                if (top < list.scrollTop) {
                    list.scrollTop = top
                } else if (bottom > list.scrollTop + list.clientHeight) {
                    list.scrollTop = bottom - list.clientHeight
                }
            }
        },
        accept(index) {
            const item = this.items[index]
            const context = this.context
            const input = this.$refs.input
            if (!item || !context || !input) {
                return
            }
            const { text, cursor, insert } = applyCompletion(input.value, context, item)
            this.close()
            input.focus()
            input.setSelectionRange(context.from, context.to)
            // Through the browser's own editing, so that undo takes it back; it fires `input` like typing does
            let done = false
            try {
                done = document.execCommand("insertText", false, insert)
            } catch (e) {
                done = false
            }
            if (!done || input.value !== text) {
                this.$emit("input", text)
                this.$nextTick(() => {
                    input.setSelectionRange(cursor, cursor)
                    if (item.insert.endsWith(" ")) {
                        this.refresh(true, NAME_KINDS)
                    }
                })
            } else {
                input.setSelectionRange(cursor, cursor)
            }
        },
        onKeydown(event) {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault()
                this.close()
                this.$emit("run")
                return
            }
            if (event.ctrlKey && (event.key === " " || event.code === "Space")) {
                event.preventDefault()
                this.refresh(true)
                return
            }
            if (!this.open) {
                return
            }
            switch (event.key) {
            case "ArrowDown":
                event.preventDefault()
                this.move(1)
                break
            case "ArrowUp":
                event.preventDefault()
                this.move(-1)
                break
            case "PageDown":
                event.preventDefault()
                this.move(Math.min(7, this.items.length - 1 - this.active) || 0)
                break
            case "PageUp":
                event.preventDefault()
                this.move(-Math.min(7, this.active) || 0)
                break
            case "Enter":
            case "Tab":
                event.preventDefault()
                this.accept(this.active)
                break
            case "Escape":
                event.preventDefault()
                event.stopPropagation()
                this.close()
                break
            case "ArrowLeft":
            case "ArrowRight":
            case "Home":
            case "End":
                this.close()
                break
            default:
                break
            }
        },
    },
}
</script>

<style scoped>
.qe {
    --qe-font: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    --qe-size: 13.5px;
    --qe-line: 1.6;
    --qe-pad-y: 0.7rem;
    --qe-pad-x: 0.85rem;
    position: relative;
    background: #fff;
    border: 1px solid #cfd5dd;
    border-radius: 6px;
    transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.qe-focused {
    border-color: var(--var-color-lapislazuli);
    box-shadow: 0 0 0 3px rgba(41, 120, 160, 0.16);
}

.qe-disabled {
    background: #f4f6f8;
}

.qe-field {
    position: relative;
}

/* The textarea and its coloured copy share every metric, so the coloured text sits exactly under the caret */
.qe-text {
    margin: 0;
    padding: var(--qe-pad-y) var(--qe-pad-x);
    border: 0;
    font-family: var(--qe-font);
    font-size: var(--qe-size);
    line-height: var(--qe-line);
    letter-spacing: 0;
    tab-size: 4;
    white-space: pre-wrap;
    word-break: normal;
    overflow-wrap: break-word;
    scrollbar-gutter: stable;
}

.qe-highlight {
    position: absolute;
    inset: 0;
    overflow: hidden;
    color: var(--var-color-yankeesblue);
    pointer-events: none;
}

.qe-input {
    position: relative;
    display: block;
    width: 100%;
    min-height: calc(5 * var(--qe-line) * var(--qe-size) + 2 * var(--qe-pad-y));
    max-height: calc(16 * var(--qe-line) * var(--qe-size) + 2 * var(--qe-pad-y));
    resize: none;
    overflow: auto;
    background: transparent;
    color: transparent;
    caret-color: var(--var-color-yankeesblue);
    outline: none;
}

.qe-input::placeholder {
    color: #b0b6bf;
    font-style: italic;
}

.qe-input::selection {
    background: rgba(41, 120, 160, 0.22);
    color: transparent;
}

.qe-mirror {
    position: absolute;
    top: 0;
    left: 0;
    visibility: hidden;
    pointer-events: none;
    overflow: hidden;
    height: auto;
}

.q-keyword { color: #1f4fa3; font-weight: 600; }
.q-table { color: #0b6e69; font-weight: 600; }
.q-name { color: var(--var-color-yankeesblue); }
.q-string { color: #9a4a00; }
.q-number,
.q-literal { color: #7b3fb0; }
.q-comment { color: #7d8590; font-style: italic; }
.q-operator { color: #b4235a; }
.q-punctuation { color: #5f6873; }
.q-unknown { color: #c0262d; }

.qe-mark {
    text-decoration: underline wavy var(--health-critical);
    text-decoration-skip-ink: none;
    text-underline-offset: 3px;
    background: rgba(192, 38, 45, 0.07);
}

.qe-caret-mark {
    display: inline-block;
    width: 0.65ch;
    height: 1.1em;
    margin-left: 1px;
    vertical-align: text-bottom;
    border-bottom: 2px solid var(--health-critical);
    background: rgba(192, 38, 45, 0.12);
}

.qe-completions {
    position: absolute;
    z-index: 30;
    width: 360px;
    max-width: calc(100% - 0.5rem);
    max-height: 17rem;
    overflow-y: auto;
    margin: 0;
    padding: 0.25rem;
    list-style: none;
    background: #fff;
    border: 1px solid #cfd5dd;
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(33, 45, 64, 0.16);
}

.qe-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.28rem 0.45rem;
    border-radius: 4px;
    font-size: 0.85rem;
    cursor: pointer;
}

.qe-option.active {
    background: #eaf3f8;
}

.qe-option-kind {
    flex: none;
    width: 1.25rem;
    height: 1.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 3px;
    font-size: 0.68rem;
    font-weight: 700;
    color: #fff;
    background: #9aa1a7;
}

.qe-kind-keyword { background: #1f4fa3; }
.qe-kind-table { background: #0b6e69; }
.qe-kind-column,
.qe-kind-field { background: var(--var-color-lapislazuli); }
.qe-kind-operator { background: #b4235a; }
.qe-kind-sort { background: #5f6873; }
.qe-kind-format { background: #7b3fb0; }

.qe-option-label {
    font-family: var(--qe-font);
    color: var(--var-color-yankeesblue);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.qe-option-detail {
    margin-left: auto;
    padding-left: 0.75rem;
    font-size: 0.75rem;
    color: #6b7380;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 55%;
}
</style>
