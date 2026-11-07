# HUB Relay — Viabilidad de autorización nativa v0.1

**Estado:** etapa A documental; capacidades del hardware `unverified`; B bloqueada.
**Baseline:** `main@739eaf9a2e0e0d6ceb564db6d1127e243178d0ea`; fuentes consultadas el 12/10/2026.
**Señal:** [diseño/plan de #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6130552981) y [aprobación del
plan](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6131840733) y [aclaración de
plataformas](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6132488110).
Benjamin Gerrit Hoff conserva la decisión humana final conforme al [handoff vigente](../../../../docs/context/OWNER_AUTHORITY_HANDOFF.md).

## Decisión y superficie

- Device Bridge es experimental y separado del runtime; [seguridad vigente](../../SECURITY_REQUIREMENTS.md) exige firma Android por uso.
- El [piloto Windows](../README.md), `fixture.v0.1` y `EXECUTOR_DISABLED` permanecen intactos.
- Broker Windows protegido + firmante Android es el candidato del plan; ningún componente está instalado por esta entrega.
- Compatibilidad con Windows 10 y extensión a plataformas mediante base común/adaptadores es requisito aclarado; edición/build/hardware concretos siguen sin confirmar.
- Hello y un callback biométrico no satisfacen por sí solos firma exclusiva con biometría fuerte.
- La evidencia documental permite preparar B; el dispositivo, sus claves y el aislamiento requieren evidencia privada real.
- El entregable mínimo son esta matriz y el [runbook](PRIVATE_PROBE_RUNBOOK.v0_1.md), sin código, collector ni nueva simulación.

## Matriz de proveedores y soporte

`documented` significa API/política descrita por fuente primaria; `observed` exige prueba exacta privada reproducible; `unverified` indica evidencia pendiente; `unsupported` indica
incompatibilidad del uso/configuración evaluado. Los textos de cada celda limitan el alcance del estado de la fila. No hay biometría `observed`.

