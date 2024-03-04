<template>
  
</template>

<script>
export default {
    name: "UserSetPassword",
    components: {
    },
    props: {
        user: {
            required: true,
            type: Object
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            postInProgress: false,
            form: {
                password: '',
                password_confirm: '',
            }
        }
    },
    computed: {
    },
    methods: {
    }
}
</script>

<style>

</style>