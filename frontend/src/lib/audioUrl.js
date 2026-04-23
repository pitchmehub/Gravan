import { supabase } from '../lib/supabase'

const cache = new Map()

export async function getAudioUrl(audioPath) {
  if (!audioPath) return null

  // Cache em memória por 50 minutos (URLs duram 1h)
  if (cache.has(audioPath)) {
    const { url, expires } = cache.get(audioPath)
    if (Date.now() < expires) return url
  }

  const { data, error } = await supabase.storage
    .from('obras-audio')
    .createSignedUrl(audioPath, 3600) // 1 hora

  if (error || !data?.signedUrl) return null

  cache.set(audioPath, {
    url:     data.signedUrl,
    expires: Date.now() + 50 * 60 * 1000,
  })

  return data.signedUrl
}
