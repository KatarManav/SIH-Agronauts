const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').trim().replace(/\/+$/, '')

export class RemoteApiError extends Error {
  constructor(message, details = {}) {
    super(message)
    this.name = 'RemoteApiError'
    Object.assign(this, details)
  }
}

export async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 12000)
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    })
    const text = await response.text()
    let payload = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        throw new RemoteApiError('The FastAPI service returned an invalid response.', {
          code: 'INVALID_RESPONSE',
          status: response.status,
          path,
        })
      }
    }
    if (!response.ok) {
      throw new RemoteApiError(
        payload?.error?.message || payload?.detail?.message || payload?.detail || `Request failed (${response.status})`,
        { code: payload?.error?.code || 'REMOTE_REQUEST_FAILED', status: response.status, path },
      )
    }
    return payload
  } catch (error) {
    if (error instanceof RemoteApiError) throw error
    if (error.name === 'AbortError') throw new RemoteApiError('The request timed out.', { code: 'TIMEOUT', path })
    throw new RemoteApiError('Unable to connect to the FastAPI service.', { code: 'NETWORK_ERROR', path })
  } finally {
    clearTimeout(timeout)
  }
}

export const apiClient = {
  get: (path, options) => request(path, options),
  post: (path, body, options = {}) => request(path, { ...options, method: 'POST', body }),
  baseUrl,
}
