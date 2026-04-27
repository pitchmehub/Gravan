import { useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { isPushSupported, getPushStatus, subscribePush } from '../lib/push'

const STORAGE_KEY = 'gravan_push_auto_asked_v1'

export default function PushAutoEnable() {
  const { user } = useAuth()

  useEffect(() => {
    if (!user) return
    if (!isPushSupported()) return

    let cancelled = false

    const run = async () => {
      try {
        const s = await getPushStatus()
        if (cancelled) return
        if (s.subscribed) return
        if (s.permission === 'denied') return

        if (s.permission === 'granted') {
          await subscribePush().catch(() => {})
          return
        }

        const asked = localStorage.getItem(STORAGE_KEY)
        if (asked) return
        localStorage.setItem(STORAGE_KEY, String(Date.now()))

        await new Promise(r => setTimeout(r, 1800))
        if (cancelled) return
        await subscribePush().catch(() => {})
      } catch {}
    }

    run()
    return () => { cancelled = true }
  }, [user?.id])

  return null
}
