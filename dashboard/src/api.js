const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function api(path, { method = 'GET', token, body, isForm = false } = {}) {
  const headers = {}
  if (!isForm) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || data.error || 'API error')
  return data
}

export { API_BASE }
