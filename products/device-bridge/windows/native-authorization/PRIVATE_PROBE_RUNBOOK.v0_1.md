# HUB Relay — Plantilla de runbook privado de prueba v0.1

**Estado:** plantilla pública de etapa A; **NO RUN**. No contiene datos del dispositivo ni autoriza ejecución real.
**Fuente:** [plan aprobado en #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6131840733), tarea 1; [viabilidad](FEASIBILITY.v0_1.md).
[Requisito de plataformas](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6132488110): Windows 10 incluido; lenguaje/toolchain y mapa pendientes de revisión.
La aprobación del plan permite preparar A; no sustituye selección de destino, inscripción ni aprobación de prueba. Benjamin Gerrit Hoff es la única contraparte humana de
aprobación; siguen vigentes las reglas del [handoff](../../../../docs/context/OWNER_AUTHORITY_HANDOFF.md).

## Límite de la futura prueba B

Único probe útil: inscripción controlada y una firma biométrica nativa Android, verificada fuera del teléfono en Windows, con rechazo al cambiar un byte. Collector y admisión de
producción deshabilitados. No repetir la simulación ni crear probe Hello/validador de recibos como supuesto avance.

Operaciones permitidas propuestas: verificar artefactos aprobados, crear/proteger las dos claves de prueba, intercambiar material de inscripción y sobres por selección local
explícita, presentar y firmar request de la operación fija sin datos privados, verificar, registrar resultado privado y retirar exactamente el estado creado. Ninguna
ejecución/lectura de inventario,
shell genérica, contactos, archivos del usuario, pantalla, ADB general, acceso de red de dispositivos, relay remoto o servicio persistente. Construcción y distribución del probe
requieren subplan B revisado antes de crear proyectos.

## Manifiesto privado obligatorio antes de ejecutar

Completar fuera del repositorio en una ubicación protegida y seleccionada localmente. Identificadores y hashes de dispositivo/perfil, claves, certificados, bindings, rutas y
evidencias quedan privados, incluidos sus hashes derivados; nunca copiarlos a la issue ni al recibo público. No capturar biometría cruda, PIN, passwords o tokens.

| Sección privada | Campos exactos por completar | Estado actual |
|---|---|---|
| Selección | `windowsTargetId`, `windowsProfileId`, edición/build/arquitectura, `androidTargetId`, usuario/API/parche, método local de identificación | unverified; ningún target seleccionado aquí |
| Soporte/pins | Matriz OS fechada, pins/hashes de binarios/toolchains/transitivas/licencias; mapa del toolchain elegido y firmante Kotlin revisados | unverified; Rust/Win32 candidato; C# histórico no impuesto; no crear proyectos aún |
| Artefactos | Commit de fuente, binario Windows/APK, hashes, firma/publisher, package ID definitivo, método/ruta de carga/retirada | unverified |
| Estado previo | Alias ausentes/presentes, apps y stores previos, ACL/token, permisos y asistencia existentes; ubicaciones absolutas verificadas | unverified; sin lecturas de dispositivo en A |
| Claves nuevas | `brokerKeyAlias`, `signerKeyAlias`, proveedor/protección, generación, fingerprints completos y perfil enlazado | unverified; alias únicos exactos a fijar; no reutilizar claves existentes |
| Trust policy | TEE/StrongBox permitido, app/firma, boot/parches, esquema, raíces vigentes/CRL: URLs auténticas, fecha, bytes/hash, edad/límites | unverified; sin fallback software |
| Intercambio | Archivos seleccionables exactos, límites bundle/sobres, fingerprints por ruta independiente, evidencia y retención privada | unverified |
| Aprobación | Referencia GitHub y aprobación local de Benjamin, alcance/paso/horario, dispositivo/perfil exactos y rollback revisados | pendiente; NO RUN |

`brokerKeyAlias` y `signerKeyAlias` son nombres de campos, no aliases operativos adoptados. El manifiesto deberá fijar sus valores literales, rutas/store, ACL y todas las llamadas
ejecutables antes de la prueba. Si existen aliases o estado en esas ubicaciones, detener; no sobrescribir ni recuperar automáticamente. No borrar estado previo ni alterar
credenciales/asistencia actuales.

## Secuencia futura revisable — no ejecutada

Cada paso requiere el anterior verificado; fallo/cancelación/diferencia de hash o binding detiene sin fallback. Las llamadas de interfaz son candidatas del plan, no APIs ya
implementadas ni contratos adoptados. El manifiesto B añadirá comando/API exacto y evidencia esperada para carga, origen de clave Windows y retirada antes de autorizar.

1. **Cerrar NO RUN:** revisar independientemente matriz, OS/pins/mapas, trust policy, límites, manifiesto y rollback completos. Registrar aprobación de la prueba exacta; no
   inferirla de «listo», Site o tests sintéticos. Compatibilidad Windows 10 requiere verificar edición/build privados y evaluar toolchain adecuada: Pro 22H2/19045 queda excluido
   sólo del candidato .NET 10, no seleccionado. Rust/Win32 documenta Windows 10+; SDK/MSVC, dependencias/licencias/hashes y mapa elegido aún bloquean B. Windows 11 no es requisito
   y no hay actualización silenciosa.
2. **Comprobar antes-estado:** localmente en ambos destinos aprobados, confirmar identidad/perfil, hashes/firma de binarios y permisos mínimos. Registrar estado previo y
   aliases/store ausentes. Android: `BiometricManager.canAuthenticate(BIOMETRIC_STRONG)` y revisión local de inscripción; sin sensor fuerte/inscripción válida → stop. No inscribir
   otra biometría automáticamente ni leer inventario.
3. **Bootstrap de origen Windows:** crear la clave de origen exclusivamente mediante proveedor/llamada de protección elegidos y aprobados en el manifiesto; publicar sólo su clave
   pública en archivo local seleccionado. Mostrar fingerprint completo en UI local confiable. Compararlo con el importado en Android por una ruta independiente del cliente remoto;
   una etiqueta del transporte no identifica al broker. Fijar `brokerKeyAlias`, perfil/generación y binding privado; proteger store contra escrituras del transport. Protección/ACL
   aún sin demostrar → stop.
4. **Challenge de inscripción:** Windows genera bytes frescos con CSPRNG y los registra privadamente, separados del nonce operativo. Importarlos en Android sólo por selección local
   explícita. El challenge no es una clave, aprobación operativa ni evidencia de identidad civil.
5. **Clave Android:** `KeyPairGenerator.getInstance("EC", "AndroidKeyStore")`; `initialize(KeyGenParameterSpec.Builder(signerKeyAlias,
   PURPOSE_SIGN).setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1")).setDigests(DIGEST_SHA256).setUserAuthenticationRequired(true).setUserAuthenticationParameters(0,
   AUTH_BIOMETRIC_STRONG).setInvalidatedByBiometricEnrollment(true).setAttestationChallenge(challenge).build())`; `generateKeyPair()`. StrongBox, si lo exige la política elegida,
   se pide explícitamente; su indisponibilidad deniega, sin fallback. [API oficial](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder).
6. **Bundle y verificación:** `KeyStore.getCertificateChain(signerKeyAlias)` y exportación local explícita de cadena íntegra/evidencia de app. `ValidateEnrollment(evidence,
   expectedChallenge, trustPolicy)` en Windows verifica cadena/raíz auténtica vigente, firmas/revocación, challenge/clave/app, nivel hardware, boot y autorizaciones según versión.
   No validar exclusivamente en Android; no exigir `USER_SECURE_ID` expuesto ni `authTimeout` literalmente cero. Bundle privado separado: no truncar certificados para 4 KiB.
   [Attestation](https://developer.android.com/privacy-and-security/security-key-attestation), [esquema](https://source.android.com/docs/security/features/keystore/attestation).
7. **Confirmar binding de prueba:** comparar ambos fingerprints completos y perfil/generación en las dos UIs locales; confirmación explícita en ambos extremos y stores protegidos.
   Falta de evidencia → `ENROLLMENT_UNVERIFIED`. Inscripción de prueba no activa el broker de producción ni modifica el owner identity manifest.
8. **Preparar request sin datos:** `PrepareRequest` y `SignBrokerRequest` producen el sobre candidato firmado por origen, con destino/perfil/generaciones, nonce CSPRNG, campos
   exactos y deadline monotónico 60.000 ms. Conservar `windows.runtime_inventory.v0_1` y campos exactos/orden `['windows','powershell7','node']`; usar perfiles ficticios de prueba
   en contexto explícito separado de producción. Firmar/vincular esa petición sin invocar collector ni leer datos; el probe demuestra autorización para la operación, no su
   ejecución. No crear otro operation ID ni aceptar test flags/claves software/IDs `fixture-*` por el camino de autoridad.
   Canonicalización RFC 8785/domains/DER requieren vectores revisados. Cada sobre operativo ≤4.096 bytes UTF-8; importación explícita seleccionada.
9. **Revisar y firmar por uso:** `VerifyAndReviewBrokerRequest` rechaza origen/binding desconocido antes de presentar; UI muestra exactamente payload/identidad inscrita.
   `Signature.getInstance("SHA256withECDSA")`, `initSign(privateKey)`; `BiometricPrompt` permite sólo `BIOMETRIC_STRONG` y `authenticate(CryptoObject(signature), ...)`. Tras éxito
   usar el `Signature` del resultado para `update(exactSigningBytes)` y `sign()`. No aceptar callback/booleano solo ni `DEVICE_CREDENTIAL`. Exportar sólo aprobación seleccionada.
   [CryptoObject](https://developer.android.com/reference/android/hardware/biometrics/BiometricPrompt.CryptoObject).
10. **Verificación y negativos:** Windows verifica firma SHA-256/ECDSA DER sobre idénticos bytes y key/binding inscritos; alterar un byte debe fallar. Probar origen falso/otra
    clave/perfil/generación antes de prompt; cancelación, biometría no disponible/lockout y PIN como alternativa no producen aprobación. Segunda firma exige nueva biometría. Prueba
    destructiva de cambio de inscripción sólo si se aprueba separadamente; la clave anterior debe quedar inutilizable y una reinscripción requiere nueva ceremonia.
11. **Cerrar evidencia:** registrar resultados exactos por paso, bytes privados, versiones, estado y diferencias; ningún dato de inventario. Un PASS de firma no acredita
    aislamiento, ledger/replay duradero, revocación, soporte general o AUTH-01..10 completos. Retirar aun si falla el probe.

## Cambios previstos y retirada verificable

| Cambio sólo tras autorización B | Retirada exacta y comprobación |
|---|---|
| Artefactos aprobados en rutas/package del manifiesto | Cerrar/detener la app de prueba; retirar únicamente esos artefactos. Confirmar ausencia por ubicación/package exactos y antes-estado |
| Clave origen Windows y binding/store privado de prueba | Revocar generación de prueba en ambos extremos antes de borrar; eliminar alias por API del proveedor elegida y store creado, comprobando ACL/alias/ausencia. No tocar claves previas |
| Alias Android de prueba | `KeyStore.deleteEntry(signerKeyAlias)`; `containsAlias(signerKeyAlias) == false` y antiguo material no puede firmar. No eliminar credencial de recuperación o inscripción biométrica |
| Cadena, sobres, pending y resultados privados | Invalidar pending, rechazar aprobación anterior; eliminar sólo archivos exactos creados según política/retención aprobadas. Comprobar rutas resueltas dentro del destino autorizado antes de borrado |
| APK de prueba si hubo instalación expresamente aprobada | Retirar package exacto y comprobar ausencia de app/alias; preservar apps/ajustes/asistencia del estado previo |

No crear servicios/listeners/tareas programadas, instalar toolchain en destino ni revocar rutas legacy en este probe. Si otro recurso resulta necesario, detener y ampliar el
manifiesto mediante entrega/aprobación separada. Rollback no se considera verificado por un exit code: comparar readback contra antes-estado, confirmar no procesos/app de prueba
activos, aliases ausentes y rechazo de firma/binding antiguo. Mantener evidencia privada del resultado y cualquier residuo pendiente.

## Frescura, offline y criterio de salida

Antes de inscripción y de futura admisión, comprobar bundle auténtico/edad según política; 24 h es máximo **propuesto**, no promesa de revocación inmediata. Cache-Control oficial y
rotación de raíces se registran al obtenerlo. Caducidad o verificación incompleta → denegar, sin red automática ni trust downgrade.

Un cambio del teléfono posterior a una firma offline no llega instantáneamente a Windows. Revocación/cancelación explícita confirmada antes del punto atómico de publicación vence;
una tardía no recupera datos publicados. B no implementa publicación de inventario ni prueba esa carrera: corresponde a la admisión posterior. Si se exige observar un cambio remoto
instantáneo, detener la ruta offline y revisar un canal autenticado adicional.

Salida A: dos documentos revisables, matriz honesta y selecciones pendientes visibles. Salida futura B: firma real y byte alterado, bindings/verificación/trust policy y retirada
con evidencia privada exacta; sólo entonces actualizar los estados pertinentes a `observed` con alcance acotado. Recibo público limitado a commit/versión de artefacto, resultado
sanitizado y limitaciones, sin IDs ni hashes de dispositivo/perfil/clave/evidencia privada. Mantener #1933 abierta y collector deshabilitado.
