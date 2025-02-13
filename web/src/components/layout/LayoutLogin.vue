<template>
    <div class="main main-login">
        <div class="app app-login">
            <slot/>
        </div>
    </div>
</template>

<script>
// @ is an alias to /src
import { mapState } from "vuex"

export default {
    name: "LayoutLogin",
    components: {
    },
    data () {
        return {
            layout: "div"
        }
    },
    computed: {
        ...mapState({
        }),
    }
}
</script>
