import { isFinalJob } from "@/helpers/jobs"

// For modals that start a job on the selected servers (`server_ids` prop): the job they follow, and a promise that
// settles when it ends, so that the submitting form stays busy meanwhile. A new selection forgets the job (it keeps
// running, and is announced when it ends)
export default {
    data() {
        return {
            jobId: null,
            jobWatchers: [],
        }
    },
    computed: {
        job() {
            return this.jobId === null ? null : this.$store.getters["jobs/job"](this.jobId)
        },
    },
    watch: {
        server_ids(newIDs, oldIDs) {
            if (newIDs.length !== oldIDs.length || newIDs.some((id, index) => id !== oldIDs[index])) {
                this.jobId = null
            }
        },
    },
    methods: {
        startJob(payload) {
            return this.$store.dispatch("jobs/create", payload)
                .then((job) => {
                    this.jobId = job.id
                    return this.whenJobEnds(job.id)
                })
                .catch((error) => {
                    this.$bvToast.toast(error, { title: "Could not start the job", variant: "danger" })
                })
        },
        followJob(job) {
            this.jobId = job.id
        },
        whenJobEnds(job_id) {
            return new Promise((resolve) => {
                const ended = () => isFinalJob(this.$store.getters["jobs/job"](job_id))
                if (ended()) {
                    resolve()
                    return
                }
                const unwatch = this.$store.watch(ended, (isOver) => {
                    if (isOver) {
                        unwatch()
                        this.jobWatchers = this.jobWatchers.filter(fn => fn !== unwatch)
                        resolve()
                    }
                })
                this.jobWatchers.push(unwatch)
            })
        },
    },
    beforeDestroy() {
        this.jobWatchers.forEach(unwatch => unwatch())
    },
}
