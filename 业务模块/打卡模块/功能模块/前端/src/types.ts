export interface Habit {
  name: string
}

export interface TodayStatus {
  habit: Habit | null
  date: string
  checked_in_today: boolean
  current_streak: number
}
