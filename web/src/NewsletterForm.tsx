import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Operator } from './data'
import { getLang, t } from './i18n'

/** Debe coincidir con `CONSENT_VERSION` de `src/newsletter.py`: cambia cada vez que cambia el texto del consentimiento. */
const CONSENT_VERSION = '2026-11-v1'
/** Usuario de Telegram: empieza con @, luego una letra y de 4 a 31 letras, números o guion bajo (5 a 32 en total). */
const USERNAME = /^@[A-Za-z][A-Za-z0-9_]{4,31}$/

type Kind = 'alertas' | 'resumen'
type Bot = { username: string; link: string } | null
type Result = { kind: Kind; bot: Bot }

const kindName = (kind: Kind) => kind === 'alertas' ? t('alertas y sugerencias', 'alerts and suggestions') : t('resumen diario', 'daily summary')

/** Texto del consentimiento informado (versión `CONSENT_VERSION`). */
const consentText = () => t(
  'Acepto que AguaAlerta use mi usuario de Telegram y la ASADA que elegí para enviarme, por Telegram, la opción que escogí. Entiendo que: (1) solo se guardan, en un archivo del equipo de AguaAlerta, mi usuario, la ASADA, mi idioma y la fecha de este consentimiento; (2) no se usan para otra cosa ni se comparten; (3) solo recibo mensajes si envío /start al bot desde esa cuenta, y puedo dejar de recibirlos cuando quiera escribiendo /stop (mi suscripción queda marcada como «Baja»); (4) los mensajes son estimaciones experimentales y no reemplazan los avisos oficiales del IMN, el AyA ni de mi ASADA.',
  'I agree that AguaAlerta may use my Telegram username and the ASADA I chose to send me, through Telegram, the option I picked. I understand that: (1) only my username, the ASADA, my language and the date of this consent are saved, in a file kept by the AguaAlerta team; (2) they are not used for anything else or shared; (3) I only receive messages if I send /start to the bot from that account, and I can stop receiving them whenever I want by sending /stop (my subscription is then marked as "Baja", i.e. unsubscribed); (4) the messages are experimental estimates and do not replace the official notices from the IMN, the AyA or my ASADA.',
)

async function send(username: string, kind: Kind, asadaId: string): Promise<Result> {
  let response: Response
  try {
    response = await fetch('/api/suscripciones', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, kind, asada_id: asadaId, consent: true, consent_version: CONSENT_VERSION, lang: getLang() }),
    })
  } catch {
    throw new Error(t('No pudimos conectarnos con el servicio de suscripciones. Revisá tu conexión e intentá de nuevo.', 'We could not reach the subscription service. Check your connection and try again.'))
  }
  const body = await response.json().catch(() => null) as { detail?: { message?: string }; bot?: Bot; kind?: Kind } | null
  if (!response.ok) {
    throw new Error(body?.detail?.message ?? (response.status === 404
      ? t('El servicio de suscripciones no está disponible en este momento.', 'The subscription service is not available right now.')
      : t('No pudimos guardar tu suscripción. Intentá de nuevo en un momento.', 'We could not save your subscription. Try again in a moment.')))
  }
  return { kind, bot: body?.bot ?? null }
}

/**
 * Newsletter por Telegram de una ASADA. Se muestra al elegir una ASADA en Predicciones: usuario con @, una (y solo una) de las
 * dos opciones y el consentimiento informado. Al guardar, el sitio indica el último paso: abrir el bot y enviarle /start.
 */
