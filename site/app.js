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
      issues: "Issues"
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
      issues: "Issues"
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
      issues: "Issues"
    }
  };

  const supportedLanguages = Object.keys(translations);
  let activeLanguage = "en";
  let globePaused = false;

  function chooseInitialLanguage() {
    let saved = "";
    try {
      saved = window.localStorage.getItem("hub_optimus_language") || "";
    } catch {
      saved = "";
    }

    if (supportedLanguages.includes(saved)) return saved;
    const browserLanguage = (window.navigator.language || "en").slice(0, 2).toLowerCase();
    return supportedLanguages.includes(browserLanguage) ? browserLanguage : "en";
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

  const context = canvas.getContext("2d", { alpha: true });
  if (!context) return;

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
    canvas.setAttribute("aria-hidden", "true");
    motionButton.hidden = true;
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
      canvas.setAttribute("aria-hidden", "true");
      motionButton.hidden = true;
    });
})();