| providerId | osSupport | hardwareTrust | perUseBiometric | pinFallback | requestSignature | isolationEvidence | status | evidenceRef |
|---|---|---|---|---|---|---|---|---|
| windows.user-consent-verifier | API Windows documentada; target pendiente | No acredita clave hardware | Verificación admite modalidades distintas | PIN admitido | No devuelve firma del request | No establece aislamiento del broker | documented | [MS consent](https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverifier) |
| windows.hello-keycredential | API Windows documentada; target pendiente | TPM opcional; software posible | Gesto PIN o biométrico; insuficiente para política | PIN admitido | `RequestSignAsync` documentado | No acredita aislamiento de HUB Relay | documented | [MS Hello](https://learn.microsoft.com/en-us/windows/apps/develop/security/windows-hello) |
| android.keystore-per-use-api | API 30+ candidata; soporte concreto pendiente | TEE/StrongBox posibles, sin garantía por modelo | Auth por uso + CryptoObject documentados | Puede excluirse de esta operación | `Signature` en CryptoObject | UI/app y broker aún sin probar | documented | [Builder](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder), [CryptoObject](https://developer.android.com/reference/android/hardware/biometrics/BiometricPrompt.CryptoObject) |
| android.selected-hardware | Teléfono/API/parche por seleccionar privadamente | Attestation y nivel pendientes | Sensor Class 3/inscripción/prueba pendientes | Exclusión efectiva pendiente | Firma cruzada real pendiente | Hash/app/verified boot pendientes | unverified | [Keystore](https://developer.android.com/privacy-and-security/keystore), runbook privado futuro |
| windows.dotnet10-pro22h2 | Windows 10 Pro 22H2/build 19045 excluido | No evaluado | No aplica | No aplica | No evaluada | No evaluado | unsupported | [matriz .NET 10](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md), [instalación Windows](https://learn.microsoft.com/en-us/dotnet/core/install/windows#supported-versions) |
| windows.dotnet10-supported-candidate | Windows 11 en edición/release expresamente admitida | No evaluado | Firma desde Android candidata | Sin sustitución por Hello | Verificador .NET candidato | Identidad/ACL/token pendientes | documented | mismas matrices oficiales; no demuestra disponibilidad de un target |
| windows.rust-win32-candidate | `x86_64-pc-windows-msvc`, Tier 1 con host tools, Windows 10+ | Clave/proveedor/protección unverified | Depende de Android; prueba unverified | Sin sustitución por Hello | Verificador nativo candidato; unverified | Broker/ACL/token unverified | documented | [Rust Windows MSVC](https://doc.rust-lang.org/rustc/platform-support/windows-msvc.html), [tiers](https://doc.rust-lang.org/rustc/platform-support.html); sólo soporte documental de toolchain |
| windows.selected-broker | Equipo/perfil/build por seleccionar privadamente | Fuente y protección de clave pendientes | Depende de firmante validado | Debe denegar fallback | Verificación independiente pendiente | Prueba con token real pendiente | unverified | runbook; AUTH-01..03 y AUTH-10 del diseño |

La exclusión de Pro 22H2/19045 limita al candidato .NET 10, no demuestra que HUB Relay sea imposible en Windows 10 ni identifica el equipo del usuario. La lista de Microsoft limita
Windows 10 a ediciones/releases LTSC/Enterprise concretas; no trasladar ese soporte por similitud. Evaluar un broker nativo Win32 compatible con el Windows 10 seleccionado antes de
adoptar toolchain. Rust documenta soporte Windows 10+ del target MSVC; las APIs/seguridad de HUB Relay siguen `unverified`. Windows 11 soportado es una opción, no un requisito ni
un equipo disponible confirmado. No actualizar el OS ni sustituir
toolchain silenciosamente. No crear un probe Hello para repetir su limitación ya documentada.

El objetivo multiplataforma conserva firma por uso, binding, verificación independiente y denegación uniforme. Una base común candidata de request canónico y adaptadores por
plataforma requiere pruebas de APIs, soporte y aislamiento en cada destino. Este documento no certifica todas las plataformas ni adopta nuevos contratos, lenguaje o arquitectura;
la compatibilidad debe resolverse en A antes de proyectos B.

## Política que B debe concretar

El firmante candidato usa P-256/SHA-256, `setUserAuthenticationRequired(true)`, `setUserAuthenticationParameters(0, AUTH_BIOMETRIC_STRONG)` e invalidación ante nueva inscripción
biométrica. `BiometricPrompt.CryptoObject(Signature)` y sólo `BIOMETRIC_STRONG`; sin `DEVICE_CREDENTIAL`, clave software ni ventana reutilizable. La credencial de recuperación del
OS se conserva. La API no acredita quién es civilmente el usuario ni qué hardware cumple en el teléfono elegido.
[Builder](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder), [Keystore](https://developer.android.com/privacy-and-security/keystore).

La política de attestation debe fijar TEE o StrongBox aceptables, nivel de seguridad de clave/attestation, aplicación y firma esperadas, verified boot, soporte/parches y
algoritmos. No hay fallback software. El verificador protegido se ejecutará fuera de Android: cadena completa, firmas, challenge fresco, clave pública, revocación y extensión/app
según esquema. No asumir que la extensión confiable está siempre en el certificado hoja. [Verificación
oficial](https://developer.android.com/privacy-and-security/security-key-attestation).

Auth-per-operation puede representarse sin `AUTH_TIMEOUT`; no exigir literalmente `authTimeout == 0` en attestation ni un `USER_SECURE_ID` marcado como no expuesto en attestation.
Interpretar versión/listas de autorización y enforcement según [esquema AOSP](https://source.android.com/docs/security/features/keystore/attestation) y
[KeyMint](https://source.android.com/docs/security/features/keystore/implementer-ref), y contrastarlo con firma real por uso; no aceptar sólo declaraciones de la app.

Raíces y revocación se obtendrán de fuentes oficiales autenticadas con URL, fecha, hash y política en manifiesto privado protegido. El conjunto vigente incluye rotación; no fijar
una antigua raíz única. Edad máxima de bundle local de 24 h al inscribir y admitir es **propuesta del piloto**, no garantía de revocación inmediata; la fuente determina
actualización mediante `Cache-Control`. La [CRL oficial](https://android.googleapis.com/attestation/status) devolvió `public, max-age=86400` al consultar cabeceras el 12/10/2026;
verificarlo de nuevo al obtener el bundle. Evidencia caducada/ausente deniega. [Raíces y política CRL](https://developer.android.com/privacy-and-security/security-key-attestation).

La cadena/raíces tienen bundle de inscripción privado separado, íntegro y con límites de bytes/certificados a revisar; jamás truncarlo para caber en 4 KiB. Los sobres operativos
candidatos `relay.native-request.v0.1`/`relay.native-approval.v0.1` se limitan a 4.096 bytes UTF-8 cada uno. Siguen pendientes de adopción como contrato y no reemplazan
`fixture.v0.1`.

Intercambio offline sólo por importación/exportación local explícita y selección acotada. No observa instantáneamente cambios remotos posteriores a una firma. Consumo único,
deadline monotónico de 60.000 ms y cancelación/revocación recibida por el broker son requisitos posteriores: la revocación confirmada antes del punto atómico de publicación vence;
después no recupera datos publicados. Exigir observación remota instantánea bloquearía esta ruta hasta revisar un canal autenticado adicional.

## Pins candidatos y bloqueos antes de crear proyectos

Estos valores son documentación consultada, no adopción, instalación ni aceptación de licencias. Cada selección final requiere URL de artefacto, versión exacta, arquitectura, hash,
procedencia/licencia, dependencias transitivas y revisión bajo #1933.

| Componente | Candidato documental | Pendiente que bloquea B |
|---|---|---|
| Rust nativo / target MSVC | `1.99.0`, manifest `2026-10-01` de [metadata oficial](https://static.rust-lang.org/dist/channel-rust-stable.toml); `x86_64-pc-windows-msvc` candidato | Arquitectura real, artefactos/componentes/hashes/licencias, mapa Rust y dependencias pendientes de revisión; sin adopción |
| .NET SDK / runtime | SDK `10.0.401`; latest-release/runtime `10.0.12` en [metadata oficial](https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json) | No seleccionado: compatibilidad Windows 10 requerida; si se reconsidera, paquete/arquitectura/hash/runtime efectivo pendientes; no igualar runtime del SDK con latest-release |
| Windows SDK / MSVC / packaging / clave broker | Sin pins seleccionados; alternativa nativa Win32 por revisar | Compatibilidad Windows 10 requisito; APIs, SDK/MSVC/CRT, versión/hash/licencias/transitivas, protección de clave, identidad/ACL y mapa del toolchain elegido bloquean B |
| AGP / Gradle | `9.4.0` / `9.6.0`, [tabla oficial AGP](https://developer.android.com/build/releases/agp-9-4-0-release-notes) | Revisar tuple completo, distribución/wrapper/hash, compatibilidad y licencias |
| JDK | `17` requerido por tabla AGP | Proveedor, patch, artefacto/hash y términos pendientes |
| Android SDK | min API `30`, compile/target `37` candidatos; Build Tools `36.0.0` según tabla AGP | Paquetes/revisiones/hashes, política de soporte real y términos de distribución/test pendientes |
| Kotlin / transitivas Android | Configuración integrada de AGP por revisar | Versión efectiva, artefactos/transitivas/licencias y reproducibilidad pendientes |
| RFC 8785 / ASN.1 / attestation verifier | Sin bibliotecas seleccionadas | Implementación, versión/hash/licencia, vectores y parser con límites; ningún paquete instalado |
| Bundle de confianza | Raíces/CRL oficiales vigentes; edad máxima 24 h propuesta | Trust policy, bytes/hashes/obtención auténtica y límites exactos pendientes |

## Aceptación y siguiente decisión

La revisión A comprobará campos/estados/fuentes, elección de plataforma, mapa del toolchain elegido y firmante Kotlin, pins/licencias, trust policy y runbook privado concreto.
El mapa C# histórico es candidato evaluado, no impuesto; un mapa Rust requiere revisión antes de proyectos B. Cualquier selección o
evidencia `unverified` pertinente mantiene B en **NO RUN**; la revisión documental no convierte hardware en `observed`.

Fuera de alcance: inventario/shell/contactos, red de dispositivos, nuevas conexiones, permisos legacy, servicios, instalaciones, biometría real, contratos vigentes, CI, branding y
gobernanza. El siguiente subplan es una única prueba nativa de firma/inscripción de B después de revisar selecciones y aprobar la prueba concreta. No añadir fixture, validador
artificial de recibos ni cerrar #1933 por este documento.
