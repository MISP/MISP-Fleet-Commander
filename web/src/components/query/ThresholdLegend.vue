<template>
    <ul class="threshold-legend">
        <li>
            <svg width="20" height="8" aria-hidden="true"><line x1="1" y1="4" x2="19" y2="4" class="legend-line" /></svg>
            {{ threshold.text }}
        </li>
        <li v-if="threshold.side">
            <span :class="['legend-zone', `tone-${threshold.tone}`]" aria-hidden="true"></span>
            Not as expected
        </li>
    </ul>
</template>

<script>
// What the dashed line and the tint of a saved query's charts mean, said once above them
export default {
    name: "ThresholdLegend",
    props: {
        // `{ text, side, tone }`, as `thresholdOf` gives it with the saved query's tone
        threshold: { type: Object, required: true },
    },
}
</script>

<style scoped>
.threshold-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
    color: #52514e;
    font-size: 0.8rem;
}

.threshold-legend li {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.legend-line {
    stroke: #52514e;
    stroke-width: 1;
    stroke-dasharray: 4 3;
}

.legend-zone {
    display: inline-block;
    width: 14px;
    height: 10px;
    border-radius: 2px;
    background: rgba(255, 193, 7, 0.22);
}

.legend-zone.tone-critical {
    background: rgba(220, 53, 69, 0.16);
}

.legend-zone.tone-info {
    background: rgba(23, 162, 184, 0.18);
}
</style>
