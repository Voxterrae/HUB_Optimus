import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import './OptimusExperience.css';
type Page = 'home' | 'saved' | 'guide' | 'settings';
type Panel = 'privacy' | 'add' | null;
type LinkItem = {
  title: string;
  url: string;
  note: string;
  glyph: string;
  color: string;
};
const resources: LinkItem[] = [{
  title: 'Wikipedia',
  url: 'https://es.wikipedia.org/',
  note: 'Una idea, mil descubrimientos.',
  glyph: 'W',
  color: 'sand'
}, {
  title: 'Correo',
  url: 'https://outlook.live.com/',
  note: 'Abre Outlook en una pestaña.',
  glyph: '@',
  color: 'blue'
}, {
  title: 'YouTube',
  url: 'https://www.youtube.com/',
  note: 'Aprende algo. O desconecta.',
  glyph: 'play',
  color: 'rose'
}];
const examples: LinkItem[] = [{
  title: 'Wikipedia en español',
  url: 'https://es.wikipedia.org/',
  note: 'Una enciclopedia para empezar a explorar y contrastar información.',
  glyph: 'W',
  color: 'sand'
}, {
  title: 'Internet paso a paso',
  url: 'https://www.incibe.es/ciudadania',
  note: 'Recursos de INCIBE para aprender a moverte por internet.',
  glyph: 'shield',
  color: 'mint'
}, {
  title: 'Aprender con vídeos',
  url: 'https://www.youtube.com/',
  note: 'Busca tutoriales y explicaciones en YouTube.',
  glyph: 'play',
  color: 'rose'
}];
const guide = [{
  q: '¿Cómo busco algo?',
  a: 'Escribe lo que necesitas en la barra y toca la flecha. En esta vista verás resultados de ejemplo. La búsqueda real se configura en la aplicación Windows.'
}, {
  q: '¿Qué significa privado?',
  a: 'En Optimus para Windows, las pestañas privadas usan un perfil separado y no se restauran al cerrar. Eso no te hace anónimo. Aquí puedes explorar el diseño de esa función; esta vista no cambia la privacidad de tu navegador.'
}, {
  q: 'Quiero verlo más grande',
  a: 'Abre Ajustes y elige Texto grande. También puedes activar Alto contraste y ocultar las sugerencias. Tú decides cómo se ve tu espacio.'
}];
function Icon({
  name,
  size = 20
}: {
  name: string;
  size?: number;
}) {
  const paths: Record<string, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>,
    arrow: <><path d="M4 12h15M13 5l7 7-7 7" /></>,
    external: <><path d="M14 3h7v7m0-7L10 14" /><path d="M10 4H4v16h16v-6" /></>,
    bookmark: <path d="M6 3h12v18l-6-4-6 4Z" />,
    guide: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" /></>,
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" /><path d="m9 12 2 2 4-4" /></>,
    settings: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="2" fill="currentColor" /><circle cx="16" cy="12" r="2" fill="currentColor" /><circle cx="8" cy="18" r="2" fill="currentColor" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    check: <path d="m5 12 4 4L19 6" />,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1" /></>,
    moon: <path d="M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z" />,
    play: <path d="m9 5 11 7-11 7Z" />,
    back: <path d="m14 5-7 7 7 7" />,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>,
    eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
    dots: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.guide}</svg>;
}
function Mark({
  small = false
}: {
  small?: boolean;
}) {
  return <img src="https://storage.googleapis.com/storage.magicpath.ai/component-assets/466697341487947776/466697341487947777/3758496c27511fb0e7162e89369824a449eb61ec7877f41ab65d877e9b0d4089.svg" alt="" className={small ? 'op-mark small' : 'op-mark'} />;
}
function Switch({
  checked,
  onChange,
  label
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={onChange} className={'op-switch ' + (checked ? 'on' : '')}><span /></button>;
}
function Modal({
  title,
  children,
  onClose
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    const previous = document.activeElement as HTMLElement | null;
    el?.showModal();
    return () => {
      el?.close();
      previous?.focus();
    };
  }, []);
  return <dialog ref={ref} className="op-dialog" onCancel={onClose} onClick={e => {
    if (e.target === e.currentTarget) onClose();
  }} aria-label={title}>
    <div className="op-dialog-head"><h2>{title}</h2><button className="op-icon-button" onClick={onClose} aria-label="Cerrar"><Icon name="close" /></button></div>
    {children}
  </dialog>;
}
export const OptimusExperience = () => {
  const [page, setPage] = useState<Page>('home');
  const [panel, setPanel] = useState<Panel>(null);
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState('');
  const [simple, setSimple] = useState(false);
  const [large, setLarge] = useState(false);
  const [contrast, setContrast] = useState(false);
  const [quiet, setQuiet] = useState(false);
  const [light, setLight] = useState(false);
  const [privatePreview, setPrivatePreview] = useState(false);
  const [saved, setSaved] = useState<LinkItem[]>([]);
  const [answer, setAnswer] = useState<number | null>(null);
  const [linkName, setLinkName] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLHeadingElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(''), 3200);
    return () => window.clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(target.tagName) && !target.isContentEditable && !panel) {
        e.preventDefault();
        setPage('home');
        window.setTimeout(() => searchRef.current?.focus(), 30);
      }
    };
    window.addEventListener('keydown', fn);
    return () => window.removeEventListener('keydown', fn);
  }, [panel]);
  const go = (next: Page) => {
    setPage(next);
    setSubmitted('');
    setAnswer(null);
    window.requestAnimationFrame(() => {
      window.scrollTo({
        top: 0,
        behavior: 'instant'
      });
      mainRef.current?.focus({
        preventScroll: true
      });
    });
  };
  const doSearch = (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      searchRef.current?.focus();
      return;
    }
    setSubmitted(query.trim().slice(0, 500));
    setPage('home');
    window.setTimeout(() => resultRef.current?.focus(), 40);
  };
  const toggleSave = (item: LinkItem) => {
    const exists = saved.some(x => x.url === item.url);
    setSaved(exists ? saved.filter(x => x.url !== item.url) : [...saved, item]);
    setNotice(exists ? 'Quitado de Guardados' : 'Añadido a Guardados de esta demo');
  };
  const addLink = (e: FormEvent) => {
    e.preventDefault();
    let url: URL;
    try {
      url = new URL(linkUrl.includes('://') ? linkUrl : 'https://' + linkUrl);
      if (!['https:', 'http:'].includes(url.protocol) || !url.hostname.includes('.') || url.username || url.password) throw Error();
    } catch {
      setError('Escribe una web válida, como ejemplo.com.');
      return;
    }
    if (saved.some(x => x.url === url.href)) {
      setError('Ese enlace ya está guardado.');
      return;
    }
    setSaved([...saved, {
      title: linkName.trim() || url.hostname,
      url: url.href,
      note: url.hostname,
      glyph: 'external',
      color: 'mint'
    }]);
    setPanel(null);
    setLinkName('');
    setLinkUrl('');
    setError('');
    setNotice('Enlace añadido a esta demo');
  };
  const nav = [{
    id: 'home' as Page,
    icon: 'home',
    label: 'Inicio'
  }, {
    id: 'saved' as Page,
    icon: 'bookmark',
    label: 'Guardados'
  }, {
    id: 'guide' as Page,
    icon: 'guide',
    label: 'Guía'
  }, {
    id: 'settings' as Page,
    icon: 'settings',
    label: 'Ajustes'
  }];
  return <div lang="es" className={'op-app' + (large ? ' op-large' : '') + (contrast ? ' op-contrast' : '') + (light ? ' op-light' : '') + (quiet ? ' op-quiet' : '') + (privatePreview ? ' op-private' : '')}>
    <a href="#optimus-main" className="op-skip">Ir al contenido</a>
    <aside className="op-sidebar" aria-label="Navegación principal">
      <button className="op-wordmark" onClick={() => go('home')} aria-label="Optimus, ir al inicio"><Mark /><span>optimus<span className="op-wordmark-dot">.</span><small>BY HUB_OPTIMUS</small></span></button>
      <div className="op-nav-caption">TU ESPACIO</div>
      <nav>{nav.map(n => <button key={n.id} onClick={() => go(n.id)} className={'op-nav-item ' + (page === n.id ? 'active' : '')} aria-current={page === n.id ? 'page' : undefined}><Icon name={n.icon} /><span>{n.label}</span>{n.id === 'saved' && saved.length > 0 && <span className="op-count">{saved.length}</span>}</button>)}</nav>
      <div className="op-sidebar-note"><div className="op-mini-orbit"><Icon name="guide" size={24} /></div><p>La tecnología se adapta.<br /><strong>El ritmo lo pones tú.</strong></p><button onClick={() => go('settings')}>Hazlo tuyo <Icon name="arrow" size={16} /></button></div>
      <div className="op-sidebar-footer"><img src="https://storage.googleapis.com/storage.magicpath.ai/component-assets/466697341487947776/466697341487947777/5db211be97c00543df44840f7193607698e23b0850ef5b4d42fdce6ef9f84488.svg" alt="HUB Optimus" /><span>Diseñado para humanos<small>Concepto de interfaz</small></span></div>
    </aside>

    <div className="op-workspace">
      <header className="op-topbar">
        <button className="op-mobile-brand" onClick={() => go('home')} aria-label="Optimus, inicio"><Mark small /><span>optimus<span>.</span></span></button>
        <div className="op-breadcrumb"><span>Tu espacio</span><span>/</span><strong>{nav.find(n => n.id === page)?.label}</strong></div>
        <div className="op-top-actions"><span className="op-demo-tag"><span /> Vista previa interactiva</span><button className={'op-privacy-button ' + (privatePreview ? 'selected' : '')} onClick={() => setPanel('privacy')}><Icon name="shield" size={17} /><span>{privatePreview ? 'Vista privada · demo' : 'Privacidad'}</span></button><button className="op-icon-button op-theme" onClick={() => setLight(!light)} aria-label={light ? 'Activar tema oscuro' : 'Activar tema claro'} title={light ? 'Tema oscuro' : 'Tema claro'}><Icon name={light ? 'moon' : 'sun'} /></button></div>
      </header>
      <div className="op-mobile-demo"><span /> Vista previa interactiva · sin búsqueda en vivo</div>

      <main ref={mainRef} id="optimus-main" className="op-main" tabIndex={-1} aria-label={'Página ' + nav.find(n => n.id === page)?.label}>
        {page === 'home' && <>
          {privatePreview && <div className="op-private-banner"><Icon name="eye" /><span><strong>Estás probando el aspecto privado.</strong> Esta demo no activa incógnito.</span><button onClick={() => setPrivatePreview(false)}>Salir de la vista</button></div>}
          <div className="op-home-layout">
            <div className="op-primary">
              <section className="op-hero" aria-labelledby="hero-title">
                <div className="op-eyebrow"><span className="op-line" /> INTERNET, A TU MANERA</div>
                <h1 id="hero-title"><span className="op-title-first">Menos ruido.</span><br /><span className="op-hero-accent">Más tú.</span><span className="op-hero-star" aria-hidden="true">✳</span></h1>
                <p className="op-hero-description">Busca, descubre y entiende.<br className="op-mobile-break" /> A tu ritmo, con Optimus.</p>
                <form onSubmit={doSearch} className="op-search-form" role="search">
                  <label className="op-sr" htmlFor="op-search">¿Qué quieres encontrar?</label>
                  <div className="op-search-bar"><Icon name="search" size={23} /><input id="op-search" ref={searchRef} value={query} onChange={e => setQuery(e.target.value)} placeholder="¿Qué quieres encontrar?" maxLength={500} autoComplete="off" enterKeyHint="search" aria-describedby="op-search-note" /><button type="submit" aria-label="Ver resultados de ejemplo"><Icon name="arrow" size={24} /></button></div>
                  <div className="op-search-meta"><span><b>OPTIMUS SEARCH</b><span id="op-search-note">Resultados de ejemplo · sin conexión</span></span><kbd>/</kbd></div>
                </form>
                {!simple && !submitted && <div className="op-prompt-row"><span>Prueba con</span>{['Aprender algo nuevo', 'Usar internet con calma'].map(s => <button key={s} onClick={() => {
                    setQuery(s);
                    searchRef.current?.focus();
                  }}>{s}<Icon name="arrow" size={13} /></button>)}</div>}
              </section>

              {submitted ? <section className="op-results" aria-labelledby="op-results-title"><div className="op-section-heading"><h2 id="op-results-title" tabIndex={-1} ref={resultRef}>Así se verían tus resultados</h2><button className="op-text-button" onClick={() => {
                    setSubmitted('');
                    setQuery('');
                    searchRef.current?.focus();
                  }}>Limpiar</button></div><p className="op-demo-explanation">Ejemplos de interfaz para «{submitted}». Estos enlaces son fijos; no hemos consultado internet.</p><div className="op-result-list">{examples.map((r, i) => <article key={r.url} className="op-result"><div className="op-result-source"><span className={'op-resource-glyph ' + r.color}>{r.glyph.length === 1 ? r.glyph : <Icon name={r.glyph} size={17} />}</span><span>{new URL(r.url).hostname}<small>RECURSO DE EJEMPLO · 0{i + 1}</small></span><button className={'op-icon-button ' + (saved.some(x => x.url === r.url) ? 'is-saved' : '')} onClick={() => toggleSave(r)} aria-label={(saved.some(x => x.url === r.url) ? 'Quitar de guardados: ' : 'Guardar: ') + r.title} aria-pressed={saved.some(x => x.url === r.url)}><Icon name="bookmark" size={18} /></button></div><a href={r.url} target="_blank" rel="noopener noreferrer" className="op-result-title">{r.title}<Icon name="external" size={16} /><span className="op-sr">, abre web externa</span></a><p>{r.note}</p></article>)}</div></section> : <section className="op-quick" aria-labelledby="op-quick-heading"><div className="op-section-heading"><h2 id="op-quick-heading">Un buen punto de partida</h2><span>ACCESOS DE EJEMPLO</span></div><div className="op-quick-grid">{resources.map(r => <a href={r.url} target="_blank" rel="noopener noreferrer" key={r.title} className="op-quick-card"><div><span className={'op-resource-glyph ' + r.color}>{r.glyph.length === 1 ? r.glyph : <Icon name={r.glyph} size={21} />}</span><Icon name="external" size={15} /></div><strong>{r.title}</strong><small>{r.note}</small><span className="op-sr">Abre una web externa en otra pestaña</span></a>)}</div><button className="op-add-access" onClick={() => {
                  setPanel('add');
                  setError('');
                }}><Icon name="plus" size={16} /> Añadir mi propio enlace</button></section>}

              {!simple && <section className="op-adapt-card"><div className="op-adapt-icon"><Icon name="settings" size={23} /></div><div><span className="op-eyebrow">NO TIENES QUE SABERLO TODO</span><h2>Que se sienta como tuyo.</h2><p>Texto más grande, menos elementos o más contraste.<br className="op-desktop-break" /> Una interfaz que eliges tú.</p></div><button onClick={() => go('settings')} aria-label="Adaptar la interfaz"><Icon name="arrow" /></button></section>}
            </div>

            {!simple && <aside className="op-companion" aria-label="Guía de Optimus"><div className="op-companion-top"><div className="op-companion-emblem"><Icon name="guide" size={29} /></div><span>GUÍA LOCAL<small>DEMO</small></span><span className="op-orbit-dot" /></div><h2>Un poco de ayuda.<br /><em>Cuando la necesites.</em></h2><p>Sin palabras complicadas.<br />Sin prisa por entenderlo todo.</p><button className="op-companion-primary" onClick={() => go('guide')}>Vamos paso a paso <Icon name="arrow" size={19} /></button><div className="op-help-prompts">{guide.slice(0, 2).map((g, i) => <button key={g.q} onClick={() => {
                  go('guide');
                  setAnswer(i);
                }}><span>{g.q}</span><Icon name="plus" size={16} /></button>)}</div><div className="op-companion-bottom"><span className="op-small-spark">✳</span><span>La mejor interfaz<br /><strong>es la que entiendes.</strong></span></div></aside>}
          </div>
        </>}

        {page === 'saved' && <section className="op-page-section"><span className="op-eyebrow">LO IMPORTANTE, CERCA</span><h1>Tus guardados<span>.</span></h1><p className="op-page-intro">Los enlaces que elijas, en un mismo lugar. En esta demo se borran al recargar.</p><div className="op-section-heading"><h2>{saved.length} {saved.length === 1 ? 'enlace' : 'enlaces'}</h2><button className="op-filled-button" onClick={() => {
              setPanel('add');
              setError('');
            }}><Icon name="plus" size={17} /> Añadir enlace</button></div>{saved.length ? <div className="op-saved-list">{saved.map(r => <article key={r.url}><span className={'op-resource-glyph ' + r.color}>{r.glyph.length === 1 ? r.glyph : <Icon name={r.glyph} />}</span><a href={r.url} target="_blank" rel="noopener noreferrer"><strong>{r.title}</strong><span>{new URL(r.url).hostname} · web externa <Icon name="external" size={13} /></span></a><button className="op-icon-button" onClick={() => toggleSave(r)} aria-label={'Quitar ' + r.title}><Icon name="close" /></button></article>)}</div> : <div className="op-empty"><Icon name="bookmark" size={37} /><h2>Un lugar para tus favoritos.</h2><p>Añade una web o guarda un resultado de ejemplo.<br />Aquí aparecerán tus enlaces.</p></div>}</section>}

        {page === 'guide' && <section className="op-page-section op-guide-page"><span className="op-eyebrow">GUÍA LOCAL · DEMO</span><h1>Vamos a tu ritmo<span>.</span></h1><p className="op-page-intro">Elige lo que necesitas. Una explicación sencilla, paso a paso.</p><div className="op-guide-layout"><div className="op-guide-questions">{guide.map((g, i) => <button key={g.q} onClick={() => setAnswer(answer === i ? null : i)} aria-expanded={answer === i} className={answer === i ? 'chosen' : ''}><span className="op-guide-number">0{i + 1}</span><span>{g.q}</span><Icon name={answer === i ? 'close' : 'arrow'} size={19} /></button>)}</div><div className="op-guide-answer" aria-live="polite"><Icon name="guide" size={33} /><h2>{answer === null ? 'Tú marcas el siguiente paso.' : guide[answer].q}</h2><p>{answer === null ? 'No hace falta saber de tecnología para empezar. Toca una pregunta y lo vemos juntos.' : guide[answer].a}</p>{answer === 2 && <button className="op-filled-button" onClick={() => go('settings')}>Abrir Ajustes <Icon name="arrow" size={18} /></button>}<small>Respuestas preparadas. No es una conversación con IA ni está conectado al asistente remoto.</small></div></div></section>}

        {page === 'settings' && <section className="op-page-section op-settings-page"><span className="op-eyebrow">TU COMODIDAD, PRIMERO</span><h1>Hazlo tuyo<span>.</span></h1><p className="op-page-intro">Tú decides cómo se ve. Los cambios son inmediatos y duran hasta recargar esta demo.</p><div className="op-setting-list">{[{
              title: 'Vista sencilla',
              text: 'Una búsqueda y tus accesos. Oculta sugerencias y tarjetas de ayuda.',
              value: simple,
              change: () => setSimple(!simple),
              icon: 'eye'
            }, {
              title: 'Texto grande',
              text: 'Más espacio para leer y controles con texto más grande.',
              value: large,
              change: () => setLarge(!large),
              icon: 'search'
            }, {
              title: 'Alto contraste',
              text: 'Bordes más claros y colores de texto más definidos.',
              value: contrast,
              change: () => setContrast(!contrast),
              icon: 'sun'
            }, {
              title: 'Reducir movimiento',
              text: 'Desactiva transiciones y efectos de movimiento.',
              value: quiet,
              change: () => setQuiet(!quiet),
              icon: 'guide'
            }, {
              title: 'Tema claro',
              text: 'Un fondo luminoso si te resulta más cómodo.',
              value: light,
              change: () => setLight(!light),
              icon: 'sun'
            }].map(s => <div className="op-setting" key={s.title}><span className="op-setting-icon"><Icon name={s.icon} /></span><div><h2>{s.title}</h2><p>{s.text}</p></div><Switch checked={s.value} onChange={s.change} label={s.title} /></div>)}</div><div className="op-settings-bottom"><button className="op-text-button" onClick={() => {
              setSimple(false);
              setLarge(false);
              setContrast(false);
              setQuiet(false);
              setLight(false);
              setNotice('Diseño inicial restaurado');
            }}>Restablecer diseño</button><button className="op-filled-button" onClick={() => go('home')}>Ver mi inicio <Icon name="arrow" size={18} /></button></div><p className="op-setting-note"><Icon name="info" size={17} /> La adaptación es tuya: esta vista no analiza tu comportamiento ni cambia tus opciones sin que lo elijas.</p></section>}

        <footer className="op-footer"><span>HUMAN FIRST. ALWAYS.</span><span>Optimus · Concepto de interfaz<small>Los enlaces externos se abren en otra pestaña.</small></span></footer>
      </main>
    </div>

    <nav className="op-bottom-nav" aria-label="Navegación móvil">{nav.map(n => <button key={n.id} onClick={() => go(n.id)} className={page === n.id ? 'active' : ''} aria-current={page === n.id ? 'page' : undefined}><Icon name={n.icon} size={21} /><span>{n.label}</span>{n.id === 'saved' && saved.length > 0 && <i>{saved.length}</i>}</button>)}</nav>
    {notice && <div className="op-toast" role="status"><Icon name="check" size={18} />{notice}</div>}
    {panel === 'privacy' && <Modal title="Privacidad, sin letra pequeña." onClose={() => setPanel(null)}><span className="op-demo-pill">DEMOSTRACIÓN VISUAL</span><p className="op-dialog-copy">Puedes probar el aspecto de una pestaña privada. Esto no abre incógnito ni cambia las cookies, el historial o la protección de tu navegador actual.</p><div className="op-private-setting"><div><strong>Ver aspecto privado</strong><span>Solo cambia esta interfaz.</span></div><Switch checked={privatePreview} onChange={() => setPrivatePreview(!privatePreview)} label="Ver aspecto privado de demostración" /></div><div className="op-privacy-detail"><Icon name="info" /><p>En la aplicación Windows, las reglas pueden abrir dominios elegidos en privado o bloquearlos. El modo privado no te hace anónimo.</p></div><button className="op-filled-button op-wide" onClick={() => setPanel(null)}>Entendido <Icon name="check" size={18} /></button></Modal>}
    {panel === 'add' && <Modal title="Un enlace que te importa." onClose={() => setPanel(null)}><p className="op-dialog-copy">Quedará en Guardados durante esta demo.</p><form onSubmit={addLink} className="op-add-form"><label htmlFor="op-link-title">Nombre <span>(opcional)</span></label><input id="op-link-title" value={linkName} onChange={e => setLinkName(e.target.value)} maxLength={80} placeholder="Por ejemplo, Mi biblioteca" /><label htmlFor="op-link-url">Dirección de la web</label><input id="op-link-url" value={linkUrl} onChange={e => {
          setLinkUrl(e.target.value);
          setError('');
        }} maxLength={2000} placeholder="ejemplo.com" autoCapitalize="none" inputMode="url" required aria-invalid={!!error} aria-describedby={error ? 'op-url-error' : undefined} />{error && <p id="op-url-error" className="op-error" role="alert">{error}</p>}<button className="op-filled-button op-wide" type="submit">Guardar enlace <Icon name="plus" size={18} /></button></form></Modal>}
  </div>;
};
export const OptimusTuInternetMSHumano = OptimusExperience;