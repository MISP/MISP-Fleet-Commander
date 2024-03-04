<template>
    <div>
        <b-form class="mb-3" inline>
            <b-overlay
                :show="readInProgress"
                spinner-type="grow"
                :spinner-small="true"
                opacity="0.6"
                class="row col-6"
            >
                <b-form-file 
                    v-model="file"
                    @change="handleFileChange"
                ></b-form-file>
                <b-form-textarea
                    v-model="rawText"
                    class="w-100 mt-2"
                    size="sm"
                    placeholder="Enter CSV data"
                    rows="3"
                ></b-form-textarea>
            </b-overlay>

        </b-form>
        <b-form-group
            class="row col-4 mt-2"
            size="sm"
            label="CSV Delimiter"
            label-for="input-delimiter"
            description="The one-character string used to separate fields."
        >
            <b-form-input
                id="input-delimiter"
                size="sm"
                v-model="delimiter"
            ></b-form-input>
        </b-form-group>
         <b-form-checkbox
            class="ml-2"
            v-model="has_header"
        >First row is header</b-form-checkbox>

        <b-table
            striped small empty-text selectable
            selected-variant="table-none"
            tbody-tr-class="no-outline"
            ref="csvTable"
            v-if="rawText !== ''"
            :fields="getFieldList"
            :items="mappedCSV"
            @row-selected="onRowSelected"
        >
            <template v-slot:head(selected)>
                <b-form-checkbox
                    @change="setCheckOnServers"
                ></b-form-checkbox>
            </template>
            <template v-slot:cell(selected)="row">
                <b-form-checkbox
                    v-model="row.rowSelected"
                    @input="selectRow(row.rowSelected, row.index)"
                ></b-form-checkbox>
            </template>

            <template
                v-for="item in getSelectableFieldList"
                v-slot:[`head(${item.key})`]
            >
                <div :key="`header-text-${item.key}`">{{ item.label }}</div>
                <b-form-select
                    v-model="mappedFields[item.key].csvIndex"
                    :state="mappedFields[item.key].required ? mappedFields[item.key].csvIndex !== null : true"
                    :key="`header-select-${item.key}`"
                    :options="getHeaderOptions"
                    size="sm"
                    class=""
                    @change="handleSelectableFieldChange"
                ></b-form-select>
            </template>

            <template
                v-for="item in getSelectableFieldList"
                v-slot:[`cell(${item.key})`]="row"
            >
                <div :key="`cell-row-${row.rowIndex}-${item.key}`">
                    <span
                        v-if="!checkFieldValidity(item, row.value)"
                        class="text-danger"
                        style="text-decoration: line-through"
                        :title="`This value doesn't pass the validation: ${item.regex}`"
                    >
                        {{ row.value }}
                    </span>
                    <span v-else>
                        {{ row.value }}
                    </span>
                </div>
            </template>
        </b-table>
    </div>
</template>

