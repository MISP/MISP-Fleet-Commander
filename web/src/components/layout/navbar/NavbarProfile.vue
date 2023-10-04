<template>
    <div>
        <b-dropdown-item
            class="logout-button"
            @click="logout()"
        >
            <i class="fas fa-right-from-bracket fa-fw"></i> Logout
        </b-dropdown-item>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "NavbarProfile",
    components: {
    },
    data: function () {
        return {
        }
    },
    computed: {
    },
    methods: {
        logout() {
            this.$store.dispatch('auth/logout')
        }
    },
}
</script>

<style>
.navbar .logout-button .dropdown-item:hover {
    color: #fff;
    text-decoration: none;
    background-color: #bd2130;
}

.navbar .logout-button .dropdown-item:focus {
    color: #fff;
    text-decoration: none;
    background-color: #b21f2d;
}
</style>