export function NewsletterForm({ operator }: { operator: Operator }) {
  const [username, setUsername] = useState('')
  const [kind, setKind] = useState<Kind | ''>('')
  const [consent, setConsent] = useState(false)
  const [touched, setTouched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState<Result>()

  const cleanName = username.trim()
  const nameOk = USERNAME.test(cleanName)
  const ready = nameOk && kind !== '' && consent
  const showNameError = touched && !nameOk

  async function submit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (!ready || busy) return  // `ready` ya garantiza que hay una opción elegida
    setBusy(true)
    setError('')
    try {
      setDone(await send(cleanName, kind, operator.id))
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure))
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return <section className="section newsletter" id="newsletter" aria-labelledby="nl-title">
      <div className="newsletter-card done" role="status">
        <span className="eyebrow">Telegram</span>
        <h2 id="nl-title">{t('¡Casi listo!', 'Almost done!')}</h2>
        <p>{t(`Guardamos tu suscripción a ${kindName(done.kind)} para ${operator.name}.`, `We saved your subscription to ${kindName(done.kind)} for ${operator.name}.`)}</p>
        <p><strong>{t('Último paso:', 'Last step:')}</strong> {t(
          `abrí el bot de Telegram y enviale /start desde la cuenta ${cleanName}. Telegram no deja que un bot escriba primero: sin ese paso no vas a recibir nada. Apenas lo envíes te llega un mensaje de bienvenida y uno de prueba.`,
          `open the Telegram bot and send it /start from the account ${cleanName}. Telegram does not let a bot write first: without this step you will not receive anything. As soon as you send it, you get a welcome message and a test message.`)}</p>
        {done.bot
          ? <a className="pill pill-primary hero-cta" href={done.bot.link} target="_blank" rel="noopener noreferrer">{t(`Abrir @${done.bot.username} en Telegram`, `Open @${done.bot.username} in Telegram`)}</a>
          : <p className="empty">{t('Todavía no hay un bot de Telegram activo. Tu suscripción queda guardada y vas a empezar a recibir mensajes cuando el equipo lo active; si ya lo hizo, buscá el bot y enviale /start.',
              'There is no active Telegram bot yet. Your subscription is saved and you will start receiving messages once the team activates it; if it already did, find the bot and send it /start.')}</p>}
        <p className="muted">{t('Para dejar de recibir mensajes, escribí /stop en el chat del bot.', 'To stop receiving messages, send /stop in the bot chat.')}</p>
        <button type="button" className="pill pill-ghost" onClick={() => { setDone(undefined); setConsent(false); setKind('') }}>{t('Suscribir otra cuenta u opción', 'Subscribe another account or option')}</button>
      </div>
    </section>
  }

  return <section className="section newsletter" id="newsletter" aria-labelledby="nl-title">
    <form className="newsletter-card" onSubmit={submit} noValidate>
      <span className="eyebrow">{t('Newsletter por Telegram', 'Telegram newsletter')}</span>
      <h2 id="nl-title">{t(`Recibí lo que se espera para ${operator.name}`, `Get what is expected for ${operator.name}`)}</h2>
      <p className="lead">{t('Elegí una opción y dejá tu usuario de Telegram. Es gratis y podés darte de baja cuando quieras.', 'Pick one option and leave your Telegram username. It is free and you can unsubscribe whenever you want.')}</p>

      <label className="field">
        <span>{t('Tu usuario de Telegram', 'Your Telegram username')}</span>
        <input type="text" name="username" value={username} placeholder="@usuario" autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={40}
          aria-invalid={showNameError} aria-describedby="nl-username-help"
          onChange={event => setUsername(event.target.value)} onBlur={() => setTouched(true)} />
        <small id="nl-username-help" className={showNameError ? 'error' : 'muted'}>
          {t('Tiene que empezar con @ (5 a 32 letras, números o guion bajo). Ejemplo: @mi_usuario', 'It must start with @ (5 to 32 letters, numbers or underscores). Example: @my_username')}
        </small>
      </label>

      <fieldset className="options">
        <legend>{t('¿Qué querés recibir? (elegí una)', 'What do you want to receive? (choose one)')}</legend>
        <label className={kind === 'alertas' ? 'option on' : 'option'}>
          <input type="radio" name="kind" value="alertas" checked={kind === 'alertas'} onChange={() => setKind('alertas')} />
          <span><strong>{t('Alertas y sugerencias', 'Alerts and suggestions')}</strong>
            <small>{t('Solo cuando los datos advierten un riesgo de calor, lluvia o El Niño en tu zona, con qué podés hacer.', 'Only when the data warn of a heat, rain or El Niño risk in your area, with what you can do.')}</small></span>
        </label>
        <label className={kind === 'resumen' ? 'option on' : 'option'}>
          <input type="radio" name="kind" value="resumen" checked={kind === 'resumen'} onChange={() => setKind('resumen')} />
          <span><strong>{t('Resumen diario', 'Daily summary')}</strong>
            <small>{t('Cada día, un resumen de los datos de tu zona con sugerencias. Si no hay riesgos, te avisamos que no hubo cambios significativos.', 'Every day, a summary of the data for your area with suggestions. If there are no risks, we tell you there were no significant changes.')}</small></span>
        </label>
      </fieldset>

      <label className="consent">
        <input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />
        <span>{consentText()}</span>
      </label>

      <div className="newsletter-actions">
        <button type="submit" className="pill pill-primary hero-cta" disabled={!ready || busy}>{busy ? t('Guardando…', 'Saving…') : t('Suscribirme', 'Subscribe')}</button>
        {!ready && <small className="muted">{t('Falta: ', 'Missing: ')}{[!nameOk && t('usuario con @', 'username with @'), kind === '' && t('elegir una opción', 'choose an option'), !consent && t('aceptar el consentimiento', 'accept the consent')].filter(Boolean).join(', ')}</small>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  </section>
}
