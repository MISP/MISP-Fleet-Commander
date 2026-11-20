<template>
<ol class="qerr" :aria-label="`${groups.length} mistake${groups.length === 1 ? '' : 's'} in the statement`">
    <li v-for="(group, index) in placed" :key="index" class="qerr-item">
        <div class="qerr-head">
            <i class="fas fa-triangle-exclamation qerr-icon" aria-hidden="true"></i>
            <span class="qerr-message">{{ group.message }}</span>
            <code v-if="group.code" class="qerr-code">{{ group.code }}</code>
            <span class="qerr-where">line {{ group.place.number }}, column {{ group.place.column + 1 }}</span>
        </div>
        <pre class="qerr-excerpt" aria-hidden="true"><span class="qerr-gutter">{{ String(group.place.number).padStart(gutter) }} │ </span>{{ group.place.text }}
<span class="qerr-gutter">{{ ' '.repeat(gutter) }} │ </span><span class="qerr-caret">{{ ' '.repeat(group.place.column) }}^{{ '~'.repeat(group.place.length - 1) }}</span></pre>
        <div class="qerr-foot">
            <span v-if="group.servers && group.servers.length" class="qerr-servers">
                {{ group.servers.length === total ? (total === 1 ? 'From the server' : `From all ${total} servers`) : `From ${group.servers.join(', ')}` }}
            </span>
            <span v-if="group.path" class="qerr-path" title="Where MISP placed it in the request">{{ group.path }}</span>
            <b-button v-if="locatable" size="sm" variant="link" class="qerr-locate" @click="$emit('locate', group)">
                Show in the editor
            </b-button>
        </div>
    </li>
</ol>
</template>

<script>
import { errorLine } from "@/helpers/mispql"

// Mistakes drawn on the statement: the line, a caret under the place, who reported it
export default {
    name: "QueryErrorList",
    props: {
        statement: { type: String, default: "" },
        // groupErrors(), or check errors ({message, start, end})
        groups: { type: Array, default: () => [] },
        // How many servers answered: "From all 3 servers"
        total: { type: Number, default: 0 },
        locatable: { type: Boolean, default: false },
    },
    computed: {
        placed() {
            return this.groups.map(group => Object.assign({}, group, { place: errorLine(this.statement, group.start, group.end) }))
        },
        gutter() {
            return String(this.placed.reduce((max, group) => Math.max(max, group.place.number), 1)).length
        },
    },
}
</script>

<style scoped>
.qerr {
    margin: 0;
    padding: 0;
    list-style: none;
}

.qerr-item {
    padding: 0.7rem 0.85rem;
    border: 1px solid #f0c9cb;
    border-left: 3px solid var(--health-critical);
    border-radius: 6px;
    background: #fffafa;
}

.qerr-item + .qerr-item {
    margin-top: 0.5rem;
}

.qerr-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.5rem;
}

.qerr-icon {
    color: var(--health-critical);
}

.qerr-message {
    font-weight: 600;
    color: #5c1a1e;
}

.qerr-code {
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
    background: #f7e1e2;
    color: #7a2a2f;
    font-size: 0.75rem;
}

.qerr-where {
    margin-left: auto;
    font-size: 0.78rem;
    color: #8a6a6c;
}

.qerr-excerpt {
    margin: 0.5rem 0 0.35rem;
    padding: 0.45rem 0.6rem;
    border-radius: 4px;
    background: #fff;
    border: 1px solid #f3dcdd;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 0.82rem;
    line-height: 1.5;
    color: var(--var-color-yankeesblue);
    white-space: pre;
    overflow-x: auto;
}

.qerr-gutter {
    color: #a3aab4;
    user-select: none;
}

.qerr-caret {
    color: var(--health-critical);
    font-weight: 700;
}

.qerr-foot {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem 0.75rem;
    font-size: 0.8rem;
    color: #6b5a5b;
}

.qerr-path {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 0.75rem;
    color: #8a6a6c;
}

.qerr-locate {
    margin-left: auto;
    padding: 0;
    font-size: 0.8rem;
}
</style>
