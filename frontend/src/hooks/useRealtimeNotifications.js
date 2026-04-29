/**
 * Hook que escuta inserções e atualizações na tabela `notificacoes`
 * pelo Supabase Realtime, eliminando a necessidade de polling agressivo.
 *
 * Uso:
 *   useRealtimeNotifications(perfilId, () => recarregar())
 */
import { useEffect, useRef } from 'react'
import { supabase } from '../lib/supabase'

export default function useRealtimeNotifications(perfilId, onChange) {
  const cbRef = useRef(onChange)
  cbRef.current = onChange

  useEffect(() => {
    if (!perfilId) return

    // Remove qualquer canal com o mesmo nome antes de criar um novo
    // (evita o erro "cannot add callbacks after subscribe()" no StrictMode)
    const topic = `realtime:notif:${perfilId}`
    const existing = supabase.getChannels().find(c => c.topic === topic)
    if (existing) {
      supabase.removeChannel(existing).catch(() => {})
    }

    const channel = supabase
      .channel(`notif:${perfilId}`)
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'notificacoes', filter: `perfil_id=eq.${perfilId}` },
        () => { cbRef.current && cbRef.current('insert') }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'notificacoes', filter: `perfil_id=eq.${perfilId}` },
        () => { cbRef.current && cbRef.current('update') }
      )
      .on(
        'postgres_changes',
        { event: 'DELETE', schema: 'public', table: 'notificacoes', filter: `perfil_id=eq.${perfilId}` },
        () => { cbRef.current && cbRef.current('delete') }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel).catch(() => {})
    }
  }, [perfilId])
}
