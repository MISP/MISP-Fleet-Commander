<template>
    <div>
        <b-form-group>
            <b-form-tags
                v-model="selected_value"
                @input="$emit('input', $event)"
                no-outer-focus style="margin-bottom: -0.75em;"
            >
                <template v-slot="{ tags, disabled, addTag, removeTag }">
                    <ul v-if="tags.length > 0" class="list-inline d-inline-block mb-2">
                        <li v-for="tag in tags" :key="tag" class="list-inline-item">
                            <b-form-tag
                            @remove="removeTag(tag)"
                            :title="tag"
                            :disabled="disabled"
                            variant="info"
                            >{{ textByValue[tag] }}</b-form-tag>
                        </li>
                        <b-button
                            variant="danger"
                            size="xs"
                            class="px-2"
                            @click="clearAll(removeTag)"
                        >
                        <i class="fa fa-trash mr-1"></i>Clear All
                        </b-button>
                    </ul>

                    <b-dropdown size="sm" variant="outline-secondary" block menu-class="w-100">
                        <template #button-content>
                            <b-icon icon="tag-fill"></b-icon> Choose
                        </template>

                        <b-dropdown-form @submit.stop.prevent="() => {}">
                            <b-form-group
                                label="Search tags"
                                label-for="tag-search-input"
                                label-cols-md="auto"
                                class="mb-0"
                                label-size="sm"
                                :description="searchDesc"
                                :disabled="disabled"
                                >
                                <b-form-input
                                    v-model="search"
                                    id="tag-search-input"
                                    type="search"
                                    size="sm"
                                    autocomplete="off"
                                    autofocus
                                ></b-form-input>
                            </b-form-group>
                        </b-dropdown-form>

                        <b-dropdown-item-button
                            variant="primary" size="sm" class="my-1"
                            @click="selectAll(addTag)"
                        >
                            <i class="fa fa-check-square mr-1"></i>Select All
                        </b-dropdown-item-button>

                        <b-dropdown-divider></b-dropdown-divider>

                        <div style="overflow-y: auto; max-height: 18rem;">
                            <b-dropdown-item-button
                                v-for="option in availableOptions"
                                :key="option.value"
                                :disabled="!isSelected(option.value)"
                                @click="onOptionClick(option.value, addTag)"
                            >
                                {{ option.text }}
                            </b-dropdown-item-button>
    
                            <b-dropdown-text v-if="availableOptions.length === 0">
                                There are no option available to select
                            </b-dropdown-text>
                        </div>
                    </b-dropdown>
            </template>
        </b-form-tags>
    </b-form-group>
</div>
</template>

<script>
export default {
    props: {
        options: {
            type: Array,
            required: true
        },
    },
    data() {
        return {
            search: '',
            selected_value: [],
        }
    },
    computed: {
        textByValue() {
            const indexedText = {}
            this.options.forEach(option => {
                indexedText[option.value] = option.text
            });
            return indexedText
        },
        criteria() {
            return this.search.trim().toLowerCase()
        },
        availableOptions() {
            const criteria = this.criteria
            const options = this.options.filter(opt => this.selected_value.indexOf(opt.value) === -1)
            if (criteria) {
                return this.matchingOptions(options)
            }
            return options
        },
        searchDesc() {
            if (this.criteria && this.availableOptions.length === 0) {
                return 'There are no tags matching your search criteria'
            }
            return ''
        },
    },
    methods: {
        isSelected(value) {
            return this.selected_value.indexOf(value) === -1
        },
        matchingOptions(options) {
            if (!options) {
                options = this.options
            }
            return options.filter(opt => opt.value.toLowerCase().indexOf(this.criteria) > -1 || opt.text.toLowerCase().indexOf(this.criteria) > -1);
        },
        onOptionClick(selectedOption, addTag ) {
            addTag(selectedOption)
            this.search = ''
        },
        selectAll(addTag) {
            this.matchingOptions().forEach(option => {
                addTag(option.value)
            });
            this.search = ''
        },
        clearAll(removeTag) {
            this.selected_value.forEach(value => {
                removeTag(value)
            });
        }
    },
}
</script>