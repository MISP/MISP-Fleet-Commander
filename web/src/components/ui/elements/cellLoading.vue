<template>
    <div class="align-middle h-100">
        <b-progress 
            :value="100" 
            :style="pStyle"
            striped animated
            variant="secondary"
        ></b-progress>
    </div>
</template>

<script>
export default {
    name: "CellLoading",
    props: {
        height: {
            type: String,
            default: "0.5rem"
        },
        width: {
            type: String,
            default: ""
        },
        maxWidth: {
            type: String,
            default: "120px"
        }
    },
    computed: {
        pStyle: function() {
            let style = {
                height: this.height,
                width: this.width,
                "max-width": this.maxWidth
            }
            return style
        }
    }
}
</script>

<style scoped>
</style>
