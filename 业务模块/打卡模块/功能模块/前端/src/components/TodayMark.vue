<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  checkedIn: boolean
  streak: number
  busy: boolean
}>()

const emit = defineEmits<{
  complete: []
}>()
const sealButton = ref<HTMLButtonElement | null>(null)

const actionLabel = computed(() => {
  if (props.busy) return '正在打卡…'
  return props.checkedIn ? '今天已完成' : '完成今天'
})

const buttonLabel = computed(() => {
  if (props.checkedIn) {
    return `今天已打卡，当前连续 ${props.streak} 天`
  }
  return '完成今天打卡'
})

function focusAction() {
  sealButton.value?.focus()
}

defineExpose({ focusAction })
</script>

<template>
  <section class="today-mark" aria-labelledby="mark-title">
    <div class="mark-and-streak">
      <div class="streak" role="group" aria-label="当前连续天数">
        <span class="streak-label">当前连续</span>
        <span class="streak-value">{{ streak }}</span>
        <span class="streak-unit">天</span>
      </div>

      <button
        id="mark-title"
        ref="sealButton"
        class="seal"
        :class="{ 'seal--done': checkedIn }"
        type="button"
        :disabled="checkedIn || busy"
        :aria-busy="busy"
        :aria-label="buttonLabel"
        @click="emit('complete')"
      >
        <span class="seal-ring" aria-hidden="true"></span>
        <svg
          v-if="checkedIn"
          class="seal-check"
          viewBox="0 0 64 64"
          aria-hidden="true"
        >
          <path d="M15 33.5 27.5 46 50 20" />
        </svg>
        <span v-else class="seal-character" aria-hidden="true">记</span>
        <span class="seal-label">{{ actionLabel }}</span>
      </button>
    </div>
    <p class="mark-hint">
      {{
        checkedIn
          ? '今天已经留下记号。明天再回来继续。'
          : '一次点击，只记录今天。'
      }}
    </p>
  </section>
</template>
