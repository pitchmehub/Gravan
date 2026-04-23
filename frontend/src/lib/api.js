/**
 * Cliente HTTP para a API Flask — com trat. de 401 e hardening.
 */
import { supabase } from './supabase'

const BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL

async function getJwt() {
  const { data } = await supabase.auth.getSession()
  return data?.session?.access_token ?? null
}

async function request(method, path, { body, isFormData = false } = {}) {
  // Valida path: não pode conter quebras de linha nem caracteres bizarros
  if (typeof path !== 'string' || /[\r\n\t]/.test(path)) {
    throw new Error('Requisição inválida.')
  }

  const jwt = await getJwt()
  const headers = {}
  if (jwt) headers['Authorization'] = `Bearer ${jwt}`
  if (!isFormData && body !== undefined) headers['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'omit', // Não enviamos cookies — usamos JWT apenas
    })
  } catch (e) {
    throw new Error('Servidor inacessível. Verifique se o backend está rodando.')
  }

  // Sessão expirada: força logout e redirect
  if (res.status === 401) {
    await supabase.auth.signOut().catch(() => {})
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login?expirado=1'
    }
    throw new Error('Sessão expirada. Faça login novamente.')
  }

  // Rate limit
  if (res.status === 429) {
    throw new Error('Muitas tentativas em curto espaço de tempo. Aguarde e tente novamente.')
  }

  const text = await res.text()
  let json = {}
  try { json = text ? JSON.parse(text) : {} } catch {}

  if (!res.ok) {
    const msg = json.error || json.description || json.message || `Erro ${res.status}`
    throw new Error(msg)
  }
  return json
}

export const api = {
  request,
  get:    (path)       => request('GET',    path),
  post:   (path, body) => request('POST',   path, { body }),
  put:    (path, body) => request('PUT',    path, { body }),
  patch:  (path, body) => request('PATCH',  path, { body }),
  delete: (path)       => request('DELETE', path),
  upload: (path, form) => request('POST',   path, { body: form, isFormData: true }),
  // Download de arquivos binários (PDF, etc.) com JWT
  download: async (path, filename) => {
    const jwt = await getJwt()
    const res = await fetch(`${BASE}${path}`, {
      headers: jwt ? { Authorization: `Bearer ${jwt}` } : {},
      credentials: 'omit',
    })
    if (res.status === 429) {
      throw new Error('Limite de 10 downloads por hora atingido. Tente novamente mais tarde.')
    }
    if (!res.ok) {
      const t = await res.text().catch(() => '')
      throw new Error(`Erro ${res.status}: ${t || 'falha no download'}`)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'download'
    document.body.appendChild(a)
    a.click()
    setTimeout(() => { URL.revokeObjectURL(url); a.remove() }, 200)
  },
}
