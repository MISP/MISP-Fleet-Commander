<template>
     <div class="d-flex flex-nowrap compact" :title="title" :style="tight ? 'line-height: 1.2' : ''">
        <span class="text-center">
            <img
                v-if="useAsset"
                class="mr-2 svgIcon"
                :src="forceWhite ? require(`@/assets/${icon}-white.svg`) : require(`@/assets/${icon}.svg`)"
                alt="Radar"
            />
            <i 
                v-else
                :class="[`fas fa-${icon}`, tight ? 'mr-1' : 'mr-2']"
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
        },
        tight: {
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