<template>
    <b-list-group>
        <b-dropdown-item-button
            v-for="(entry, index) in getMenu"
            v-bind:key="index"
            :disabled="entry.disabled"
            :class="['compact rounded-0', entry.variant ? entry.variant : '', entry.disabled ? 'disabled' : '']"
            @click.stop="emitClick(entry.eventName, entry.callbackData)"
        >
            <iconButton
                :text="entry.text"
                :title="entry.title"
                :icon="entry.icon"
                :useAsset="entry.useAsset"
                :forceWhite="entry.forceWhite"
            ></iconButton>
        </b-dropdown-item-button>
    </b-list-group>
</template>

<script>
import iconButton from "@/components/ui/elements/iconButton.vue"

export default {
    name: "contextualMenu",
    components: {
        iconButton
    },
    props: {
        menu: {
            type: Array,
            required: true
        }
    },
    computed: {
        getMenu() {
            let default_menu = []
            this.menu.forEach(entry => {
                if (entry.text) {
                    default_menu.push(entry)
                }
            })
            return default_menu
        }
    },
    methods: {
        setDefault(variable, default_value) {
            Object.is(variable, undefined) ? default_value : variable
        },
        emitClick(eventName, callbackData) {
            this.$emit(eventName, callbackData)
        }
    }
}
</script>

<style>
.list-group > .outline-danger, .list-group > .outline-primary,
.dropdown-menu > li.outline-danger > .dropdown-item, .dropdown-menu > li.outline-primary > .dropdown-item {
    transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out;
}

.list-group > .outline-danger:not(.disabled):hover,
.dropdown-menu > li.outline-danger > .dropdown-item:not(.disabled):hover  {
    color: #fff;
    background-color: var(--red);
    border-color: var(--red);
}

.list-group > .outline-primary:not(.disabled):hover,
.dropdown-menu > li.outline-primary.dropdown-item:not(.disabled):hover {
    color: #fff;
    background-color: var(--blue);
    border-color: var(--blue);
}

.list-group .outline-primary:not(.disabled) .dropdown-item:hover,
.list-group .outline-danger:not(.disabled) .dropdown-item:hover {
    color: unset !important;
    background-color: unset !important;
}
</style>