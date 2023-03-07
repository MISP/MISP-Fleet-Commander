<template>
<i :class="['fa', value ? 'fa-check' : 'fa-times']"></i>
</template>

<script>
export default {
  name: 'BooleanIcon',
  props: {
    value: {
      type: Boolean,
      required: true
    }
  }
}
</script>

<style scoped>
i.fa-check {
    color: green
}

i.fa-times {
    color: red
}
</style>
