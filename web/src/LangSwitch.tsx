import { setLang, t, useLang } from './i18n'

/** Selector de idioma ES | EN. Cada botón lleva su propio `lang` para que los lectores de pantalla lo pronuncien bien. */
export function LangSwitch() {
  const lang = useLang()
  return <div className="segmented lang-switch" role="group" aria-label={t('Idioma', 'Language')}>
    <button type="button" lang="es" aria-pressed={lang === 'es'} title="Español" onClick={() => setLang('es')}>ES</button>
    <button type="button" lang="en" aria-pressed={lang === 'en'} title="English" onClick={() => setLang('en')}>EN</button>
  </div>
}