<script>
export default {
    name: "csvReader",
    props: {
        show_table: {
            type: Boolean,
            default: true
        }
    },
    data: function() {
        return {
            readInProgress: false,
            file: null,
            fileMaxAllowedSize: 102400,
            rawText: "",
            has_header: true,
            defaultHeader: ["name", "Comment", "url", "skip_ssl", "authkey"],
            delimiter: ",",
            mappedFields: {
                name: {label: "Name", csvIndex: null, required: true},
                comment: {label: "Comment", csvIndex: null, required: false},
                url: {label: "URL", csvIndex: null, required: true, regex:/^(ftp|http|https):\/\/[^ "]+$/},
                skip_ssl: {label: "Skip SSL", csvIndex: null, required: false, castFun: (v) => { return (v === 'true' || v === '1') ? true : false }},
                authkey: {label: "Authkey", csvIndex: null, required: true, regex:/^[a-zA-Z0-9]{40}$/},
            },
            csvHeader:"",
            speratedCSV: [],
            selectedServers: []
        }
    },
    computed: {
        getHeaderOptions() {
            let header = this.csvHeader.split(this.delimiter)
            header = header.map((str) => {
                return str.startsWith('"') && str.endsWith('"') ? str.slice(1, -1) : str
            })
            let headerOptions = header.map((field, index) => {
                return {value: index, text: field}
            })
            headerOptions.push({ value: null, text: "Pick a column" })
            return headerOptions
        },
        getRemainingHeaderOptions() {
            return this.getHeaderOptions
        },
        getSelectableFieldList() {
            return Object.entries(this.mappedFields).map(([key, value]) => {
                return {key: key, ...value}
            })
        },
        getFieldList() {
            let fields = this.getSelectableFieldList.slice()
            fields.unshift({
                key: "selected",
                label: "",
            })
            return fields
        },
        mappedCSV() {
            let items = []
            this.speratedCSV.forEach(csvLineArray => {
                let row = {}
                Object.entries(this.mappedFields).map(([field_name, field_config]) => {
                    if (Number.isInteger(field_config.csvIndex)) {
                        row[field_name] = csvLineArray[field_config.csvIndex]
                        if (field_config.castFun) {
                            row[field_name] = field_config.castFun(row[field_name])
                        }
                    }
                })
                if (Object.keys(row).length > 0) {
                    items.push(row)
                }
            })
            return items
        }
    },
    methods: {
        setCheckOnServers(checked) {
            if (checked) {
                this.$refs.csvTable.selectAllRows()
            } else {
                this.$refs.csvTable.clearSelected()
            }
        },
        onRowSelected(items) {
            this.selectedServers = items
            this.$emit("update:selectedServers", this.selectedServers)
        },
        selectRow(checked, index) {
            if (checked) {
                this.$refs.csvTable.selectRow(index)
            } else {
                this.$refs.csvTable.unselectRow(index)
            }
        },
        handleFileChange(event) {
            const file = event.target.files[0]
            this.readFile(file)
                .then((result) => {
                    this.rawText = result
                })
                // .catch((error) => {
                // })
                // .finally(() => {
                // })
        },
        readFile(file) {
            return new Promise((resolve, reject) => {
                if (file.size > this.fileMaxAllowedSize) {
                    this.$bvToast.toast(`File is larger than the accepted maximum size (${file.size} > ${this.fileMaxAllowedSize} Bytes)`, {
                        title: "Error while parsing the CSV file",
                        variant: "warning",
                    })
                    this.reject("File is larger than the accepted maximum size")
                } else {
                    const reader = new FileReader()
                    reader.onloadstart = () => {
                        this.readInProgress = true
                    }
                    reader.onloadend = () => {
                        this.readInProgress = false
                    }
                    reader.onload = () => {
                        resolve(reader.result)
                    }
                    reader.onerror = () => {
                        reject("error")
                    }
                    reader.readAsText(file)
                }
            })
        },
        autoPickMapping() {
            const tableHeader = this.defaultHeader
            Object.keys(this.mappedFields).forEach((field_name) => {
                this.mappedFields[field_name].csvIndex = null
            })
            this.getHeaderOptions.forEach((option, i) => {
                if (tableHeader.indexOf(option.text) >= 0) {
                    this.mappedFields[option.text].csvIndex = i
                }
            })
            this.handleSelectableFieldChange()
        },
        updateAfterRead() {
            let csvLines = this.rawText.trim().split(/\r?\n/)
            if (this.has_header) {
                this.csvHeader = csvLines[0]
                csvLines = csvLines.splice(1)
            } else {
                this.csvHeader = csvLines[0]
            }
            let tmpCsv = []
            csvLines.forEach(line => {
                let list = line.split(this.delimiter)
                list = list.map((str) => {
                    return str.startsWith('"') && str.endsWith('"') ? str.slice(1, -1) : str
                })
                tmpCsv.push(list)
            })
            this.speratedCSV = tmpCsv
            this.autoPickMapping()
        },
        checkFieldValidity(fieldConfig, value) {
            return fieldConfig.regex ? fieldConfig.regex.test(value) : true
        },
        handleSelectableFieldChange() {
            const allRequiredFields = Object.entries(this.mappedFields)
                // eslint-disable-next-line no-unused-vars
                .filter(([fieldName, field]) => { return field.required && field.csvIndex === null })
                .filter(([fieldName, field]) => { 
                    if (!field.regex) {
                        return true
                    }
                    for (let i = 0; i < this.mappedCSV.length; i++) {
                        const value = this.mappedCSV[i];
                        if (!this.checkFieldValidity(field, value)) {
                            return false
                        }
                    }
                    return true
                })
            this.$emit("update:allRequiredFieldsPicked", allRequiredFields.length == 0 )
        }
    },
    watch: {
        has_header: function() {
            this.updateAfterRead()
        },
        rawText: function() {
            this.updateAfterRead()
        },
    }
}
</script>

<style scoped>

</style>