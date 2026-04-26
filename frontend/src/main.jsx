import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { startKeepAlive } from './lib/keepAlive'
import './styles/modal.css'

startKeepAlive()

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {})
  })
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
