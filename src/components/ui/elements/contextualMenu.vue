<template>
    <b-list-group>
        <b-list-group-item button
            v-for="(entry, index) in getMenu"
            v-bind:key="index"
            size="sm"
            :variant="entry.variant"
            class="compact rounded-0"
            @click="emitClick(entry.eventName, entry.callbackData)"
        >
            <div class="row">
                <div class="col-1 text-center">
                    <i :class="`mr-2 fas fa-${entry.icon}`"></i>
                </div>
                <div class="col-md-auto">
                    {{ entry.text }}
                </div>
            </div>
        </b-list-group-item>
    </b-list-group>
</template>

<script>
export default {
    name: "contextualMenu",
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

<style scoped>
.compact {
    padding: 0.5rem 0.5rem;
}

.compact i.fas {
    width: 20px;
}

.list-group-item-outline-danger {
    transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out;
}

.list-group-item-outline-danger:hover {
    color: #fff;
    background-color: var(--red);
    border-color: var(--red);
}
</style>