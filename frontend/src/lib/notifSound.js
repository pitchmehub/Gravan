/**
 * Toca um chime suave de dois tons usando Web Audio API.
 * Não depende de arquivo externo — gerado sinteticamente.
 * Respeita a política de autoplay: só toca após alguma interação do usuário.
 */

let ctx = null

function getCtx() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)()
  }
  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {})
  }
  return ctx
}

function playTone(frequency, startTime, duration, gainPeak, audioCtx) {
  const osc = audioCtx.createOscillator()
  const gain = audioCtx.createGain()

  osc.type = 'sine'
  osc.frequency.setValueAtTime(frequency, startTime)

  gain.gain.setValueAtTime(0, startTime)
  gain.gain.linearRampToValueAtTime(gainPeak, startTime + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration)

  osc.connect(gain)
  gain.connect(audioCtx.destination)

  osc.start(startTime)
  osc.stop(startTime + duration)
}

export function tocarNotificacao() {
  try {
    const audioCtx = getCtx()
    const now = audioCtx.currentTime

    // Dois tons ascendentes — chime elegante e discreto
    playTone(880, now,        0.35, 0.18, audioCtx)  // Lá5
    playTone(1320, now + 0.18, 0.40, 0.13, audioCtx) // Mi6
  } catch (_) {
    // Silencia erros (contexto bloqueado, etc.)
  }
}
