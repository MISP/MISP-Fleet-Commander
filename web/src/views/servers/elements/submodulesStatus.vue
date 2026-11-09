<template>
    <span
        v-if="submodules !== '' && submodules !== undefined && hasSubmodules"
        class="submodules-status"
    >
        <span
            v-if="allValid"
            :class="['fas', 'fa-check', overallTone === null ? 'text-success' : toneTextClass(overallTone)]"
            :title="toneTitle(overallTone) || 'All module systems OK'"
        ></span>
        <b-badge
            v-for="module in shownModules"
            :key="module.name"
            :variant="module.badge.variant"
            :class="module.badge.class"
            :title="module.title"
        >
            <strong>{{ module.name }}</strong>
            : <small>{{ module.error }}</small>
        </b-badge>
    </span>
</template>

<script>
import { healthCellMixin, isProblem, toneBadge, toneTextClass, toneTitle } from "@/helpers/healthCells"

const MODULE_ERRORS = {
    0: "OK",
    1: "System not enabled",
    2: "No modules found",
}

export default {
    name: "submoduleStatus",
    mixins: [healthCellMixin],
    props: {
        submodules: {},
        server_id: {
            type: Number,
            default: null,
        },
    },
    computed: {
        hasSubmodules() {
            return typeof this.submodules === "object" && this.submodules !== null && Object.keys(this.submodules).length > 0
        },
        overallTone() {
            return this.healthTone(this.server_id, "modules")
        },
        // Every module system that is not plainly OK, coloured by its issue. A system that is not enabled is no
        // issue (neutral badge); without health, every one of them is a warning, as before
        shownModules() {
            if (!this.hasSubmodules) {
                return []
            }
            return Object.entries(this.submodules)
                .filter(([, status]) => status != 0)
                .map(([name, status]) => {
                    const tone = this.healthTone(this.server_id, "modules", { subject: name })
                    const known = MODULE_ERRORS[status]
                    const badge = tone === null
                        ? { variant: "warning", class: "" }
                        : (isProblem(tone) ? toneBadge(tone) : { variant: "light", class: "text-muted" })
                    return {
                        name,
                        error: known || "Unavailable",
                        badge,
                        title: [known ? null : String(status), toneTitle(tone)].filter(Boolean).join("\n"),
                    }
                })
        },
        allValid() {
            return this.overallTone === null
                ? this.shownModules.length === 0
                : !isProblem(this.overallTone)
        },
    },
    methods: {
        toneTextClass,
        toneTitle,
    },
}
</script>

<style scoped>
.submodules-status .badge {
    margin-right: 0.2rem;
}
</style>
