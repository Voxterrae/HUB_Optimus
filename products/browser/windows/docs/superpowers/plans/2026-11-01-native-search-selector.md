# Native Web provider selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elegir y usar explícitamente la fuente Web desde Windows y comprobar el resultado en cloud.
**Architecture:** Configuración validada Core → launcher con revisión de configuración → diálogo y consumidor de búsqueda. Se reutiliza cancelación y quiescencia existentes; guardado transaccional antes de activar preferencias.
**Tech Stack:** .NET10, WPF/WebView2, ASP.NET Core existente; sin paquetes nuevos.
**Spec:** ../specs/2026-11-01-native-search-selector-design.md

## Ejecución y pruebas externas
Raíz implementa en línea y una revisión independiente completa al final. La prueba GUI normal conserva consultas locales. Se añade opt-in `-Gui -LiveWeb` / `--gui --live-web` para una sola consulta pública `web accessibility`, sin abrir resultados ni guardar textos. El workflow protegido no cambia. Si hace falta ejecutarlo allí sin nuevo input, un commit de QA separado solo habilita ese switch en el script de diagnóstico, conservando idénticos bytes de producción y dejando trazabilidad explícita de ambos SHAs.

## Global Constraints
Default None; migración legacy SearxEndpoint. Sin pagos/cuentas/keys/CI/gobernanza/merge. Web independiente no confirmado bloqueado, Index disponible. Ningún guardado/selector hace peticiones. Mantener TLS/HMAC/nonce/Host/Origin y cierre EOF confirmado. Mwmbl solo piloto privado con condiciones pendientes. Preservar diagnóstico padre07d.

## Review Focus
- None explícito con endpoint recordado no reactiva Web al reiniciar.
- Cambio mientras se prueba identidad no devuelve configuración obsoleta ni inicia host nuevo tras cierre fallido.
- Servicio independiente no recibe consulta Web seleccionada para otro proveedor; Index sigue disponible.
- Fallo de disco conserva política y fuente activas, no solo archivo anterior.
- GUI nativa visible no implica WebView listo; la evidencia de preparación debe preceder cualquier supuesto arreglo.

### Task1 — Preferencias y guardado
**Files:** Core/BrowserSettings.cs, new Core/WebSearchConfiguration.cs, Core/SettingsStore.cs; new Core.Tests/WebSearchSettingsTests.cs + registro.
**Interfaces:** enum WebProvider {None=0,Mwmbl=1,Searx=2}; BrowserSettings.WebProvider nullable; WebSearchConfiguration.FromSettings(settings), validated constructor(provider,endpoint); SettingsStore.Apply(current,candidate) -> SettingsResult.
- [x] Escribir casos de roundtrip JSON de Mwmbl/None, legacy endpoint y rechazo de999/Searx sin endpoint; RED con API previa sin errores de compilación.
- [x] Implementar configuración/migración y verificar Core completo GREEN.
- [x] Caso persistencia fallida devuelve active anterior; RED y añadir Apply, GREEN con archivo real.

### Task2 — Host y envío
**Files:** Core/SearchHostLauncher.cs; Search.Tests/NativeWebProviderTests.cs + registro; App/OptimusSearchView.cs consumidor.
**Interfaces:** overloads con WebSearchConfiguration para CreateStartInfo/ConfigureUpstream/ConnectAsync, wrappers legacy string; SearchHostConnection.WebError opcional, GetError(scope) conserva Index.
- [x] Casos argumentos literales Mwmbl/Searx/None, reconfiguración host propio, fallo de cierre e independiente; observar RED antes de implementación.
- [x] Añadir revisión de configuración y prueba de cambio durante readiness; ninguna consulta/reintento automático.
- [x] Implementar y ejecutar Search completo GREEN; mantener todas las negativas TLS previas.

### Task3 — Interfaz y condiciones
**Files:** App/PrivacySettingsDialog.cs, MainWindow.xaml.cs, NativeHomeView.cs, OptimusSearchView.cs, Core/SearchService.cs; docs/VALIDATION_NATIVE_SEARCH_2026_11_01.md, docs/WEB_PROVIDER_CONDITIONS_2026_11_01.md.
- [ ] Integrar selector/campo condicional, aviso de piloto y Apply antes de cambiar estado activo; conectar configuración completa.
- [ ] Actualizar explicaciones SearXNG exclusivas a fuente elegida, conservando procedencia y privacidad.
- [ ] Registrar revisión primaria de condiciones y borrador de consulta no enviado.
- [ ] Compilar WPF/helper y suites Core/Search/Privacy/backend/Python; registrar comandos/resultados y revisión independiente final.

### Task4 — Aceptación Windows
**Files:** cambios acotados de diagnóstico/regresión en App/BrowserTab.cs y MainWindow.xaml.cs, scripts/WindowsSmoke/GuiSmoke.cs y GuiNavigationDiagnostics.cs solo si la evidencia lo requiere.
- [ ] Publicar candidato trazable y ejecutar workflow existente con source_commit exacto, primero servicio y después GUI.
- [ ] Si se reproduce navegación no preparada, registrar etapas/flags sin datos de página; distinguir carrera de arranque y bloqueo real, corregir causa observada con RED→GREEN, conservar evidencia adversa.
- [ ] Comprobar selector en GUI sin emitir consultas externas al guardar; nunca afirmar prueba funcional desde una captura estática.

Entrega externa: actualizar propuesta borrador/handoff y registrar SHA exacto, evidencia nativa y límites pendientes; no autorizar merge o uso empresarial mediante pruebas técnicas.
