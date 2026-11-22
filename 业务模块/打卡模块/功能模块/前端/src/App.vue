<script setup lang="ts">
import { computed, nextTick, onMounted, ref, shallowRef } from 'vue'

import {
  completeToday,
  fetchTodayStatus,
  saveHabitName,
  undoToday,
} from './api'
import HabitForm from './components/HabitForm.vue'
import TodayMark from './components/TodayMark.vue'
import type { TodayStatus } from './types'

const status = shallowRef<TodayStatus | null>(null)
const loading = ref(true)
const loadError = ref('')
const formError = ref('')
const actionError = ref('')
const feedback = ref('')
const editingHabit = ref(false)
const savingHabit = ref(false)
const confirmingUndo = ref(false)
const action = ref<'check-in' | 'undo' | null>(null)
const heading = ref<HTMLElement | null>(null)
const todayMark = ref<{ focusAction: () => void } | null>(null)
const undoTrigger = ref<HTMLButtonElement | null>(null)
const undoKeepButton = ref<HTMLButtonElement | null>(null)

const isBusy = computed(
  () => savingHabit.value || action.value !== null,
)
const formattedDate = computed(() => {
  if (!status.value) return ''
  const date = new Date(`${status.value.date}T12:00:00`)
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(date)
})
const statusSentence = computed(() => {
  if (!status.value) return ''
  if (status.value.checked_in_today) {
    return '今天已经完成。'
  }
  if (status.value.current_streak > 0) {
    return '今天还没打卡，之前的连续记录仍然保留。'
  }
  return '今天是新的开始。'
})

async function loadStatus() {
  loading.value = true
  loadError.value = ''
  feedback.value = ''
  try {
    status.value = await fetchTodayStatus()
  } catch (error) {
    loadError.value =
      error instanceof Error ? error.message : '读取失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function focusHeading() {
  void nextTick(() => heading.value?.focus())
}

async function submitHabit(name: string) {
  savingHabit.value = true
  formError.value = ''
  feedback.value = ''
  try {
    status.value = await saveHabitName(name)
    editingHabit.value = false
    feedback.value = '习惯名称已保存。'
    focusHeading()
  } catch (error) {
    formError.value =
      error instanceof Error ? error.message : '保存失败，请稍后重试。'
  } finally {
    savingHabit.value = false
  }
}

function startEditing() {
  formError.value = ''
  feedback.value = ''
  editingHabit.value = true
}

function cancelEditing() {
  editingHabit.value = false
  formError.value = ''
  focusHeading()
}

async function checkIn() {
  action.value = 'check-in'
  actionError.value = ''
  feedback.value = ''
  let completed = false
  try {
    status.value = await completeToday()
    feedback.value = '今天已打卡。'
    completed = true
  } catch (error) {
    actionError.value =
      error instanceof Error ? error.message : '打卡失败，请稍后重试。'
  } finally {
    action.value = null
  }
  if (completed) {
    await nextTick()
    undoTrigger.value?.focus()
  }
}

async function askToUndo() {
  actionError.value = ''
  feedback.value = ''
  confirmingUndo.value = true
  await nextTick()
  undoKeepButton.value?.focus()
}

async function cancelUndo() {
  confirmingUndo.value = false
  await nextTick()
  undoTrigger.value?.focus()
}

async function confirmUndo() {
  action.value = 'undo'
  actionError.value = ''
  try {
    status.value = await undoToday()
    confirmingUndo.value = false
    feedback.value = '已撤销今天的打卡。'
    await nextTick()
    todayMark.value?.focusAction()
  } catch (error) {
    actionError.value =
      error instanceof Error ? error.message : '撤销失败，请稍后重试。'
  } finally {
    action.value = null
  }
}

onMounted(loadStatus)
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>

  <div class="page-shell">
    <header class="site-header">
      <span class="wordmark">一日</span>
      <span class="header-note">一个习惯，只记今天</span>
    </header>

    <main id="main-content" class="main-content" tabindex="-1">
      <section v-if="loading" class="loading-state" aria-live="polite">
        <span class="loading-dot" aria-hidden="true"></span>
        <p>正在读取今天的状态…</p>
      </section>

      <section v-else-if="loadError" class="error-state">
        <p class="eyebrow">连接未完成</p>
        <h1>暂时读不到今天。</h1>
        <p class="supporting-copy">{{ loadError }}</p>
        <button class="primary-button" type="button" @click="loadStatus">
          重新连接
        </button>
      </section>

      <section
        v-else-if="status && !status.habit"
        class="setup-view"
        aria-labelledby="setup-title"
      >
        <div class="setup-copy">
          <p class="eyebrow">从今天开始</p>
          <h1 id="setup-title">每天，只做一件事。</h1>
          <p class="supporting-copy">
            先写下你要坚持的习惯。之后每天回来，只需要回答“今天做了吗”。
          </p>
        </div>
        <div class="setup-form-panel">
          <HabitForm
            :busy="savingHabit"
            :external-error="formError"
            @submit="submitHabit"
          />
        </div>
      </section>

      <section
        v-else-if="status?.habit"
        class="daily-view"
        aria-labelledby="habit-heading"
      >
        <div class="daily-copy">
          <p class="date-line">{{ formattedDate }}</p>
          <div class="habit-title-row">
            <h1
              id="habit-heading"
              ref="heading"
              class="habit-heading"
              tabindex="-1"
            >
              {{ status.habit.name }}
            </h1>
            <button
              v-if="!editingHabit"
              class="text-button"
              type="button"
              :disabled="isBusy"
              @click="startEditing"
            >
              修改名称
            </button>
          </div>
          <p class="status-sentence">{{ statusSentence }}</p>

          <div v-if="editingHabit" class="edit-panel">
            <HabitForm
              :initial-name="status.habit.name"
              :busy="savingHabit"
              :external-error="formError"
              :focus-on-mount="true"
              @submit="submitHabit"
              @cancel="cancelEditing"
            />
          </div>
        </div>

        <div class="daily-action">
          <TodayMark
            ref="todayMark"
            :checked-in="status.checked_in_today"
            :streak="status.current_streak"
            :busy="action === 'check-in'"
            @complete="checkIn"
          />

          <div
            v-if="status.checked_in_today && !confirmingUndo"
            class="undo-entry"
          >
            <button
              ref="undoTrigger"
              class="text-button text-button--quiet"
              type="button"
              :disabled="isBusy"
              @click="askToUndo"
            >
              撤销今天的打卡
            </button>
          </div>

          <div
            v-else-if="confirmingUndo"
            class="undo-confirm"
            role="group"
            aria-label="确认撤销今天打卡"
          >
            <p>撤销后，今天会回到未完成状态。</p>
            <div class="undo-actions">
              <button
                ref="undoKeepButton"
                class="secondary-button"
                type="button"
                :disabled="action === 'undo'"
                @click="cancelUndo"
              >
                保留打卡
              </button>
              <button
                class="danger-button"
                type="button"
                :disabled="action === 'undo'"
                @click="confirmUndo"
              >
                {{ action === 'undo' ? '正在撤销…' : '确认撤销' }}
              </button>
            </div>
          </div>
        </div>

        <p v-if="actionError" class="action-message error-message" role="alert">
          {{ actionError }}
        </p>
        <p class="action-message" role="status" aria-live="polite">
          {{ feedback }}
        </p>
      </section>
    </main>

    <footer class="site-footer">
      <span>数据保存在这台电脑</span>
      <span aria-hidden="true">·</span>
      <span>只记录每日是否完成</span>
    </footer>
  </div>
</template>
