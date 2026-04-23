import React, { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(undefined)
  const [perfil,  setPerfil]  = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) { setUser(session.user); fetchPerfil(session.user.id) }
      else { setUser(null); setLoading(false) }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        setUser(session.user); fetchPerfil(session.user.id)
      } else if (event === 'SIGNED_OUT') {
        setUser(null); setPerfil(null); setLoading(false)
      }
    })
    return () => subscription.unsubscribe()
  }, [])

  async function fetchPerfil(userId) {
    try {
      const { data } = await supabase
        .from('perfis')
        .select('*, wallets(saldo_cents)')
        .eq('id', userId)
        .single()
      if (data) setPerfil(data)
    } catch (_) {}
    finally { setLoading(false) }
  }

  async function refreshPerfil() {
    if (user?.id) await fetchPerfil(user.id)
  }

  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
        // Força o Google a sempre mostrar o seletor de contas,
        // mesmo que o usuário já tenha uma sessão ativa no navegador.
        queryParams: {
          prompt: 'select_account',
          access_type: 'offline',
        },
      },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
    // Redireciona para a landing page
    if (typeof window !== 'undefined') {
      window.location.href = '/'
    }
  }

  if (loading && user === undefined) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#71717A' }}>Carregando…</div>
  }

  return (
    <AuthContext.Provider value={{ user, perfil, loading, signInWithGoogle, signOut, refreshPerfil }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
