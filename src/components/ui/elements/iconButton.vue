<template>
     <div class="d-flex flex-nowrap compact" :title="title">
        <span class="text-center">
            <img
                v-if="useAsset"
                class="mr-2 svgIcon"
                :src="forceWhite ? require(`@/assets/${icon}-white.svg`) : require(`@/assets/${icon}.svg`)"
                alt="Radar"
            />
            <i 
                v-else
                :class="`mr-2 fas fa-${icon}`"
            ></i>
        </span>
        <span :class="['text-nowrap', forceWhite ? 'text-white' : '']">
            {{ text }}
        </span>
    </div>
</template>

<script>
export default {
    name: "iconButton",
    props: {
        text: {
            type: String,
        },
        title: {
            type: String,
            default: function() { return "" }
        },
        icon: {
            type: String,
        },
        useAsset: {
            type: Boolean,
            default: false
        },
        forceWhite: {
            type: Boolean,
            default: false
        }
    }
}
</script>

<style scoped>
.compact i.fas, .compact img.svgIcon {
    width: 20px;
}
</style>