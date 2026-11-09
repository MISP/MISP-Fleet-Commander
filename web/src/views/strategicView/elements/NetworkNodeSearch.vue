<template>
    <div class="node-search" @keydown.esc.stop="close">
        <i class="fas fa-search node-search-icon" aria-hidden="true"></i>
        <input
            ref="input"
            v-model="query"
            type="search"
            class="form-control form-control-sm node-search-input"
            placeholder="Find a server…"
            role="combobox"
            aria-autocomplete="list"
            aria-label="Find a server in the graph"
            :aria-expanded="isOpen ? 'true' : 'false'"
            aria-controls="node-search-results"
            :aria-activedescendant="isOpen && activeIndex >= 0 ? `node-search-option-${activeIndex}` : null"
            autocomplete="off"
            spellcheck="false"
            @focus="open = true"
            @blur="onBlur"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="choose(activeIndex)"
        >
        <ul
            v-show="isOpen"
            id="node-search-results"
            class="node-search-results shadow"
            role="listbox"
            aria-label="Matching servers"
        >
            <li
                v-for="(match, index) in matches"
                :id="`node-search-option-${index}`"
                :key="match.id"
                role="option"
                :aria-selected="index === activeIndex ? 'true' : 'false'"
                :class="['node-search-option', { active: index === activeIndex }]"
                @mousedown.prevent="choose(index)"
                @mousemove="activeIndex = index"
            >
                <span :class="['node-search-dot', `dot-${match.level}`]" aria-hidden="true"></span>
                <span class="node-search-text">
                    <span class="node-search-name">{{ match.name }}</span>
                    <span class="node-search-url">{{ match.url }}</span>
                </span>
                <span v-if="!match.managed" class="node-search-tag">remote</span>
            </li>
            <li v-if="matches.length === 0" class="node-search-empty" role="presentation">No server matches “{{ query }}”</li>
        </ul>
    </div>
</template>

<script>
const MAX_RESULTS = 8

export default {
    name: "NetworkNodeSearch",
    props: {
        // [{id, name, url, managed, level}]: level colours the dot (a health severity or a link level)
        nodes: { type: Array, required: true },
    },
    data() {
        return {
            query: "",
            open: false,
            activeIndex: 0,
            // The query was set by choosing a result, not typed: the list stays closed
            chosen: false,
        }
    },
    computed: {
        matches() {
            const needle = this.query.trim().toLowerCase()
            if (needle === "") {
                return []
            }
            const scored = []
            this.nodes.forEach(node => {
                const name = (node.name || "").toLowerCase()
                const url = (node.url || "").toLowerCase()
                if (name.startsWith(needle)) {
                    scored.push([0, node])
                } else if (name.includes(needle)) {
                    scored.push([1, node])
                } else if (url.includes(needle)) {
                    scored.push([2, node])
                }
            })
            scored.sort((a, b) => a[0] - b[0] || Number(b[1].managed) - Number(a[1].managed) || a[1].name.localeCompare(b[1].name))
            return scored.slice(0, MAX_RESULTS).map(entry => entry[1])
        },
        isOpen() {
            return this.open && this.query.trim() !== ""
        },
    },
    watch: {
        query() {
            this.activeIndex = 0
            if (this.chosen) {
                this.chosen = false
                return
            }
            this.open = true
        },
    },
    methods: {
        move(step) {
            if (!this.isOpen) {
                this.open = true
                return
            }
            if (this.matches.length > 0) {
                this.activeIndex = (this.activeIndex + step + this.matches.length) % this.matches.length
            }
        },
        choose(index) {
            const match = this.matches[index]
            if (match === undefined) {
                return
            }
            this.$emit("select", match.id)
            this.chosen = this.query !== match.name
            this.query = match.name
            this.open = false
        },
        close() {
            this.open = false
        },
        onBlur() {
            this.open = false
        },
    },
}
</script>

<style scoped>
.node-search {
    position: relative;
    width: 13rem;
}

.node-search-icon {
    position: absolute;
    left: 0.55rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.75rem;
    color: #6c757d;
    pointer-events: none;
}

.node-search-input {
    padding-left: 1.7rem;
}

.node-search-results {
    position: absolute;
    top: calc(100% + 0.25rem);
    left: 0;
    z-index: 20;
    width: 19rem;
    max-width: calc(100vw - 2rem);
    margin: 0;
    padding: 0.25rem 0;
    list-style: none;
    background: white;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.3rem;
    font-size: 0.8rem;
}

.node-search-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.6rem;
    cursor: pointer;
}

.node-search-option.active {
    background: var(--health-focus-bg);
}

.node-search-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.node-search-name {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.node-search-url {
    color: #6c757d;
    font-size: 0.72rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.node-search-tag {
    margin-left: auto;
    padding: 0 0.35rem;
    border: 1px dashed #adb5bd;
    border-radius: 0.6rem;
    color: #6c757d;
    font-size: 0.68rem;
}

.node-search-dot {
    flex: none;
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 50%;
    background: var(--link-unknown);
}

.dot-broken, .dot-critical { background: var(--link-broken); }
.dot-degraded, .dot-warning { background: var(--link-degraded); }
.dot-ok { background: var(--link-ok); }
.dot-info { background: var(--health-info); }

.node-search-empty {
    padding: 0.35rem 0.6rem;
    color: #6c757d;
}
</style>
