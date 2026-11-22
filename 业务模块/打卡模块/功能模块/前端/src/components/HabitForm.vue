<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from 'vue'

const props = defineProps<{
  initialName?: string
  busy?: boolean
  focusOnMount?: boolean
  externalError?: string
}>()

const emit = defineEmits<{
  submit: [name: string]
  cancel: []
}>()

const inputId = useId()
const hintId = useId()
const errorId = useId()
const name = ref(props.initialName ?? '')
const localError = ref('')
const input = ref<HTMLInputElement | null>(null)
const visibleError = computed(
  () => localError.value || props.externalError || '',
)
const characterCount = computed(() => name.value.trim().length)

onMounted(async () => {
  if (!props.focusOnMount) return
  await nextTick()
  input.value?.focus()
  input.value?.select()
})

watch(
  [() => props.externalError, () => props.busy],
  async ([error, busy]) => {
    if (!error || busy) return
    await nextTick()
    input.value?.focus()
  },
)

function submit() {
  const normalized = name.value.trim()
  if (!normalized) {
    localError.value = '请输入习惯名称。'
    input.value?.focus()
    return
  }
  if (normalized.length > 40) {
    localError.value = '习惯名称不能超过 40 个字符。'
    input.value?.focus()
    return
  }

  localError.value = ''
  emit('submit', normalized)
}

function clearError() {
  if (localError.value) localError.value = ''
}
</script>

<template>
  <form class="habit-form" novalidate @submit.prevent="submit">
    <label class="habit-label" :for="inputId">习惯名称</label>
    <div class="input-row">
      <input
        :id="inputId"
        ref="input"
        v-model="name"
        name="habit-name"
        type="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="例如：读书半小时…"
        :aria-invalid="visibleError ? 'true' : 'false'"
        :aria-describedby="`${hintId}${visibleError ? ` ${errorId}` : ''}`"
        :disabled="busy"
        @input="clearError"
      />
      <button class="primary-button" type="submit" :disabled="busy">
        {{ busy ? '正在保存…' : '保存名称' }}
      </button>
    </div>
    <div class="form-meta">
      <p :id="hintId" class="field-hint">去除首尾空白后需为 1–40 个字符。</p>
      <span class="character-count" aria-hidden="true">
        {{ characterCount }}/40
      </span>
    </div>
    <p v-if="visibleError" :id="errorId" class="field-error" role="alert">
      {{ visibleError }}
    </p>
    <button
      v-if="initialName"
      class="text-button form-cancel"
      type="button"
      :disabled="busy"
      @click="emit('cancel')"
    >
      取消修改
    </button>
  </form>
</template>
