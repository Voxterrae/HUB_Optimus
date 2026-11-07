# Optimus accessible web pilot

## Intent and authorization

Continue the approved Optimus direction with a useful mobile-accessible companion web app. The user delegated implementation choices on 30 October 2026 after choosing Microsoft as target infrastructure and a small controlled-cost pilot. Existing Windows 0.2, source-import PR2018, original MagicPath demo and private assistant stay intact. This increment is a browser home/search companion, not a replacement native browser or an IoT controller.

## Decisions

Use dependency-free HTML/CSS/ES modules, preserving the graphite/copper/mint visual identity and existing exact SVG marks. This is a new host in an isolated module; the original React snapshot remains preserved. A private Sites preview is for acceptance, with equivalent static files ready for Pages and Azure Static Web Apps. No Azure accounts, paid resources, credits, identity roles, backend, device connections or public-site merge are activated.

Alternative approaches considered: a React build needs a new toolchain for a small static pilot; an immediate Azure backend adds billing/account decisions before they are needed. A buildless static companion gives a runnable, portable increment with no runtime dependencies.

## Experience

Default comfortable 18px text, semantic landmarks, keyboard-visible focus, touch targets at least 44px for principal controls, 320px reflow and user-selected simple/balanced/advanced density. Text sizes 18/22/26px, high contrast, light/dark theme and reduced motion are reversible. No age/disability inference or mandatory account. Six UI languages: es, ca, en, de, fr, ru; all user-facing copy including voice/privacy/errors uses the locale dictionary. Language metadata and speech language are separate.

Main routes: home, saved, guide, settings. Navigation should move focus to the main heading and scroll to top without losing control labels. Mobile bottom navigation remains reachable without covering content. Guide explains real current capabilities. Device/IoT help is informational and says no devices are connected. No fake security guarantee, private-tab claim or assistant connection.

## Search and local data

Search submits only after a button or Enter. Inform before submission that the query is sent to Wikipedia. Six fixed language Wikipedia API hosts; no arbitrary endpoint. Query maximum500 UTF16 units, at most10 results, response1MiB maximum, timeout10s. Requests omit credentials, forbid redirects, use no-referrer and no-store. Stream response with bounded bytes. Cancel and invalidate stale work on new search, edited query, language or page changes. Result titles/snippets are inert text; positive integer pageid constructs destination URLs. No query history, automatic suggestion requests, tracking, cookies or backend. Empty/error/cancel states preserve input and support retry.

Explicit opt-in remembers only sanitized visual/language preferences and saved HTTP(S) links on this device. Default is session-only. No query, results, dictated transcript, voice audio or API URL in persistent storage. Reject credentials, control characters, backslashes, executable schemes and overlong links; no HTML insertion from data. Storage failure falls back to memory and is communicated. Clear-device-data removes only this app's own key. No service worker in this increment, so no offline guarantee or cached authenticated page.

## Voice contract

Local installed speech voices only (localService=true). Read the localized help/current safe app text only; no background reading, arbitrary web content or provider calls. Explicit start/stop, rate control and language selection. If no local matching voice exists, show a useful unavailable state.

Dictation is push-to-talk, local-only and capability-gated: require Recognition support, processLocally capability and Recognition.available({langs:[lang],processLocally:true})==='available'. No remote fallback, automatic model install, permanent listening or automatic command execution. Stop after30s, page/language change, close, error or user cancellation. Transcript goes to the editable search input, never automatically submits and is discarded if the input changed meanwhile. Cancellation must invalidate pending availability and late callbacks. Report permission errors distinctly. UI must remain useful without voice. Tests cover lifecycle via injected browser-boundary doubles; actual hardware voice availability remains a device acceptance item.

## Module interfaces

- dist/i18n.mjs exports LANGUAGES (code,name,locale,wikiHost), normalizeLanguage(value), t(language,key,params={}), dictionaries and validateDictionaries(). Unknown language falls back to es; missing key falls back to Spanish or key safely. Interpolation is plain text.
- dist/voice.mjs exports VoiceController. constructor accepts {synthesis,Recognition,createUtterance,setTimer,clearTimer}. getLocalVoices(lang); async availability(lang) returning available/unsupported/unavailable/download-required; speak(text,{lang,rate,onState}); async dictate({lang,onText,onState}) returning {started,reason}; stop(); dispose(). onState values idle/speaking/listening/permission-denied/error. Browser defaults resolved safely if APIs absent. No state callback after dispose.
- dist/core.mjs exports createSearchController({fetchImpl,timeoutMs,maxBytes,setTimer,clearTimer}), safeExternalUrl(input), readDeviceState(storage), writeDeviceState(storage,state), clearDeviceState(storage). Search controller exposes async search(query,language) -> [{title,snippet,url,source}], cancel(). Search defaults10s/1MiB/10results. Storage key optimus.browser.pilot.v1, schemaVersion1. State {remember,language,speechLanguage,mode,fontSize,theme,contrast,reducedMotion,saved:[{title,url}]}; saved maximum50, title120, URL2048.
- dist/app.mjs imports the three modules, renders semantic DOM and owns UI lifetime. Use textContent for remote/user content. No third-party scripts or fonts. Local SVG icons are reused.

## Organization and deployment boundaries

Public technical documentation uses roles, not private family/shareholding details. A separate owner-private operating note records user-supplied LCDH context as provisional facts, not legal ownership findings. Technical lead, finance/operator and collaborator task roles do not grant permissions until explicitly configured. No automatic licensing/IP assignments, company registration or tax changes.

## Verification

Meaningful Node built-in tests for search bounds, malformed/redirect response, cancellation including noncooperative transport, URL validation, opt-in persistence and failure. Voice tests cover unsupported/no-local-voice, denial, late events, cancelled pending availability, language/rate bounds and disposal. I18n tests cover fallback/interpolation and actual dictionary completeness without asserting exact marketing copy. UI manually checked in supported browser at mobile and desktop widths, keyboard focus, routes, six languages, settings, search, saved links and feature-unavailable voice state. No certification or untested native/hardware claims.
