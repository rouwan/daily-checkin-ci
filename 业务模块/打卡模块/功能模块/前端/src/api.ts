import type { TodayStatus } from './types'

export class ApiRequestError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

function getErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return null
  }

  const detail = payload.detail
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const firstError = detail[0]
    if (
      firstError &&
      typeof firstError === 'object' &&
      'msg' in firstError &&
      typeof firstError.msg === 'string'
    ) {
      return firstError.msg
    }
  }

  return null
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
  } catch {
    throw new ApiRequestError(
      '无法连接本地服务。请确认后端已在 8000 端口启动。',
      0,
    )
  }

  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      // 非 JSON 错误响应会使用下面的通用文案。
    }
    throw new ApiRequestError(
      getErrorMessage(payload) ?? '操作没有完成，请稍后重试。',
      response.status,
    )
  }

  return (await response.json()) as T
}

export function fetchTodayStatus(): Promise<TodayStatus> {
  return request<TodayStatus>('/api/status')
}

export function saveHabitName(name: string): Promise<TodayStatus> {
  return request<TodayStatus>('/api/habit', {
    method: 'PUT',
    body: JSON.stringify({ name }),
  })
}

export function completeToday(): Promise<TodayStatus> {
  return request<TodayStatus>('/api/check-ins/today', {
    method: 'POST',
  })
}

export function undoToday(): Promise<TodayStatus> {
  return request<TodayStatus>('/api/check-ins/today', {
    method: 'DELETE',
  })
}
