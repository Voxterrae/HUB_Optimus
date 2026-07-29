(() => {
  "use strict";

  document.body.classList.remove("no-js");
  document.body.classList.add("js");

  const translations = {
    en: {
      title: "HUB_Optimus — Versioned public portfolio",
      description: "The evidence-backed public portfolio of HUB_Optimus: Core, deterministic simulator, Semantic Engine contracts and CLI, Operator, research, governance, and Labs.",
      skip: "Skip to portfolio",
      homeAria: "HUB_Optimus home",
      brandDescriptor: "Versioned public portfolio",
      navAria: "Primary navigation",
      navMethod: "Method",
      navPortfolio: "Portfolio",
      navLabs: "Labs",
      navBoundaries: "Boundaries",
      languageAria: "Language",
      openGithub: "Open GitHub",
      heroEyebrow: "Public, versioned, evidence-backed",
      sequence: "Reality → Evidence → Inference → Narrative → Operational Signal",
      heroLead: "An integrity-first diplomatic simulation workflow for structured evaluation, preventive mediation, and systemic learning.",
      heroBoundary: "It supports better judgment. It is not an authority, a prediction engine, or a replacement for diplomacy.",
      explorePortfolio: "Explore the portfolio",
      openOperator: "Open Operator",
      truthSource: "Source of truth",
      truthCore: "Canonical v1 language",
      truthCoreValue: "Spanish",
      truthPublic: "Public layer",
      truthPublicValue: "Static Pages",
      truthRuntime: "Analysis runtime",
      truthRuntimeValue: "Local / controlled",
      globeLabel: "Geographic orientation",
      globeNotice: "Illustrative coordinates · no live telemetry",
      pauseGlobe: "Pause",
      resumeGlobe: "Resume",
      globeFallbackAlt: "HUB_Optimus approved geographic brand artwork",
      globeAria: "Interactive globe projected from real coastline coordinates. Routes are illustrative and are not live telemetry.",
      globeControls: "Drag, swipe, or use the arrow keys to rotate.",
      globeData: "Geographic data",
      principleAria: "Operating principle",
      principle: "Observe → detect → decide → act.",
      noBuild: "No build without signal.",
      accountability: "Human accountability remains mandatory.",
      methodKicker: "The method",
      methodTitle: "Separate before interpreting.",
      methodLead: "The five stages are an operating discipline. Each stage limits what the next stage is allowed to claim.",
      methodReality: "Reality",
      methodRealityCopy: "What is directly observed.",
      methodEvidence: "Evidence",
      methodEvidenceCopy: "What supports or contradicts a claim.",
      methodInference: "Inference",
      methodInferenceCopy: "What follows cautiously from the evidence.",
      methodNarrative: "Narrative",
      methodNarrativeCopy: "What may amplify, simplify, or distort.",
      methodSignal: "Operational Signal",
      methodSignalCopy: "What is operationally relevant for human review.",
      portfolioKicker: "Repository-backed portfolio",
      portfolioTitle: "What exists today.",
      portfolioLead: "Every surface carries a status and a direct evidence path. Implemented work is kept separate from prototypes, controlled services, and RFC-only plans.",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / SIMULATOR",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / URL INTAKE",
      cardResearchLabel: "06 / RESEARCH",
      cardGovernanceLabel: "07 / GOVERNANCE",
      statusActive: "Active methodology",
      statusSimulator: "Working deterministic prototype",
      statusSemantic: "Early implementation",
      statusBrowser: "Browser prototype",
      statusIntake: "Implementation present · deployment unverified",
      statusResearch: "Experimental tooling",
      statusGovernance: "Active · ratified protocol",
      coreCopy: "Canonical v1 methodology, operational flow, scenarios, and meta-learning. Spanish is authoritative for v1; English is the parity reference.",
      viewCanonical: "Canonical core",
      viewStatus: "Status policy",
      simulatorTitle: "Deterministic Scenario Simulator",
      simulatorCopy: "Strict JSON-schema validation, seeded round execution, deterministic JSON output, frozen benchmarks, and structural drift diagnostics.",
      runScenario: "Run a scenario",
      runtimeContract: "Runtime contract",
      semanticTitle: "Contracts & CLI",
      semanticCopy: "Minimal claim, evidence, result, audit-log, and decision-trace contracts with a local CLI that validates and preserves structured case records. It does not evaluate or score claims.",
      inspectEngine: "Inspect the engine",
      cliContract: "CLI contract",
      operatorCopy: "A local-first PWA for structured intake, editable case records, deterministic browser triage, local memory, readable sharing, JSON, and result rendering.",
      operatorDisclosure: "This locale pack translates the portfolio description, not the Operator interface. Operator performs deterministic browser-side triage and does not execute the Semantic Engine. Unverified provenance remains unverified.",
      inspectSource: "Inspect source",
      intakeTitle: "Controlled URL intake",
      intakeCopy: "Repository code and tests define bounded URL retrieval. GitHub alone does not establish that a public endpoint is deployed or available. Retrieved text is not verified evidence.",
      inspectIntake: "Inspect intake source",
      intakeTests: "Inspect tests",
      researchTitle: "Scenario & Narrative Research",
      researchCopy: "Experimental scenario generation, mutation sweeps, boundary search, scenario telemetry, narrative consistency checks, and source-labelled research datasets.",
      labState: "Lab state",
      researchTools: "Research tools",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "A versioned protocol for separating claim, evidence, inference, uncertainty, narrative amplification, and operational relevance under human accountability.",
      readProtocol: "Read protocol",
      protectionMatrix: "Protection matrix",
      truthNote: "The public Operator produces browser-side triage drafts. The minimal Python Semantic Engine CLI runs locally. Controlled URL intake has repository code and tests, but GitHub does not confirm a live deployment. Retrieval is not verification.",
      labsKicker: "Official incubation space",
      labsLead: "Labs is part of the HUB_Optimus portfolio: a governed space for experiments before they are eligible for the Core or a product surface.",
      openLabs: "Open HUB-Optimus Labs",
      checkedOn: "Repository checked on 28 July 2026",
      labsEmpty: "Repository exists · no released artifacts",
      labsTruth: "The repository is official and currently empty. The site does not attribute unreleased engines, datasets, deployments, or security capabilities to it.",
      labsRuleOne: "Experiments remain explicitly non-canonical.",
      labsRuleTwo: "Promotion requires evidence, tests, and a reviewed PR.",
      labsRuleThree: "The Core remains authoritative.",
      boundariesKicker: "Architecture & authority",
      boundariesTitle: "One truth, explicit execution boundaries.",
      boundariesLead: "GitHub holds the authoritative project state. Public presentation, local tools, and future private deployments may consume that truth but cannot redefine it.",
      boundaryTableAria: "Capability boundaries",
      layer: "Layer",
      state: "State",
      authority: "Authority",
      layerGithub: "GitHub repository",
      stateVersioned: "Versioned / reviewed",
      authorityCanonical: "Project source of truth",
      layerPages: "Public portfolio",
      stateStatic: "Static GitHub Pages",
      authorityNone: "Presentation only",
      stateLocal: "Browser-local / controlled handoff",
      authorityAdvisory: "Advisory output",
      layerIntake: "Controlled URL intake",
      stateRepository: "Code and tests in repository",
      authorityRetrieval: "Retrieval only · deployment unverified",
      layerEngine: "Semantic Engine CLI",
      statePrivate: "Local minimal CLI",
      authorityContract: "Contract-bound draft",
      layerHuman: "Human review",
      stateMandatory: "Mandatory",
      authorityAccountability: "Final accountability",
      providerKicker: "Provider position",
      providerTitle: "Portable by design.",
      providerCopy: "GitHub provides versioning, review, CI, and the public static site. Analysis execution remains local or controlled and provider-independent. A hosting or model provider does not gain project or semantic authority.",
      platformPolicy: "Platform compatibility policy",
      futureKicker: "Future work",
      futureTitle: "Designed boundaries, not released capabilities.",
      futureLead: "These documents define constraints for possible future work. They do not prove that a product, deployment, cryptographic control plane, or enterprise service exists.",
      futureHermesLabel: "RFC / UI",
      futureEnterpriseLabel: "RFC / OPERATING MODEL",
      futurePostQuantumLabel: "RFC / SECURITY",
      hermesCopy: "Future PWA interface boundary. Not implemented.",
      enterpriseCopy: "Private operating boundary. No public service is released.",
      postQuantumTitle: "Post-quantum control plane",
      postQuantumCopy: "Standards-only planning. No cryptographic implementation.",
      evidenceKicker: "Inspect the evidence",
      evidenceTitle: "The repository outranks the presentation.",
      evidenceCopy: "Review code, contracts, tests, issues, pull requests, releases, governance, security policy, and intellectual-property terms directly on GitHub.",
      openRepository: "Open repository",
      capabilityStatus: "Capability status",
      logoAlt: "HUB_Optimus approved repository logo lockup",
      footerPortfolio: "Public portfolio",
      footerBoundary: "No analytics. No advertising cookies. No hidden scoring. GitHub remains authoritative.",
      footerNavAria: "Legal and project links",
      security: "Security",
      issues: "Issues",
      translationReview: "Russian, Hebrew, and Simplified Chinese are machine-assisted drafts; qualified human review by named reviewers is required. These interface translations are non-authoritative: canonical v1 Spanish remains authoritative, and no constitutional translation is ratified.",
      translationStatus: "Translation status",
      termbase: "Versioned termbase"
    },
    es: {
      title: "HUB_Optimus — Portfolio público versionado",
      description: "El portfolio público de HUB_Optimus respaldado por evidencia: Core, simulador determinista, contratos y CLI del Semantic Engine, Operator, investigación, gobernanza y Labs.",
      skip: "Ir al portfolio",
      homeAria: "Inicio de HUB_Optimus",
      brandDescriptor: "Portfolio público versionado",
      navAria: "Navegación principal",
      navMethod: "Método",
      navPortfolio: "Portfolio",
      navLabs: "Labs",
      navBoundaries: "Límites",
      languageAria: "Idioma",
      openGithub: "Abrir GitHub",
      heroEyebrow: "Público, versionado y respaldado por evidencia",
      sequence: "Realidad → Evidencia → Inferencia → Narrativa → Señal operativa",
      heroLead: "Un flujo de simulación diplomática que prioriza la integridad para la evaluación estructurada, la mediación preventiva y el aprendizaje sistémico.",
      heroBoundary: "Ayuda a mejorar el criterio. No es una autoridad, un motor de predicción ni un sustituto de la diplomacia.",
      explorePortfolio: "Explorar el portfolio",
      openOperator: "Abrir Operator",
      truthSource: "Fuente de verdad",
      truthCore: "Idioma canónico de v1",
      truthCoreValue: "Español",
      truthPublic: "Capa pública",
      truthPublicValue: "Páginas estáticas",
      truthRuntime: "Entorno de análisis",
      truthRuntimeValue: "Local / controlado",
      globeLabel: "Orientación geográfica",
      globeNotice: "Coordenadas ilustrativas · sin telemetría en directo",
      pauseGlobe: "Pausar",
      resumeGlobe: "Reanudar",
      globeFallbackAlt: "Gráfico geográfico aprobado de la marca HUB_Optimus",
      globeAria: "Globo interactivo proyectado a partir de coordenadas costeras reales. Las rutas son ilustrativas y no representan telemetría en directo.",
      globeControls: "Arrastra, desliza o utiliza las flechas del teclado para girar.",
      globeData: "Datos geográficos",
      principleAria: "Principio operativo",
      principle: "Observar → detectar → decidir → actuar.",
      noBuild: "No construir sin señal.",
      accountability: "La responsabilidad humana sigue siendo obligatoria.",
      methodKicker: "El método",
      methodTitle: "Separar antes de interpretar.",
      methodLead: "Las cinco etapas son una disciplina operativa. Cada una limita lo que la siguiente puede afirmar.",
      methodReality: "Realidad",
      methodRealityCopy: "Lo que se observa directamente.",
      methodEvidence: "Evidencia",
      methodEvidenceCopy: "Lo que respalda o contradice una afirmación.",
      methodInference: "Inferencia",
      methodInferenceCopy: "Lo que se desprende prudentemente de la evidencia.",
      methodNarrative: "Narrativa",
      methodNarrativeCopy: "Lo que puede amplificar, simplificar o distorsionar.",
      methodSignal: "Señal operativa",
      methodSignalCopy: "Lo que resulta operativamente relevante para la revisión humana.",
      portfolioKicker: "Portfolio respaldado por el repositorio",
      portfolioTitle: "Lo que existe hoy.",
      portfolioLead: "Cada superficie muestra su estado y enlaza directamente con la evidencia. Lo implementado se separa de los prototipos, los servicios controlados y los planes que solo existen como RFC.",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / SIMULADOR",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / INGESTA URL",
      cardResearchLabel: "06 / INVESTIGACIÓN",
      cardGovernanceLabel: "07 / GOBERNANZA",
      statusActive: "Metodología activa",
      statusSimulator: "Prototipo determinista funcional",
      statusSemantic: "Implementación inicial",
      statusBrowser: "Prototipo web",
      statusIntake: "Implementación presente · despliegue sin verificar",
      statusResearch: "Herramientas experimentales",
      statusGovernance: "Activo · protocolo ratificado",
      coreCopy: "Metodología v1 canónica, flujo operativo, escenarios y metaaprendizaje. El español es la fuente canónica de v1; el inglés es la referencia de paridad.",
      viewCanonical: "Core canónico",
      viewStatus: "Política de estado",
      simulatorTitle: "Simulador determinista de escenarios",
      simulatorCopy: "Validación estricta mediante esquema JSON, ejecución por rondas con semilla, salida JSON determinista, pruebas de referencia congeladas y diagnóstico de deriva estructural.",
      runScenario: "Ejecutar un escenario",
      runtimeContract: "Contrato de ejecución",
      semanticTitle: "Contratos y CLI",
      semanticCopy: "Contratos mínimos de afirmaciones, evidencias, resultados, auditoría y trazas de decisión, junto con una CLI local que valida y conserva expedientes estructurados. No evalúa ni puntúa afirmaciones.",
      inspectEngine: "Inspeccionar el motor",
      cliContract: "Contrato de la CLI",
      operatorCopy: "Una PWA con prioridad local para ingesta estructurada, expedientes editables, triaje determinista en el navegador, memoria local, compartición legible, JSON y visualización de resultados.",
      operatorDisclosure: "Este paquete de idioma traduce la descripción del portfolio, no la interfaz de Operator. Operator realiza un triaje determinista en el navegador y no ejecuta el Semantic Engine. La procedencia no verificada sigue sin verificar.",
      inspectSource: "Inspeccionar el código",
      intakeTitle: "Ingesta controlada de URL",
      intakeCopy: "El repositorio contiene código y pruebas para una recuperación acotada de URL. GitHub por sí solo no demuestra que exista un endpoint público desplegado o disponible. El texto recuperado no es evidencia verificada.",
      inspectIntake: "Inspeccionar el código de ingesta",
      intakeTests: "Inspeccionar las pruebas",
      researchTitle: "Investigación de escenarios y narrativas",
      researchCopy: "Generación experimental de escenarios, barridos de mutaciones, búsqueda de límites, telemetría de escenarios, controles de coherencia narrativa y conjuntos de datos de investigación con fuentes identificadas.",
      labState: "Estado del laboratorio",
      researchTools: "Herramientas de investigación",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "Un protocolo versionado para separar afirmación, evidencia, inferencia, incertidumbre, amplificación narrativa y relevancia operativa bajo responsabilidad humana.",
      readProtocol: "Leer el protocolo",
      protectionMatrix: "Matriz de protección",
      truthNote: "El Operator público genera borradores de triaje en el navegador. La CLI mínima del Semantic Engine en Python se ejecuta localmente. La ingesta controlada de URL cuenta con código y pruebas en el repositorio, pero GitHub no confirma un despliegue activo. Recuperar una fuente no equivale a verificarla.",
      labsKicker: "Espacio oficial de incubación",
      labsLead: "Labs forma parte del portfolio HUB_Optimus: un espacio gobernado para experimentos antes de que puedan incorporarse al Core o a una superficie de producto.",
      openLabs: "Abrir HUB-Optimus Labs",
      checkedOn: "Repositorio comprobado el 28 de julio de 2026",
      labsEmpty: "El repositorio existe · sin artefactos publicados",
      labsTruth: "El repositorio es oficial y actualmente está vacío. La web no le atribuye motores, datasets, despliegues ni capacidades de seguridad que no se hayan publicado.",
      labsRuleOne: "Los experimentos siguen siendo explícitamente no canónicos.",
      labsRuleTwo: "La promoción exige evidencia, pruebas y una PR revisada.",
      labsRuleThree: "El Core continúa siendo la referencia canónica.",
      boundariesKicker: "Arquitectura y autoridad",
      boundariesTitle: "Una verdad, límites de ejecución explícitos.",
      boundariesLead: "GitHub conserva el estado autoritativo del proyecto. La presentación pública, las herramientas locales y los futuros despliegues privados pueden consumir esa verdad, pero no redefinirla.",
      boundaryTableAria: "Límites de capacidades",
      layer: "Capa",
      state: "Estado",
      authority: "Autoridad",
      layerGithub: "Repositorio GitHub",
      stateVersioned: "Versionado / revisado",
      authorityCanonical: "Fuente de verdad del proyecto",
      layerPages: "Portfolio público",
      stateStatic: "GitHub Pages estático",
      authorityNone: "Solo presentación",
      stateLocal: "Local en navegador / entrega controlada",
      authorityAdvisory: "Salida consultiva",
      layerIntake: "Ingesta controlada de URL",
      stateRepository: "Código y pruebas en el repositorio",
      authorityRetrieval: "Solo recuperación · despliegue sin verificar",
      layerEngine: "CLI del Semantic Engine",
      statePrivate: "CLI local mínima",
      authorityContract: "Borrador sujeto a contrato",
      layerHuman: "Revisión humana",
      stateMandatory: "Obligatoria",
      authorityAccountability: "Responsabilidad final",
      providerKicker: "Posición sobre proveedores",
      providerTitle: "Portable por diseño.",
      providerCopy: "GitHub aporta versionado, revisión, CI y la web pública estática. La ejecución del análisis permanece local o controlada y es independiente del proveedor. Ningún proveedor de alojamiento o modelos obtiene autoridad sobre el proyecto ni autoridad semántica.",
      platformPolicy: "Política de compatibilidad de plataformas",
      futureKicker: "Trabajo futuro",
      futureTitle: "Límites diseñados, no capacidades publicadas.",
      futureLead: "Estos documentos fijan restricciones para posibles trabajos futuros. No demuestran la existencia de un producto, un despliegue, un plano de control criptográfico ni un servicio empresarial.",
      futureHermesLabel: "RFC / INTERFAZ",
      futureEnterpriseLabel: "RFC / MODELO OPERATIVO",
      futurePostQuantumLabel: "RFC / SEGURIDAD",
      hermesCopy: "Límite para una futura interfaz PWA. No implementado.",
      enterpriseCopy: "Límite operativo privado. No existe un servicio público publicado.",
      postQuantumTitle: "Plano de control poscuántico",
      postQuantumCopy: "Planificación basada únicamente en estándares. Sin implementación criptográfica.",
      evidenceKicker: "Inspeccionar la evidencia",
      evidenceTitle: "El repositorio prevalece sobre la presentación.",
      evidenceCopy: "Revisa directamente en GitHub el código, los contratos, las pruebas, los issues, las PR, las versiones, la gobernanza, la política de seguridad y las condiciones de propiedad intelectual.",
      openRepository: "Abrir el repositorio",
      capabilityStatus: "Estado de capacidades",
      logoAlt: "Logotipo oficial de HUB_Optimus aprobado en el repositorio",
      footerPortfolio: "Portfolio público",
      footerBoundary: "Sin analítica. Sin cookies publicitarias. Sin puntuación oculta. GitHub sigue siendo la fuente autoritativa.",
      footerNavAria: "Enlaces legales y del proyecto",
      security: "Seguridad",
      issues: "Issues",
      translationReview: "El ruso, el hebreo y el chino simplificado son borradores asistidos por máquina; requieren revisión humana cualificada por revisores identificados. Estas traducciones de interfaz no son autoritativas: el español canónico de v1 sigue siendo la referencia y no hay traducciones constitucionales ratificadas.",
      translationStatus: "Estado de las traducciones",
      termbase: "Base terminológica versionada"
    },
    de: {
      title: "HUB_Optimus — Versioniertes öffentliches Portfolio",
      description: "Das evidenzgestützte öffentliche Portfolio von HUB_Optimus: Core, deterministischer Simulator, Verträge und CLI der Semantic Engine, Operator, Forschung, Governance und Labs.",
      skip: "Zum Portfolio springen",
      homeAria: "HUB_Optimus Startseite",
      brandDescriptor: "Versioniertes öffentliches Portfolio",
      navAria: "Hauptnavigation",
      navMethod: "Methode",
      navPortfolio: "Portfolio",
      navLabs: "Labs",
      navBoundaries: "Grenzen",
      languageAria: "Sprache",
      openGithub: "GitHub öffnen",
      heroEyebrow: "Öffentlich, versioniert und evidenzgestützt",
      sequence: "Realität → Evidenz → Schlussfolgerung → Narrativ → Operatives Signal",
      heroLead: "Ein integritätsorientierter Workflow für diplomatische Simulation, strukturierte Bewertung, präventive Vermittlung und systemisches Lernen.",
      heroBoundary: "Das System unterstützt bessere Urteile. Es ist weder Autorität noch Prognosemaschine noch Ersatz für Diplomatie.",
      explorePortfolio: "Portfolio erkunden",
      openOperator: "Operator öffnen",
      truthSource: "Quelle der Wahrheit",
      truthCore: "Kanonische Sprache von v1",
      truthCoreValue: "Spanisch",
      truthPublic: "Öffentliche Ebene",
      truthPublicValue: "Statische Seiten",
      truthRuntime: "Analyseumgebung",
      truthRuntimeValue: "Lokal / kontrolliert",
      globeLabel: "Geografische Orientierung",
      globeNotice: "Illustrative Koordinaten · keine Live-Telemetrie",
      pauseGlobe: "Pausieren",
      resumeGlobe: "Fortsetzen",
      globeFallbackAlt: "Freigegebene geografische Markengrafik von HUB_Optimus",
      globeAria: "Interaktiver Globus, projiziert aus realen Küstenkoordinaten. Die Routen sind illustrativ und stellen keine Live-Telemetrie dar.",
      globeControls: "Mit Ziehen, Wischen oder den Pfeiltasten drehen.",
      globeData: "Geografische Daten",
      principleAria: "Arbeitsprinzip",
      principle: "Beobachten → erkennen → entscheiden → handeln.",
      noBuild: "Keine Umsetzung ohne Signal.",
      accountability: "Menschliche Verantwortung bleibt zwingend.",
      methodKicker: "Die Methode",
      methodTitle: "Trennen, bevor interpretiert wird.",
      methodLead: "Die fünf Stufen bilden eine operative Disziplin. Jede Stufe begrenzt, was die nächste behaupten darf.",
      methodReality: "Realität",
      methodRealityCopy: "Was unmittelbar beobachtet wird.",
      methodEvidence: "Evidenz",
      methodEvidenceCopy: "Was eine Behauptung stützt oder ihr widerspricht.",
      methodInference: "Schlussfolgerung",
      methodInferenceCopy: "Was sich vorsichtig aus der Evidenz ableiten lässt.",
      methodNarrative: "Narrativ",
      methodNarrativeCopy: "Was verstärken, vereinfachen oder verzerren kann.",
      methodSignal: "Operatives Signal",
      methodSignalCopy: "Was für die menschliche Prüfung operativ relevant ist.",
      portfolioKicker: "Repository-gestütztes Portfolio",
      portfolioTitle: "Was heute tatsächlich existiert.",
      portfolioLead: "Jede Oberfläche zeigt ihren Status und verlinkt direkt auf die Evidenz. Implementiertes wird klar von Prototypen, kontrollierten Diensten und reinen RFC-Planungen getrennt.",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / SIMULATOR",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / URL-ERFASSUNG",
      cardResearchLabel: "06 / FORSCHUNG",
      cardGovernanceLabel: "07 / GOVERNANCE",
      statusActive: "Aktive Methodik",
      statusSimulator: "Funktionsfähiger deterministischer Prototyp",
      statusSemantic: "Frühe Implementierung",
      statusBrowser: "Browser-Prototyp",
      statusIntake: "Implementierung vorhanden · Deployment ungeprüft",
      statusResearch: "Experimentelle Werkzeuge",
      statusGovernance: "Aktiv · ratifiziertes Protokoll",
      coreCopy: "Kanonische v1-Methodik, operativer Ablauf, Szenarien und Meta-Lernen. Spanisch ist für v1 maßgeblich; Englisch dient als Paritätsreferenz.",
      viewCanonical: "Kanonischer Core",
      viewStatus: "Statusrichtlinie",
      simulatorTitle: "Deterministischer Szenario-Simulator",
      simulatorCopy: "Strikte JSON-Schema-Validierung, rundenbasierte Ausführung mit Seed, deterministische JSON-Ausgabe, eingefrorene Benchmarks und Diagnose struktureller Abweichungen.",
      runScenario: "Szenario ausführen",
      runtimeContract: "Laufzeitvertrag",
      semanticTitle: "Verträge & CLI",
      semanticCopy: "Minimale Verträge für Behauptungen, Evidenz, Ergebnisse, Audit-Logs und Entscheidungsspuren sowie eine lokale CLI, die strukturierte Falldaten validiert und erhält. Sie bewertet oder bepunktet keine Behauptungen.",
      inspectEngine: "Engine prüfen",
      cliContract: "CLI-Vertrag",
      operatorCopy: "Eine lokal arbeitende PWA für strukturierte Erfassung, editierbare Falldaten, deterministische Browser-Triage, lokalen Speicher, lesbares Teilen, JSON und Ergebnisdarstellung.",
      operatorDisclosure: "Dieses Sprachpaket übersetzt die Portfolio-Beschreibung, nicht die Operator-Oberfläche. Operator führt eine deterministische Browser-Triage aus und führt die Semantic Engine nicht aus. Ungeprüfte Herkunft bleibt ungeprüft.",
      inspectSource: "Quellcode prüfen",
      intakeTitle: "Kontrollierte URL-Erfassung",
      intakeCopy: "Das Repository enthält Code und Tests für einen begrenzten URL-Abruf. GitHub allein belegt nicht, dass ein öffentlicher Endpunkt bereitgestellt oder verfügbar ist. Abgerufener Text ist keine verifizierte Evidenz.",
      inspectIntake: "Quellcode der Erfassung prüfen",
      intakeTests: "Tests prüfen",
      researchTitle: "Szenario- & Narrativforschung",
      researchCopy: "Experimentelle Szenariogenerierung, Mutationsläufe, Grenzwertsuche, Szenario-Telemetrie, Konsistenzprüfungen für Narrative und quellgekennzeichnete Forschungsdatensätze.",
      labState: "Laborstatus",
      researchTools: "Forschungswerkzeuge",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "Ein versioniertes Protokoll zur Trennung von Behauptung, Evidenz, Schlussfolgerung, Unsicherheit, narrativer Verstärkung und operativer Relevanz unter menschlicher Verantwortung.",
      readProtocol: "Protokoll lesen",
      protectionMatrix: "Schutzmatrix",
      truthNote: "Der öffentliche Operator erzeugt Triage-Entwürfe im Browser. Die minimale Python-CLI der Semantic Engine wird lokal ausgeführt. Für die kontrollierte URL-Erfassung liegen Code und Tests im Repository vor, doch GitHub bestätigt kein aktives Deployment. Abruf ist keine Verifizierung.",
      labsKicker: "Offizieller Inkubationsraum",
      labsLead: "Labs ist Teil des HUB_Optimus-Portfolios: ein geregelter Raum für Experimente, bevor diese für den Core oder eine Produktoberfläche infrage kommen.",
      openLabs: "HUB-Optimus Labs öffnen",
      checkedOn: "Repository geprüft am 28. Juli 2026",
      labsEmpty: "Repository vorhanden · keine veröffentlichten Artefakte",
      labsTruth: "Das Repository ist offiziell und derzeit leer. Die Website schreibt ihm keine unveröffentlichten Engines, Datensätze, Deployments oder Sicherheitsfunktionen zu.",
      labsRuleOne: "Experimente bleiben ausdrücklich nicht kanonisch.",
      labsRuleTwo: "Eine Übernahme erfordert Evidenz, Tests und einen geprüften PR.",
      labsRuleThree: "Der Core bleibt maßgeblich.",
      boundariesKicker: "Architektur & Autorität",
      boundariesTitle: "Eine Wahrheit, klare Ausführungsgrenzen.",
      boundariesLead: "GitHub hält den maßgeblichen Projektstand. Öffentliche Darstellung, lokale Werkzeuge und künftige private Deployments dürfen diese Wahrheit nutzen, aber nicht neu definieren.",
      boundaryTableAria: "Fähigkeitsgrenzen",
      layer: "Ebene",
      state: "Status",
      authority: "Autorität",
      layerGithub: "GitHub-Repository",
      stateVersioned: "Versioniert / geprüft",
      authorityCanonical: "Quelle der Projektwahrheit",
      layerPages: "Öffentliches Portfolio",
      stateStatic: "Statische GitHub Pages",
      authorityNone: "Nur Darstellung",
      stateLocal: "Browser-lokal / kontrollierte Übergabe",
      authorityAdvisory: "Beratende Ausgabe",
      layerIntake: "Kontrollierte URL-Erfassung",
      stateRepository: "Code und Tests im Repository",
      authorityRetrieval: "Nur Abruf · Deployment ungeprüft",
      layerEngine: "Semantic Engine CLI",
      statePrivate: "Minimale lokale CLI",
      authorityContract: "Vertragsgebundener Entwurf",
      layerHuman: "Menschliche Prüfung",
      stateMandatory: "Zwingend",
      authorityAccountability: "Endverantwortung",
      providerKicker: "Provider-Position",
      providerTitle: "Portabel konzipiert.",
      providerCopy: "GitHub übernimmt Versionierung, Prüfung, CI und die öffentliche statische Website. Die Analyseausführung bleibt lokal oder kontrolliert und ist anbieterunabhängig. Ein Hosting- oder Modellanbieter erhält weder Projektautorität noch semantische Autorität.",
      platformPolicy: "Richtlinie zur Plattformkompatibilität",
      futureKicker: "Künftige Arbeit",
      futureTitle: "Definierte Grenzen, keine veröffentlichten Fähigkeiten.",
      futureLead: "Diese Dokumente definieren Grenzen für mögliche künftige Arbeit. Sie belegen nicht, dass ein Produkt, Deployment, kryptografischer Kontrollplan oder Unternehmensdienst existiert.",
      futureHermesLabel: "RFC / OBERFLÄCHE",
      futureEnterpriseLabel: "RFC / BETRIEBSMODELL",
      futurePostQuantumLabel: "RFC / SICHERHEIT",
      hermesCopy: "Grenze für eine künftige PWA-Oberfläche. Nicht implementiert.",
      enterpriseCopy: "Private Betriebsgrenze. Kein öffentlicher Dienst ist veröffentlicht.",
      postQuantumTitle: "Postquanten-Kontrollplan",
      postQuantumCopy: "Reine Standardplanung. Keine kryptografische Implementierung.",
      evidenceKicker: "Evidenz prüfen",
      evidenceTitle: "Das Repository steht über der Darstellung.",
      evidenceCopy: "Code, Verträge, Tests, Issues, Pull Requests, Releases, Governance, Sicherheitsrichtlinie und Schutzrechte können direkt auf GitHub geprüft werden.",
      openRepository: "Repository öffnen",
      capabilityStatus: "Fähigkeitsstatus",
      logoAlt: "Im Repository freigegebenes HUB_Optimus-Logo",
      footerPortfolio: "Öffentliches Portfolio",
      footerBoundary: "Keine Analytik. Keine Werbe-Cookies. Keine verborgene Bewertung. GitHub bleibt maßgeblich.",
      footerNavAria: "Rechtliche und projektbezogene Links",
      security: "Sicherheit",
      issues: "Issues",
      translationReview: "Russisch, Hebräisch und vereinfachtes Chinesisch sind maschinell unterstützte Entwürfe; eine qualifizierte menschliche Prüfung durch namentlich benannte Prüfende ist erforderlich. Diese Oberflächenübersetzungen sind nicht maßgeblich: Das kanonische Spanisch von v1 bleibt maßgeblich, und keine Verfassungsübersetzung ist ratifiziert.",
      translationStatus: "Übersetzungsstatus",
      termbase: "Versionierte Termbase"
    },
    ru: {
      title: "HUB_Optimus — Версионируемый публичный портфель",
      description: "Публичный портфель HUB_Optimus, подкреплённый доказательствами: Core, детерминированный симулятор, контракты и CLI Semantic Engine, Operator, исследования, управление и Labs.",
      skip: "Перейти к портфелю",
      homeAria: "Главная страница HUB_Optimus",
      brandDescriptor: "Версионируемый публичный портфель",
      navAria: "Основная навигация",
      navMethod: "Метод",
      navPortfolio: "Портфель",
      navLabs: "Labs",
      navBoundaries: "Границы",
      languageAria: "Язык",
      openGithub: "Открыть GitHub",
      heroEyebrow: "Публично, версионируемо, с опорой на доказательства",
      sequence: "Реальность → Доказательства → Вывод → Нарратив → Операционный сигнал",
      heroLead: "Рабочий процесс дипломатического моделирования с приоритетом целостности для структурированной оценки, превентивного посредничества и системного обучения.",
      heroBoundary: "Он помогает улучшить суждение. Это не орган власти, не механизм прогнозирования и не замена дипломатии.",
      explorePortfolio: "Изучить портфель",
      openOperator: "Открыть Operator",
      truthSource: "Источник истины",
      truthCore: "Канонический язык v1",
      truthCoreValue: "Испанский",
      truthPublic: "Публичный слой",
      truthPublicValue: "Статические Pages",
      truthRuntime: "Среда анализа",
      truthRuntimeValue: "Локальная / контролируемая",
      globeLabel: "Географическая ориентация",
      globeNotice: "Иллюстративные координаты · без телеметрии в реальном времени",
      pauseGlobe: "Приостановить",
      resumeGlobe: "Продолжить",
      globeFallbackAlt: "Утверждённое географическое изображение бренда HUB_Optimus",
      globeAria: "Интерактивный глобус, построенный по реальным координатам береговой линии. Маршруты носят иллюстративный характер и не являются телеметрией в реальном времени.",
      globeControls: "Перетаскивайте, проводите пальцем или используйте клавиши со стрелками для вращения.",
      globeData: "Географические данные",
      principleAria: "Операционный принцип",
      principle: "Наблюдать → обнаруживать → решать → действовать.",
      noBuild: "Не создавать без сигнала.",
      accountability: "Ответственность человека остаётся обязательной.",
      methodKicker: "Метод",
      methodTitle: "Сначала разделять, затем интерпретировать.",
      methodLead: "Пять этапов образуют операционную дисциплину. Каждый этап ограничивает утверждения, допустимые на следующем.",
      methodReality: "Реальность",
      methodRealityCopy: "То, что наблюдается непосредственно.",
      methodEvidence: "Доказательства",
      methodEvidenceCopy: "То, что подтверждает утверждение или противоречит ему.",
      methodInference: "Вывод",
      methodInferenceCopy: "То, что можно осторожно вывести из доказательств.",
      methodNarrative: "Нарратив",
      methodNarrativeCopy: "То, что может усиливать, упрощать или искажать.",
      methodSignal: "Операционный сигнал",
      methodSignalCopy: "То, что имеет операционное значение для проверки человеком.",
      portfolioKicker: "Портфель, подтверждённый репозиторием",
      portfolioTitle: "Что существует сегодня.",
      portfolioLead: "Каждая поверхность имеет статус и прямой путь к доказательствам. Реализованное отделено от прототипов, контролируемых сервисов и планов, существующих только в RFC.",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / СИМУЛЯТОР",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / ПОЛУЧЕНИЕ URL",
      cardResearchLabel: "06 / ИССЛЕДОВАНИЯ",
      cardGovernanceLabel: "07 / УПРАВЛЕНИЕ",
      statusActive: "Активная методология",
      statusSimulator: "Рабочий детерминированный прототип",
      statusSemantic: "Ранняя реализация",
      statusBrowser: "Браузерный прототип",
      statusIntake: "Реализация присутствует · развёртывание не проверено",
      statusResearch: "Экспериментальные инструменты",
      statusGovernance: "Активен · протокол ратифицирован",
      coreCopy: "Каноническая методология v1, операционный поток, сценарии и метаобучение. Испанский является авторитетным для v1; английский служит эталоном паритета.",
      viewCanonical: "Канонический Core",
      viewStatus: "Политика статуса",
      simulatorTitle: "Детерминированный симулятор сценариев",
      simulatorCopy: "Строгая проверка по JSON Schema, раундовое выполнение с заданным seed, детерминированный вывод JSON, зафиксированные эталонные тесты и диагностика структурного дрейфа.",
      runScenario: "Запустить сценарий",
      runtimeContract: "Контракт среды выполнения",
      semanticTitle: "Контракты и CLI",
      semanticCopy: "Минимальные контракты утверждений, доказательств, результатов, журнала аудита и трассы решений с локальным CLI, который проверяет и сохраняет структурированные материалы дела. Он не оценивает утверждения и не присваивает им баллы.",
      inspectEngine: "Изучить движок",
      cliContract: "Контракт CLI",
      operatorCopy: "Локальная PWA для структурированного ввода, редактируемых материалов дела, детерминированной браузерной сортировки, локальной памяти, удобного обмена, JSON и отображения результатов.",
      operatorDisclosure: "Этот языковой пакет переводит описание портфеля, но не интерфейс Operator. Operator выполняет детерминированную сортировку в браузере и не запускает Semantic Engine. Непроверенное происхождение остаётся непроверенным.",
      inspectSource: "Изучить исходный код",
      intakeTitle: "Контролируемое получение URL",
      intakeCopy: "Код и тесты в репозитории определяют ограниченное получение содержимого по URL. Один лишь GitHub не подтверждает, что публичная конечная точка развёрнута или доступна. Полученный текст не является проверенным доказательством.",
      inspectIntake: "Изучить код получения",
      intakeTests: "Изучить тесты",
      researchTitle: "Исследование сценариев и нарративов",
      researchCopy: "Экспериментальная генерация сценариев, серии мутаций, поиск границ, телеметрия сценариев, проверки согласованности нарратива и исследовательские наборы данных с указанием источников.",
      labState: "Состояние лаборатории",
      researchTools: "Инструменты исследования",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "Версионируемый протокол разделения утверждения, доказательств, вывода, неопределённости, нарративного усиления и операционной значимости при ответственности человека.",
      readProtocol: "Прочитать протокол",
      protectionMatrix: "Матрица защиты",
      truthNote: "Публичный Operator создаёт в браузере черновики первичной сортировки. Минимальный Python CLI Semantic Engine запускается локально. Для контролируемого получения URL в репозитории есть код и тесты, однако GitHub не подтверждает активное развёртывание. Получение не является проверкой.",
      labsKicker: "Официальное пространство инкубации",
      labsLead: "Labs входит в портфель HUB_Optimus: это управляемое пространство для экспериментов до их допуска в Core или продуктовую поверхность.",
      openLabs: "Открыть HUB-Optimus Labs",
      checkedOn: "Репозиторий проверен 28 июля 2026 года",
      labsEmpty: "Репозиторий существует · опубликованных артефактов нет",
      labsTruth: "Репозиторий является официальным и сейчас пуст. Сайт не приписывает ему неопубликованные движки, наборы данных, развёртывания или возможности безопасности.",
      labsRuleOne: "Эксперименты явно остаются неканоническими.",
      labsRuleTwo: "Перенос требует доказательств, тестов и проверенного PR.",
      labsRuleThree: "Core остаётся авторитетным.",
      boundariesKicker: "Архитектура и полномочия",
      boundariesTitle: "Одна истина, явные границы выполнения.",
      boundariesLead: "GitHub хранит авторитетное состояние проекта. Публичное представление, локальные инструменты и будущие частные развёртывания могут использовать эту истину, но не могут её переопределять.",
      boundaryTableAria: "Границы возможностей",
      layer: "Слой",
      state: "Состояние",
      authority: "Полномочия",
      layerGithub: "Репозиторий GitHub",
      stateVersioned: "Версионируется / проверяется",
      authorityCanonical: "Источник истины проекта",
      layerPages: "Публичный портфель",
      stateStatic: "Статические GitHub Pages",
      authorityNone: "Только представление",
      stateLocal: "Локально в браузере / контролируемая передача",
      authorityAdvisory: "Рекомендательный результат",
      layerIntake: "Контролируемое получение URL",
      stateRepository: "Код и тесты в репозитории",
      authorityRetrieval: "Только получение · развёртывание не проверено",
      layerEngine: "CLI Semantic Engine",
      statePrivate: "Минимальный локальный CLI",
      authorityContract: "Черновик в рамках контракта",
      layerHuman: "Проверка человеком",
      stateMandatory: "Обязательна",
      authorityAccountability: "Конечная ответственность",
      providerKicker: "Позиция по провайдерам",
      providerTitle: "Переносимость заложена в проект.",
      providerCopy: "GitHub обеспечивает версионирование, проверку, CI и публичный статический сайт. Выполнение анализа остаётся локальным или контролируемым и не зависит от провайдера. Провайдер хостинга или моделей не получает полномочий над проектом или смысловой интерпретацией.",
      platformPolicy: "Политика совместимости платформ",
      futureKicker: "Будущая работа",
      futureTitle: "Спроектированные границы, а не выпущенные возможности.",
      futureLead: "Эти документы задают ограничения для возможной будущей работы. Они не доказывают существование продукта, развёртывания, криптографической плоскости управления или корпоративного сервиса.",
      futureHermesLabel: "RFC / ИНТЕРФЕЙС",
      futureEnterpriseLabel: "RFC / ОПЕРАЦИОННАЯ МОДЕЛЬ",
      futurePostQuantumLabel: "RFC / БЕЗОПАСНОСТЬ",
      hermesCopy: "Граница будущего интерфейса PWA. Не реализовано.",
      enterpriseCopy: "Частная операционная граница. Публичный сервис не выпущен.",
      postQuantumTitle: "Постквантовая плоскость управления",
      postQuantumCopy: "Планирование только на основе стандартов. Криптографической реализации нет.",
      evidenceKicker: "Изучить доказательства",
      evidenceTitle: "Репозиторий важнее презентации.",
      evidenceCopy: "Проверяйте код, контракты, тесты, issues, pull requests, релизы, управление, политику безопасности и условия интеллектуальной собственности непосредственно на GitHub.",
      openRepository: "Открыть репозиторий",
      capabilityStatus: "Статус возможностей",
      logoAlt: "Утверждённый в репозитории логотип HUB_Optimus",
      footerPortfolio: "Публичный портфель",
      footerBoundary: "Без аналитики. Без рекламных cookies. Без скрытого оценивания. GitHub остаётся авторитетным.",
      footerNavAria: "Юридические ссылки и ссылки проекта",
      security: "Безопасность",
      issues: "Issues",
      translationReview: "Русская, ивритская и упрощённая китайская версии являются черновиками, созданными с машинной поддержкой; требуется квалифицированная проверка указанными по имени специалистами. Эти переводы интерфейса не являются авторитетными: канонический испанский v1 сохраняет приоритет, а конституционные переводы не ратифицированы.",
      translationStatus: "Статус перевода",
      termbase: "Версионируемая терминологическая база"
    },
    he: {
      title: "HUB_Optimus — פורטפוליו ציבורי מנוהל בגרסאות",
      description: "הפורטפוליו הציבורי של HUB_Optimus, המבוסס על ראיות: Core, סימולטור דטרמיניסטי, החוזים וממשק שורת הפקודה של Semantic Engine, ‏Operator, מחקר, ממשל ו-Labs.",
      skip: "דילוג לפורטפוליו",
      homeAria: "דף הבית של HUB_Optimus",
      brandDescriptor: "פורטפוליו ציבורי מנוהל בגרסאות",
      navAria: "ניווט ראשי",
      navMethod: "שיטה",
      navPortfolio: "פורטפוליו",
      navLabs: "Labs",
      navBoundaries: "גבולות",
      languageAria: "שפה",
      openGithub: "פתיחת GitHub",
      heroEyebrow: "ציבורי, מנוהל בגרסאות ומבוסס על ראיות",
      sequence: "מציאות ← ראיות ← הסקה ← נרטיב ← אות תפעולי",
      heroLead: "תהליך עבודה לסימולציה דיפלומטית, המעמיד יושרה בראש סדר העדיפויות, לצורך הערכה מובנית, תיווך מונע ולמידה מערכתית.",
      heroBoundary: "הוא מסייע לשיקול דעת טוב יותר. הוא אינו סמכות, מנוע חיזוי או תחליף לדיפלומטיה.",
      explorePortfolio: "עיון בפורטפוליו",
      openOperator: "פתיחת Operator",
      truthSource: "מקור האמת",
      truthCore: "השפה הקנונית של v1",
      truthCoreValue: "ספרדית",
      truthPublic: "שכבה ציבורית",
      truthPublicValue: "דפים סטטיים",
      truthRuntime: "סביבת ניתוח",
      truthRuntimeValue: "מקומית / מבוקרת",
      globeLabel: "התמצאות גאוגרפית",
      globeNotice: "קואורדינטות להמחשה · ללא טלמטריה בזמן אמת",
      pauseGlobe: "השהיה",
      resumeGlobe: "המשך",
      globeFallbackAlt: "יצירת המותג הגאוגרפית המאושרת של HUB_Optimus",
      globeAria: "גלובוס אינטראקטיבי המוקרן מקואורדינטות אמיתיות של קווי חוף. המסלולים מיועדים להמחשה ואינם טלמטריה בזמן אמת.",
      globeControls: "גררו, החליקו או השתמשו במקשי החצים כדי לסובב.",
      globeData: "נתונים גאוגרפיים",
      principleAria: "עיקרון תפעולי",
      principle: "להתבונן ← לזהות ← להחליט ← לפעול.",
      noBuild: "אין לבנות ללא אות.",
      accountability: "אחריות אנושית נותרת חובה.",
      methodKicker: "השיטה",
      methodTitle: "להפריד לפני שמפרשים.",
      methodLead: "חמשת השלבים הם משמעת תפעולית. כל שלב מגביל את הטענות שהשלב הבא רשאי להעלות.",
      methodReality: "מציאות",
      methodRealityCopy: "מה שנצפה ישירות.",
      methodEvidence: "ראיות",
      methodEvidenceCopy: "מה שתומך בטענה או סותר אותה.",
      methodInference: "הסקה",
      methodInferenceCopy: "מה שנובע בזהירות מן הראיות.",
      methodNarrative: "נרטיב",
      methodNarrativeCopy: "מה שעלול להעצים, לפשט או לעוות.",
      methodSignal: "אות תפעולי",
      methodSignalCopy: "מה שרלוונטי מבחינה תפעולית לביקורת אנושית.",
      portfolioKicker: "פורטפוליו המגובה במאגר",
      portfolioTitle: "מה קיים כיום.",
      portfolioLead: "כל משטח מציג מצב ונתיב ישיר לראיות. עבודה מיושמת מופרדת מאבות טיפוס, משירותים מבוקרים ומתוכניות הקיימות רק כ-RFC.",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / סימולטור",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / קליטת URL",
      cardResearchLabel: "06 / מחקר",
      cardGovernanceLabel: "07 / ממשל",
      statusActive: "מתודולוגיה פעילה",
      statusSimulator: "אב טיפוס דטרמיניסטי פועל",
      statusSemantic: "יישום התחלתי",
      statusBrowser: "אב טיפוס בדפדפן",
      statusIntake: "קיים יישום · הפריסה לא אומתה",
      statusResearch: "כלים ניסיוניים",
      statusGovernance: "פעיל · פרוטוקול שאושרר",
      coreCopy: "מתודולוגיית v1 הקנונית, זרימה תפעולית, תרחישים ומטה-למידה. ספרדית היא המקור הסמכותי ל-v1; אנגלית היא ייחוס לשוויון תוכן.",
      viewCanonical: "Core קנוני",
      viewStatus: "מדיניות מצב",
      simulatorTitle: "סימולטור תרחישים דטרמיניסטי",
      simulatorCopy: "אימות קפדני לפי JSON Schema, הרצה בסבבים עם seed, פלט JSON דטרמיניסטי, מבחני ייחוס קפואים ואבחון סטייה מבנית.",
      runScenario: "הרצת תרחיש",
      runtimeContract: "חוזה סביבת הריצה",
      semanticTitle: "חוזים וממשק שורת פקודה",
      semanticCopy: "חוזים מינימליים לטענות, ראיות, תוצאות, יומן ביקורת ועקבות החלטה, יחד עם ממשק שורת פקודה מקומי שמאמת ושומר תיקי מקרה מובנים. הוא אינו מעריך טענות ואינו מעניק להן ציונים.",
      inspectEngine: "בדיקת המנוע",
      cliContract: "חוזה ממשק שורת הפקודה",
      operatorCopy: "יישום PWA בגישה מקומית לקליטה מובנית, תיקי מקרה הניתנים לעריכה, מיון דטרמיניסטי בדפדפן, זיכרון מקומי, שיתוף קריא, JSON והצגת תוצאות.",
      operatorDisclosure: "חבילת שפה זו מתרגמת את תיאור הפורטפוליו, אך לא את ממשק Operator. ‏Operator מבצע מיון דטרמיניסטי בדפדפן ואינו מפעיל את Semantic Engine. מקור שלא אומת נשאר בלתי מאומת.",
      inspectSource: "בדיקת קוד המקור",
      intakeTitle: "קליטת URL מבוקרת",
      intakeCopy: "הקוד והבדיקות במאגר מגדירים אחזור מוגבל מ-URL. ‏GitHub לבדו אינו מוכיח שנקודת קצה ציבורית נפרסה או זמינה. טקסט שאוחזר אינו ראיה מאומתת.",
      inspectIntake: "בדיקת קוד הקליטה",
      intakeTests: "בדיקת הבדיקות",
      researchTitle: "מחקר תרחישים ונרטיבים",
      researchCopy: "יצירת תרחישים ניסיונית, סריקות מוטציה, חיפוש גבולות, טלמטריית תרחישים, בדיקות עקביות נרטיבית ומערכי נתוני מחקר עם ציון מקור.",
      labState: "מצב המעבדה",
      researchTools: "כלי מחקר",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "פרוטוקול מנוהל בגרסאות להפרדת טענה, ראיות, הסקה, אי-ודאות, הגברה נרטיבית ורלוונטיות תפעולית תחת אחריות אנושית.",
      readProtocol: "קריאת הפרוטוקול",
      protectionMatrix: "מטריצת הגנה",
      truthNote: "Operator הציבורי יוצר בדפדפן טיוטות למיון ראשוני. ממשק שורת הפקודה המינימלי של Semantic Engine ב-Python פועל מקומית. לקליטת URL מבוקרת יש קוד ובדיקות במאגר, אך GitHub אינו מאשר פריסה פעילה. אחזור אינו אימות.",
      labsKicker: "מרחב הדגרה רשמי",
      labsLead: "Labs הוא חלק מפורטפוליו HUB_Optimus: מרחב מוסדר לניסויים לפני שניתן לשקול את קבלתם ל-Core או למשטח מוצר.",
      openLabs: "פתיחת HUB-Optimus Labs",
      checkedOn: "המאגר נבדק ב-28 ביולי 2026",
      labsEmpty: "המאגר קיים · אין פריטים שפורסמו",
      labsTruth: "המאגר רשמי וכרגע ריק. האתר אינו מייחס לו מנועים, מערכי נתונים, פריסות או יכולות אבטחה שלא פורסמו.",
      labsRuleOne: "ניסויים נשארים במפורש לא-קנוניים.",
      labsRuleTwo: "קידום דורש ראיות, בדיקות ו-PR שנבדק.",
      labsRuleThree: "ה-Core נשאר סמכותי.",
      boundariesKicker: "ארכיטקטורה וסמכות",
      boundariesTitle: "אמת אחת, גבולות ביצוע מפורשים.",
      boundariesLead: "GitHub מחזיק במצב הסמכותי של הפרויקט. המצגת הציבורית, הכלים המקומיים ופריסות פרטיות עתידיות רשאים לצרוך אמת זו, אך אינם רשאים להגדיר אותה מחדש.",
      boundaryTableAria: "גבולות יכולת",
      layer: "שכבה",
      state: "מצב",
      authority: "סמכות",
      layerGithub: "מאגר GitHub",
      stateVersioned: "מנוהל בגרסאות / נבדק",
      authorityCanonical: "מקור האמת של הפרויקט",
      layerPages: "פורטפוליו ציבורי",
      stateStatic: "GitHub Pages סטטיים",
      authorityNone: "מצגת בלבד",
      stateLocal: "מקומי בדפדפן / מסירה מבוקרת",
      authorityAdvisory: "פלט מייעץ",
      layerIntake: "קליטת URL מבוקרת",
      stateRepository: "קוד ובדיקות במאגר",
      authorityRetrieval: "אחזור בלבד · הפריסה לא אומתה",
      layerEngine: "ממשק שורת הפקודה של Semantic Engine",
      statePrivate: "ממשק שורת פקודה מקומי מינימלי",
      authorityContract: "טיוטה הכפופה לחוזה",
      layerHuman: "ביקורת אנושית",
      stateMandatory: "חובה",
      authorityAccountability: "אחריות סופית",
      providerKicker: "עמדה לגבי ספקים",
      providerTitle: "ניידות מובנית בתכנון.",
      providerCopy: "GitHub מספק ניהול גרסאות, ביקורת, CI ואת האתר הציבורי הסטטי. הרצת הניתוח נשארת מקומית או מבוקרת ובלתי תלויה בספק. ספק אירוח או מודל אינו מקבל סמכות על הפרויקט או סמכות סמנטית.",
      platformPolicy: "מדיניות תאימות פלטפורמות",
      futureKicker: "עבודה עתידית",
      futureTitle: "גבולות מתוכננים, לא יכולות שפורסמו.",
      futureLead: "מסמכים אלה מגדירים מגבלות לעבודה עתידית אפשרית. הם אינם מוכיחים שקיימים מוצר, פריסה, מישור בקרה קריפטוגרפי או שירות ארגוני.",
      futureHermesLabel: "RFC / ממשק",
      futureEnterpriseLabel: "RFC / מודל תפעולי",
      futurePostQuantumLabel: "RFC / אבטחה",
      hermesCopy: "גבול לממשק PWA עתידי. לא מיושם.",
      enterpriseCopy: "גבול תפעולי פרטי. לא פורסם שירות ציבורי.",
      postQuantumTitle: "מישור בקרה פוסט-קוונטי",
      postQuantumCopy: "תכנון המבוסס על תקנים בלבד. אין יישום קריפטוגרפי.",
      evidenceKicker: "בדיקת הראיות",
      evidenceTitle: "המאגר גובר על המצגת.",
      evidenceCopy: "בדקו ישירות ב-GitHub את הקוד, החוזים, הבדיקות, ה-issues, ה-pull requests, הגרסאות, הממשל, מדיניות האבטחה ותנאי הקניין הרוחני.",
      openRepository: "פתיחת המאגר",
      capabilityStatus: "מצב היכולות",
      logoAlt: "לוגו HUB_Optimus המאושר במאגר",
      footerPortfolio: "פורטפוליו ציבורי",
      footerBoundary: "ללא ניתוח התנהגות. ללא עוגיות פרסום. ללא ניקוד נסתר. GitHub נשאר סמכותי.",
      footerNavAria: "קישורים משפטיים וקישורי הפרויקט",
      security: "אבטחה",
      issues: "Issues",
      translationReview: "רוסית, עברית וסינית מפושטת הן טיוטות בסיוע מכונה; נדרשת ביקורת אנושית מוסמכת בידי בודקים שיזוהו בשמם. תרגומי הממשק האלה אינם סמכותיים: הספרדית הקנונית של v1 נשארת סמכותית, ולא אושרר שום תרגום חוקתי.",
      translationStatus: "מצב התרגום",
      termbase: "בסיס מונחים מנוהל בגרסאות"
    },
    "zh-Hans": {
      title: "HUB_Optimus — 版本化公开项目组合",
      description: "以证据为依据的 HUB_Optimus 公开项目组合：Core、确定性模拟器、Semantic Engine 合约与 CLI、Operator、研究、治理和 Labs。",
      skip: "跳至项目组合",
      homeAria: "HUB_Optimus 首页",
      brandDescriptor: "版本化公开项目组合",
      navAria: "主导航",
      navMethod: "方法",
      navPortfolio: "项目组合",
      navLabs: "Labs",
      navBoundaries: "边界",
      languageAria: "语言",
      openGithub: "打开 GitHub",
      heroEyebrow: "公开、版本化、以证据为依据",
      sequence: "现实 → 证据 → 推断 → 叙事 → 运营信号",
      heroLead: "以完整性为先的外交模拟工作流，用于结构化评估、预防性调解和系统性学习。",
      heroBoundary: "它帮助改善判断。它不是权威机构、预测引擎，也不能替代外交。",
      explorePortfolio: "浏览项目组合",
      openOperator: "打开 Operator",
      truthSource: "事实依据来源",
      truthCore: "v1 规范语言",
      truthCoreValue: "西班牙语",
      truthPublic: "公开层",
      truthPublicValue: "静态 Pages",
      truthRuntime: "分析运行环境",
      truthRuntimeValue: "本地 / 受控",
      globeLabel: "地理方向",
      globeNotice: "坐标仅作说明 · 无实时遥测",
      pauseGlobe: "暂停",
      resumeGlobe: "继续",
      globeFallbackAlt: "经仓库认可的 HUB_Optimus 地理品牌图像",
      globeAria: "依据真实海岸线坐标投影的交互式地球仪。路线仅作说明，并非实时遥测。",
      globeControls: "拖动、滑动或使用方向键旋转。",
      globeData: "地理数据",
      principleAria: "运营原则",
      principle: "观察 → 发现 → 决策 → 行动。",
      noBuild: "没有信号就不构建。",
      accountability: "人类问责始终是必需的。",
      methodKicker: "方法",
      methodTitle: "先分离，再解释。",
      methodLead: "五个阶段构成一套运营纪律。每个阶段都限制下一阶段可以作出的声明。",
      methodReality: "现实",
      methodRealityCopy: "直接观察到的内容。",
      methodEvidence: "证据",
      methodEvidenceCopy: "支持或反驳某项声明的内容。",
      methodInference: "推断",
      methodInferenceCopy: "根据证据谨慎得出的结论。",
      methodNarrative: "叙事",
      methodNarrativeCopy: "可能放大、简化或扭曲的内容。",
      methodSignal: "运营信号",
      methodSignalCopy: "与人工审核有关的运营信息。",
      portfolioKicker: "由仓库支撑的项目组合",
      portfolioTitle: "当前实际存在的内容。",
      portfolioLead: "每个界面都标有状态和直接证据路径。已实现内容与原型、受控服务以及仅存在于 RFC 中的计划保持分离。",
      cardCoreLabel: "01 / CORE",
      cardSimulatorLabel: "02 / 模拟器",
      cardSemanticLabel: "03 / SEMANTIC ENGINE",
      cardOperatorLabel: "04 / OPERATOR",
      cardIntakeLabel: "05 / URL 获取",
      cardResearchLabel: "06 / 研究",
      cardGovernanceLabel: "07 / 治理",
      statusActive: "活跃方法论",
      statusSimulator: "可运行的确定性原型",
      statusSemantic: "早期实现",
      statusBrowser: "浏览器原型",
      statusIntake: "已有实现 · 部署未经核实",
      statusResearch: "实验性工具",
      statusGovernance: "活跃 · 已正式批准的协议",
      coreCopy: "v1 规范方法论、运营流程、场景和元学习。西班牙语是 v1 的权威版本；英语是对等性参考。",
      viewCanonical: "规范 Core",
      viewStatus: "状态政策",
      simulatorTitle: "确定性场景模拟器",
      simulatorCopy: "严格的 JSON Schema 验证、带 seed 的分轮执行、确定性 JSON 输出、冻结基准和结构漂移诊断。",
      runScenario: "运行场景",
      runtimeContract: "运行时合约",
      semanticTitle: "合约与 CLI",
      semanticCopy: "最小化的声明、证据、结果、审计日志和决策轨迹合约，以及用于验证并保存结构化案例记录的本地 CLI。它不会评估声明，也不会为声明评分。",
      inspectEngine: "检查引擎",
      cliContract: "CLI 合约",
      operatorCopy: "本地优先的 PWA，用于结构化录入、可编辑案例记录、确定性浏览器分流、本地存储、可读分享、JSON 和结果呈现。",
      operatorDisclosure: "此语言包翻译项目组合中的说明，不翻译 Operator 界面。Operator 仅在浏览器中执行确定性分流，不会运行 Semantic Engine。未经核实的来源信息仍然未经核实。",
      inspectSource: "检查源代码",
      intakeTitle: "受控 URL 获取",
      intakeCopy: "仓库代码和测试定义了有边界的 URL 内容获取。仅凭 GitHub 无法证明公共端点已经部署或可用。获取的文本不是经过核实的证据。",
      inspectIntake: "检查获取源代码",
      intakeTests: "检查测试",
      researchTitle: "场景与叙事研究",
      researchCopy: "实验性场景生成、变异扫描、边界搜索、场景遥测、叙事一致性检查，以及标注来源的研究数据集。",
      labState: "实验室状态",
      researchTools: "研究工具",
      governanceTitle: "Governance Intelligence",
      governanceCopy: "在人工问责下，用于分离声明、证据、推断、不确定性、叙事放大和运营相关性的版本化协议。",
      readProtocol: "阅读协议",
      protectionMatrix: "保护矩阵",
      truthNote: "公开 Operator 在浏览器中生成分流草稿。最小化 Python Semantic Engine CLI 在本地运行。受控 URL 获取在仓库中有代码和测试，但 GitHub 并未确认存在有效部署。获取不等于核实。",
      labsKicker: "官方孵化空间",
      labsLead: "Labs 是 HUB_Optimus 项目组合的一部分：这是一个受治理的实验空间，实验在具备进入 Core 或产品界面的资格之前在此开展。",
      openLabs: "打开 HUB-Optimus Labs",
      checkedOn: "仓库检查日期：2026 年 7 月 28 日",
      labsEmpty: "仓库存在 · 没有已发布构件",
      labsTruth: "该仓库是官方仓库，目前为空。网站不会把尚未发布的引擎、数据集、部署或安全能力归于该仓库。",
      labsRuleOne: "实验明确保持为非规范内容。",
      labsRuleTwo: "升级需要证据、测试和经过审核的 PR。",
      labsRuleThree: "Core 仍然具有权威性。",
      boundariesKicker: "架构与权限",
      boundariesTitle: "一个事实依据，明确的执行边界。",
      boundariesLead: "GitHub 保存项目的权威状态。公开展示、本地工具和未来的私有部署可以使用这一事实依据，但不能重新定义它。",
      boundaryTableAria: "能力边界",
      layer: "层",
      state: "状态",
      authority: "权限",
      layerGithub: "GitHub 仓库",
      stateVersioned: "版本化 / 已审核",
      authorityCanonical: "项目事实依据来源",
      layerPages: "公开项目组合",
      stateStatic: "静态 GitHub Pages",
      authorityNone: "仅用于展示",
      stateLocal: "浏览器本地 / 受控交接",
      authorityAdvisory: "建议性输出",
      layerIntake: "受控 URL 获取",
      stateRepository: "仓库中有代码和测试",
      authorityRetrieval: "仅获取 · 部署未经核实",
      layerEngine: "Semantic Engine CLI",
      statePrivate: "最小化本地 CLI",
      authorityContract: "受合约约束的草稿",
      layerHuman: "人工审核",
      stateMandatory: "必需",
      authorityAccountability: "最终问责",
      providerKicker: "提供商立场",
      providerTitle: "可移植性源自设计。",
      providerCopy: "GitHub 提供版本控制、审核、CI 和公开静态网站。分析执行保持在本地或受控环境中，并且与提供商无关。托管或模型提供商不会因此获得项目权限或语义权限。",
      platformPolicy: "平台兼容性政策",
      futureKicker: "未来工作",
      futureTitle: "已设计的边界，而非已发布的能力。",
      futureLead: "这些文档为可能的未来工作规定约束。它们不能证明产品、部署、密码控制平面或企业服务已经存在。",
      futureHermesLabel: "RFC / 界面",
      futureEnterpriseLabel: "RFC / 运营模型",
      futurePostQuantumLabel: "RFC / 安全",
      hermesCopy: "未来 PWA 界面的边界。尚未实现。",
      enterpriseCopy: "私有运营边界。没有已发布的公共服务。",
      postQuantumTitle: "后量子控制平面",
      postQuantumCopy: "仅基于标准的规划。没有密码学实现。",
      evidenceKicker: "检查证据",
      evidenceTitle: "仓库的优先级高于展示内容。",
      evidenceCopy: "请直接在 GitHub 上检查代码、合约、测试、issues、pull requests、releases、治理、安全政策和知识产权条款。",
      openRepository: "打开仓库",
      capabilityStatus: "能力状态",
      logoAlt: "仓库认可的 HUB_Optimus 徽标",
      footerPortfolio: "公开项目组合",
      footerBoundary: "无分析跟踪。无广告 Cookie。无隐藏评分。GitHub 仍是权威依据。",
      footerNavAria: "法律与项目链接",
      security: "安全",
      issues: "Issues",
      translationReview: "俄语、希伯来语和简体中文均为机器辅助草稿；需要由具名的合格人工审核人员进行审核。这些界面翻译不具有权威性：v1 规范西班牙语仍是权威版本，并且没有任何宪制性翻译获得批准。",
      translationStatus: "翻译状态",
      termbase: "版本化术语库"
    }
  };

  const supportedLanguages = Object.keys(translations);
  let activeLanguage = "en";
  let globePaused = false;

  function normalizeLanguage(language) {
    const value = String(language || "").trim();
    if (supportedLanguages.includes(value)) return value;

    const normalized = value.toLowerCase().replace(/_/g, "-");
    if (
      normalized === "zh-hans"
      || normalized.startsWith("zh-hans-")
      || normalized === "zh-cn"
      || normalized.startsWith("zh-cn-")
      || normalized === "zh-sg"
      || normalized.startsWith("zh-sg-")
    ) {
      return "zh-Hans";
    }
    if (normalized === "zh" || normalized.startsWith("zh-")) return "en";

    const baseLanguage = normalized.split("-")[0];
    return supportedLanguages.includes(baseLanguage) ? baseLanguage : "en";
  }

  function chooseInitialLanguage() {
    let saved = "";
    try {
      saved = window.localStorage.getItem("hub_optimus_language") || "";
    } catch {
      saved = "";
    }

    if (supportedLanguages.includes(saved)) return saved;
    return normalizeLanguage(window.navigator.language || "en");
  }

  function updateMotionButton() {
    const button = document.getElementById("globe-motion");
    if (!button) return;
    const dictionary = translations[activeLanguage];
    button.textContent = globePaused ? dictionary.resumeGlobe : dictionary.pauseGlobe;
    button.setAttribute("aria-pressed", String(globePaused));
  }

  function applyLanguage(language) {
    const nextLanguage = supportedLanguages.includes(language) ? language : "en";
    const dictionary = translations[nextLanguage];
    activeLanguage = nextLanguage;

    document.documentElement.lang = nextLanguage;
    document.documentElement.dir = nextLanguage === "he" ? "rtl" : "ltr";
    document.title = dictionary.title;

    const description = document.querySelector('meta[name="description"]');
    const ogTitle = document.querySelector('meta[property="og:title"]');
    const ogDescription = document.querySelector('meta[property="og:description"]');
    if (description) description.setAttribute("content", dictionary.description);
    if (ogTitle) ogTitle.setAttribute("content", dictionary.title);
    if (ogDescription) ogDescription.setAttribute("content", dictionary.sequence);

    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (Object.prototype.hasOwnProperty.call(dictionary, key)) {
        node.textContent = dictionary[key];
      }
    });

    document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
      const key = node.getAttribute("data-i18n-aria");
      if (Object.prototype.hasOwnProperty.call(dictionary, key)) {
        node.setAttribute("aria-label", dictionary[key]);
      }
    });

    document.querySelectorAll("[data-i18n-alt]").forEach((node) => {
      const key = node.getAttribute("data-i18n-alt");
      if (Object.prototype.hasOwnProperty.call(dictionary, key)) {
        node.setAttribute("alt", dictionary[key]);
      }
    });

    document.querySelectorAll("[data-language]").forEach((button) => {
      const selected = button.getAttribute("data-language") === nextLanguage;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });

    try {
      window.localStorage.setItem("hub_optimus_language", nextLanguage);
    } catch {
      // Language switching remains functional when storage is unavailable.
    }

    updateMotionButton();
  }

  document.querySelectorAll("[data-language]").forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.getAttribute("data-language")));
  });

  applyLanguage(chooseInitialLanguage());

  const canvas = document.getElementById("world-globe");
  const motionButton = document.getElementById("globe-motion");
  if (!canvas || !motionButton) return;

  function disableGlobeInteraction() {
    canvas.classList.remove("is-ready");
    canvas.setAttribute("aria-hidden", "true");
    canvas.removeAttribute("tabindex");
    canvas.hidden = true;
    if (document.activeElement === canvas) canvas.blur();
    motionButton.hidden = true;
  }

  const context = canvas.getContext("2d", { alpha: true });
  if (!context) {
    disableGlobeInteraction();
    return;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  globePaused = reduceMotion.matches;
  updateMotionButton();

  const DEG = Math.PI / 180;
  const state = {
    rings: [],
    rotation: -8,
    tilt: -11,
    width: 0,
    height: 0,
    radius: 0,
    centerX: 0,
    centerY: 0,
    dragging: false,
    pointerId: null,
    lastX: 0,
    lastY: 0,
    lastFrame: 0,
    ready: false
  };

  const illustrativePoints = [
    [2.8457, 41.6999],
    [4.3517, 50.8503],
    [13.405, 52.52],
    [6.1432, 46.2044]
  ];

  const routePairs = [
    [illustrativePoints[0], illustrativePoints[1]],
    [illustrativePoints[0], illustrativePoints[2]],
    [illustrativePoints[1], illustrativePoints[3]]
  ];

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    state.width = Math.max(1, rect.width);
    state.height = Math.max(1, rect.height);
    state.radius = Math.min(state.width, state.height) * 0.38;
    state.centerX = state.width * 0.5;
    state.centerY = state.height * 0.51;
    canvas.width = Math.round(state.width * ratio);
    canvas.height = Math.round(state.height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function spherePoint(longitude, latitude) {
    const lambda = (longitude + state.rotation) * DEG;
    const phi = latitude * DEG;
    const tilt = state.tilt * DEG;
    const cosPhi = Math.cos(phi);
    const x = cosPhi * Math.sin(lambda);
    const y = Math.sin(phi);
    const z = cosPhi * Math.cos(lambda);
    const tiltedY = y * Math.cos(tilt) - z * Math.sin(tilt);
    const tiltedZ = y * Math.sin(tilt) + z * Math.cos(tilt);

    return {
      x: state.centerX + state.radius * x,
      y: state.centerY - state.radius * tiltedY,
      z: tiltedZ
    };
  }

  function horizonPoint(a, b) {
    const denominator = a.z - b.z;
    const amount = Math.abs(denominator) < 1e-9 ? 0.5 : a.z / denominator;
    return {
      x: a.x + (b.x - a.x) * amount,
      y: a.y + (b.y - a.y) * amount,
      z: 0
    };
  }

  function strokeClippedLine(coordinates, closePath = false) {
    if (!coordinates || coordinates.length < 2) return;
    const points = coordinates.map(([longitude, latitude]) => spherePoint(longitude, latitude));
    if (closePath) points.push(points[0]);
    let drawing = false;

    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      const previousVisible = previous.z >= 0;
      const currentVisible = current.z >= 0;

      if (previousVisible && currentVisible) {
        if (!drawing) context.moveTo(previous.x, previous.y);
        context.lineTo(current.x, current.y);
        drawing = true;
      } else if (previousVisible && !currentVisible) {
        const horizon = horizonPoint(previous, current);
        if (!drawing) context.moveTo(previous.x, previous.y);
        context.lineTo(horizon.x, horizon.y);
        drawing = false;
      } else if (!previousVisible && currentVisible) {
        const horizon = horizonPoint(previous, current);
        context.moveTo(horizon.x, horizon.y);
        context.lineTo(current.x, current.y);
        drawing = true;
      } else {
        drawing = false;
      }
    }
  }

  function drawGraticule() {
    context.save();
    context.beginPath();
    context.strokeStyle = "rgba(131, 186, 242, 0.15)";
    context.lineWidth = 0.7;

    for (let latitude = -60; latitude <= 60; latitude += 30) {
      const line = [];
      for (let longitude = -180; longitude <= 180; longitude += 3) {
        line.push([longitude, latitude]);
      }
      strokeClippedLine(line);
    }

    for (let longitude = -150; longitude <= 180; longitude += 30) {
      const line = [];
      for (let latitude = -90; latitude <= 90; latitude += 3) {
        line.push([longitude, latitude]);
      }
      strokeClippedLine(line);
    }

    context.stroke();
    context.restore();
  }

  function drawLand() {
    context.save();
    context.beginPath();
    context.strokeStyle = "rgba(234, 231, 220, 0.68)";
    context.lineWidth = Math.max(0.75, state.radius / 360);
    state.rings.forEach((ring) => strokeClippedLine(ring, true));
    context.stroke();
    context.restore();
  }

  function vectorFromCoordinates([longitude, latitude]) {
    const lambda = longitude * DEG;
    const phi = latitude * DEG;
    const cosPhi = Math.cos(phi);
    return [cosPhi * Math.cos(lambda), cosPhi * Math.sin(lambda), Math.sin(phi)];
  }

  function coordinatesFromVector([x, y, z]) {
    return [Math.atan2(y, x) / DEG, Math.atan2(z, Math.hypot(x, y)) / DEG];
  }

  function greatCircle(start, end, segments = 72) {
    const a = vectorFromCoordinates(start);
    const b = vectorFromCoordinates(end);
    const dot = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
    const omega = Math.acos(dot);
    const sinOmega = Math.sin(omega);
    const points = [];

    for (let index = 0; index <= segments; index += 1) {
      const amount = index / segments;
      if (Math.abs(sinOmega) < 1e-8) {
        points.push([
          start[0] + (end[0] - start[0]) * amount,
          start[1] + (end[1] - start[1]) * amount
        ]);
        continue;
      }

      const fromWeight = Math.sin((1 - amount) * omega) / sinOmega;
      const toWeight = Math.sin(amount * omega) / sinOmega;
      points.push(coordinatesFromVector([
        a[0] * fromWeight + b[0] * toWeight,
        a[1] * fromWeight + b[1] * toWeight,
        a[2] * fromWeight + b[2] * toWeight
      ]));
    }

    return points;
  }

  function drawRoutes() {
    context.save();
    context.beginPath();
    context.strokeStyle = "rgba(214, 164, 79, 0.7)";
    context.lineWidth = Math.max(1, state.radius / 230);
    context.setLineDash([5, 7]);
    routePairs.forEach(([start, end]) => {
      strokeClippedLine(greatCircle(start, end));
    });
    context.stroke();
    context.setLineDash([]);

    illustrativePoints.forEach(([longitude, latitude]) => {
      const projected = spherePoint(longitude, latitude);
      if (projected.z < 0) return;
      const alpha = 0.45 + projected.z * 0.55;
      context.beginPath();
      context.arc(projected.x, projected.y, 3.2, 0, Math.PI * 2);
      context.fillStyle = `rgba(214, 164, 79, ${alpha})`;
      context.fill();
      context.beginPath();
      context.arc(projected.x, projected.y, 8.5, 0, Math.PI * 2);
      context.strokeStyle = `rgba(214, 164, 79, ${alpha * 0.48})`;
      context.lineWidth = 1;
      context.stroke();
    });

    context.restore();
  }

  function drawGlobe() {
    context.clearRect(0, 0, state.width, state.height);
    const gradient = context.createRadialGradient(
      state.centerX - state.radius * 0.25,
      state.centerY - state.radius * 0.3,
      state.radius * 0.08,
      state.centerX,
      state.centerY,
      state.radius
    );
    gradient.addColorStop(0, "rgba(23, 104, 196, 0.26)");
    gradient.addColorStop(0.52, "rgba(11, 61, 145, 0.12)");
    gradient.addColorStop(1, "rgba(3, 10, 18, 0.82)");

    context.save();
    context.beginPath();
    context.arc(state.centerX, state.centerY, state.radius, 0, Math.PI * 2);
    context.fillStyle = gradient;
    context.fill();
    context.clip();
    drawGraticule();
    drawLand();
    drawRoutes();
    context.restore();

    context.beginPath();
    context.arc(state.centerX, state.centerY, state.radius, 0, Math.PI * 2);
    context.strokeStyle = "rgba(214, 164, 79, 0.44)";
    context.lineWidth = 1.25;
    context.stroke();

    const atmosphere = context.createRadialGradient(
      state.centerX,
      state.centerY,
      state.radius * 0.92,
      state.centerX,
      state.centerY,
      state.radius * 1.08
    );
    atmosphere.addColorStop(0, "rgba(23, 104, 196, 0)");
    atmosphere.addColorStop(1, "rgba(23, 104, 196, 0.16)");
    context.beginPath();
    context.arc(state.centerX, state.centerY, state.radius * 1.08, 0, Math.PI * 2);
    context.fillStyle = atmosphere;
    context.fill();
  }

  function collectRings(geometry) {
    if (!geometry) return [];
    if (geometry.type === "Polygon") return geometry.coordinates;
    if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
    if (geometry.type === "GeometryCollection") {
      return geometry.geometries.flatMap(collectRings);
    }
    return [];
  }

  function animate(timestamp) {
    if (!state.lastFrame) state.lastFrame = timestamp;
    const elapsed = Math.min(40, timestamp - state.lastFrame);
    state.lastFrame = timestamp;

    if (state.ready && !globePaused && !state.dragging && !document.hidden) {
      state.rotation = (state.rotation + elapsed * 0.0026) % 360;
      drawGlobe();
    }

    window.requestAnimationFrame(animate);
  }

  motionButton.addEventListener("click", () => {
    globePaused = !globePaused;
    updateMotionButton();
  });

  const handleMotionPreference = (event) => {
    if (event.matches) {
      globePaused = true;
      updateMotionButton();
    }
  };

  if (typeof reduceMotion.addEventListener === "function") {
    reduceMotion.addEventListener("change", handleMotionPreference);
  } else if (typeof reduceMotion.addListener === "function") {
    reduceMotion.addListener(handleMotionPreference);
  }

  canvas.addEventListener("pointerdown", (event) => {
    state.dragging = true;
    state.pointerId = event.pointerId;
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!state.dragging || state.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - state.lastX;
    const deltaY = event.clientY - state.lastY;
    state.rotation += deltaX * 0.28;
    state.tilt = Math.max(-48, Math.min(48, state.tilt - deltaY * 0.18));
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    if (state.ready) drawGlobe();
  });

  function stopDragging(event) {
    if (state.pointerId !== event.pointerId) return;
    state.dragging = false;
    state.pointerId = null;
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  }

  canvas.addEventListener("pointerup", stopDragging);
  canvas.addEventListener("pointercancel", stopDragging);

  canvas.addEventListener("keydown", (event) => {
    const actions = {
      ArrowLeft: () => { state.rotation -= 5; },
      ArrowRight: () => { state.rotation += 5; },
      ArrowUp: () => { state.tilt = Math.min(48, state.tilt + 4); },
      ArrowDown: () => { state.tilt = Math.max(-48, state.tilt - 4); }
    };
    if (!actions[event.key]) return;
    event.preventDefault();
    actions[event.key]();
    drawGlobe();
  });

  window.addEventListener("resize", () => {
    resizeCanvas();
    if (state.ready) drawGlobe();
  });

  resizeCanvas();
  window.requestAnimationFrame(animate);

  const geographicSource = canvas.dataset.geoSource;
  if (!geographicSource) {
    disableGlobeInteraction();
    return;
  }

  fetch(geographicSource, { credentials: "same-origin" })
    .then((response) => {
      if (!response.ok) throw new Error(`Geographic data returned HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      const geometries = data.type === "FeatureCollection"
        ? data.features.map((feature) => feature.geometry)
        : [data.geometry || data];
      state.rings = geometries.flatMap(collectRings);
      if (!state.rings.length) throw new Error("Geographic data contains no polygon rings");
      state.ready = true;
      canvas.classList.add("is-ready");
      drawGlobe();
    })
    .catch(() => {
      disableGlobeInteraction();
    });
})();
