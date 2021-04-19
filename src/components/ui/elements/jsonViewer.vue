<template>
<div>
    <span v-if="tree">
        <ul class="pl-0">
            <li class="ml-3">
                <span 
                    variant="link"
                    :class="['p-0', canBeOpened && hasChild ? 'useCursorPointer' : '']"
                    @click="toggleOpen"
                >
                    <div :class="canBeOpened ? 'text-nowrap' : ''">
                        <i v-if="canBeOpened && hasChild" :class="['fas', isOpen ? 'fa-caret-down' : 'fa-caret-right']"></i>
                        <span :class="['font-weight-bold', rootkeyIndexing ? 'text-muted' : '']">
                            {{ rootKey }}
                        </span>
                        <span class="mx-1">
                            <span :class="[{'text-muted': hasChild || (canBeOpened && !hasChild), 'preppend-column': !canBeOpened}, childClass]">
                                {{ childString }}
                            </span>
                        </span>
                    </div>
                </span>
                <template v-if="canBeOpened && isOpen">
                    <jsonViewer
                        v-for="(child, index) in item"
                        :key="index"
                        :item="child"
                        :rootKeyName="index"
                        :rootkeyIndexing="Array.isArray(item)"
                    >
                    </jsonViewer>
                </template>
                <template v-else-if="!hasChild && Array.isArray(item)">
                    <small>empty array</small>
                </template>
                <template v-else-if="!hasChild && typeof item === 'object' && item !== null">
                    <small>empty object</small>
                </template>
            </li>
        </ul>
    </span>
    <span v-else>
        <pre>{{ item }}</pre>
    </span>
    </div>
</template>

<script>
export default {
    name: "jsonViewer",
    props: {
        tree: {
            default: function() { return true }
        },
        item: {
            required: true
        },
        rootKeyName: {
            default: function() { return "" }
        },
        open: {
            default: function() { return false }
        },
        rootkeyIndexing: {
            default: function() { return false }
        }
    },
    computed: {
        rootKey() {
            if (this.rootKeyName !== "") {
                return this.rootKeyName
            } else {
                if (Array.isArray(this.item)) {
                    return `Array [${this.item.length}]`
                } else if (typeof this.item === "object") {
                    return `Object {${Object.keys(this.item).length}}`
                } else {
                    return this.item
                }
            }
        },
        canBeOpened() {
            return Array.isArray(this.item) || typeof this.item === "object"
        },
        hasChild() {
            if (Array.isArray(this.item)) {
                return this.item.length > 0
            } else if (this.item === null) {
                return false
            } else if (typeof this.item === "object") {
                return Object.keys(this.item).length > 0
            } else {
                return false
            }
        },
        childString() {
            if (Array.isArray(this.item)) {
                return `Array[${this.item.length}]`
            } else if (this.item === null) {
                return "null"
            } else if (typeof this.item === "object") {
                return `Object{${Object.keys(this.item).length}}`
            } else {
                if (typeof this.item === "string") {
                    return `"${this.item}"`
                } else {
                    return this.item
                }
            }
        },
        childClass() {
            if (this.item === null) {
                return "text-muted"
            } else if (typeof this.item === "string") {
                return "text-success"
            } else if (typeof this.item === "boolean" || typeof this.item === "number") {
                return "text-primary"
            }
            return ""
        }
    },
    data: function() {
        return {
            isOpen: this.open
        }
    },
    methods: {
        toggleOpen() {
            if (this.hasChild) {
                this.isOpen = !this.isOpen
            }
        }
    }
}
</script>

<style scoped>
    .item {
        cursor: pointer;
    }
    ul {
        padding-left: 1em;
        list-style-type: none;
    }
    .preppend-column::before {
        content: ':';
        margin-right: 1em;
        color: black;
    }
</style>