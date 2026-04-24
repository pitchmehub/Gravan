import React, { useEffect, useState } from 'react'
  import { useNavigate, useSearchParams } from 'react-router-dom'
  import { useAuth } from '../contexts/AuthContext'
  import { supabase } from '../lib/supabase'
  import GravanLogo from '../components/GravanLogo'

  import './Login.css'

  export default function Login() {
    const { user, signInWithGoogle, loading } = useAuth()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    const [aba,        setAba]        = useState(searchParams.get('cadastro') === '1' ? 'cadastrar' : 'entrar')
    const [form,       setForm]       = useState({
      email: '', senha: '', confirmar_senha: '', nome: '', aceite_termos: false,
    })
    const [erro,     setErro]    = useState('')
    const [sucesso,  setSucesso] = useState('')
    const [enviando, setEnviando]= useState(false)

    useEffect(() => {
      if (!loading && user) navigate('/descoberta', { replace: true })
    }, [user, loading, navigate])

    function handleChange(e) {
      const { name, value, type, checked } = e.target
      setForm(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
      setErro('')
    }

    async function handleLogin(e) {
      e.preventDefault(); setErro(''); setEnviando(true)
      const { error } = await supabase.auth.signInWithPassword({ email: form.email, password: form.senha })
      if (error) setErro('Email ou senha incorretos.')
      setEnviando(false)
    }

    async function handleCadastro(e) {
      e.preventDefault(); setErro('')
      if (!form.nome.trim())        { setErro('Nome é obrigatório.'); return }
      if (!form.email.trim())       { setErro('Email é obrigatório.'); return }
      if (form.senha.length < 6)    { setErro('A senha deve ter no mínimo 6 caracteres.'); return }
      if (form.senha !== form.confirmar_senha) { setErro('As senhas não coincidem.'); return }
      if (!form.aceite_termos)      { setErro('Você precisa aceitar os Termos para criar a conta.'); return }

      setEnviando(true)
      const { error } = await supabase.auth.signUp({
        email: form.email,
        password: form.senha,
        options: {
          data: {
            full_name: form.nome.trim(),
            aceite_termos_em: new Date().toISOString(),
            // role NÃO é definido aqui — o usuário escolhe em EscolherTipoPerfil após o login
          },
        },
      })
      if (error) {
        setErro(error.message.includes('already registered') ? 'Email já cadastrado. Tente fazer login.' : error.message)
      } else {
        setSucesso('Conta criada! Verifique seu email para confirmar o cadastro.')
        setForm({ email:'', senha:'', confirmar_senha:'', nome:'', aceite_termos: false })
      }
      setEnviando(false)
    }

    return (
      <div className="login-root">
        <div className="login-card">
          <div className="login-logo">
            <GravanLogo height={56} />
          </div>
          <p className="login-tagline">Plataforma de composições musicais</p>

          <div className="login-tabs">
            <button className={`login-tab ${aba==='entrar'?'active':''}`}
                    onClick={()=>{setAba('entrar');setErro('');setSucesso('')}}>Entrar</button>
            <button className={`login-tab ${aba==='cadastrar'?'active':''}`}
                    onClick={()=>{setAba('cadastrar');setErro('');setSucesso('')}}>Criar conta</button>
          </div>

          {aba === 'entrar' && (
            <form onSubmit={handleLogin} className="login-form">
              <div className="login-field">
                <label>Email</label>
                <input name="email" type="email" required placeholder="seu@email.com" value={form.email} onChange={handleChange}/>
              </div>
              <div className="login-field">
                <label>Senha</label>
                <input name="senha" type="password" required placeholder="••••••••" value={form.senha} onChange={handleChange}/>
              </div>
              {erro && <div className="login-erro">{erro}</div>}
              <button type="submit" className="login-btn-primary" disabled={enviando}>{enviando?'Entrando…':'Entrar'}</button>
              <div className="login-divisor"><span>ou</span></div>
              <button type="button" className="login-btn-google" onClick={signInWithGoogle}>
                <GoogleIcon/> Entrar com Google
              </button>
            </form>
          )}

          {aba === 'cadastrar' && (
            <form onSubmit={handleCadastro} className="login-form">
              <div className="login-field">
                <label>Nome completo *</label>
                <input name="nome" type="text" required placeholder="Seu nome completo" value={form.nome} onChange={handleChange}/>
              </div>
              <div className="login-field">
                <label>Email *</label>
                <input name="email" type="email" required placeholder="seu@email.com" value={form.email} onChange={handleChange}/>
              </div>
              <div className="login-grid-2">
                <div className="login-field">
                  <label>Senha *</label>
                  <input name="senha" type="password" required placeholder="Mínimo 6 caracteres" value={form.senha} onChange={handleChange}/>
                </div>
                <div className="login-field">
                  <label>Confirmar senha *</label>
                  <input name="confirmar_senha" type="password" required placeholder="Repita a senha" value={form.confirmar_senha} onChange={handleChange}/>
                </div>
              </div>

              {erro    && <div className="login-erro">{erro}</div>}
              {sucesso && <div className="login-sucesso">{sucesso}</div>}

              <label style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '12px 0 4px', fontSize: 13, color: 'var(--text-secondary)',
                cursor: 'pointer', lineHeight: 1.5,
              }}>
                <input type="checkbox" name="aceite_termos"
                       checked={form.aceite_termos} onChange={handleChange}
                       style={{ marginTop: 3, accentColor: '#0C447C', cursor: 'pointer', flexShrink: 0 }}/>
                <span>
                  Li e concordo com os{' '}
                  <a href="/termos" target="_blank" rel="noopener" style={{ color: 'var(--brand)', fontWeight: 600 }}>Termos de Uso</a>,{' '}
                  <a href="/privacidade" target="_blank" rel="noopener" style={{ color: 'var(--brand)', fontWeight: 600 }}>Política de Privacidade</a>{' '}
                  e{' '}
                  <a href="/direitos-autorais" target="_blank" rel="noopener" style={{ color: 'var(--brand)', fontWeight: 600 }}>Direitos Autorais</a>.
                </span>
              </label>

              <button type="submit" className="login-btn-primary"
                      disabled={enviando || !form.aceite_termos}>
                {enviando?'Criando conta…':'Criar conta'}
              </button>
              <div className="login-divisor"><span>ou</span></div>
              <button type="button" className="login-btn-google" onClick={signInWithGoogle}>
                <GoogleIcon/> Cadastrar com Google
              </button>
            </form>
          )}
        </div>
      </div>
    )
  }

  function GoogleIcon() {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    )
  }
  