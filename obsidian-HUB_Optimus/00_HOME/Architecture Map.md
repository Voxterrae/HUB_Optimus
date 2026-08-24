---
type: "architecture-map"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "architecture"
  - "map"
  - "navigation"
---

# Architecture Map

## Master Map

```mermaid
flowchart TB
    subgraph Human["Human and governance plane"]
      Owner["Owner / reviewer"]
      Gov["Governance Guardrails"]
      Method["Canonical v1 Methodology"]
    end

    subgraph Frontend["Frontend plane"]
      Site["Public Static Site"]
      Operator["Operator PWA"]
      Learn["Operator Learning Store"]
    end

    subgraph Runtime["Executable runtime plane"]
      Loader["Scenario Contract and Loader"]
      Sim["Round-based Simulator"]
      API["Local HTTP API"]
      Intake["Controlled URL Intake"]
      Core["EC2 Core Runner"]
      Semantic["Semantic Engine CLI"]
    end

    subgraph Data["Data and evidence plane"]
      Scenario["Scenario JSON"]
      Result["SimulationResult"]
      Case["CaseInput"]
      Analysis["AnalysisResult"]
      Runs["RUN_STATE / run outputs"]
    end

    subgraph Delivery["Delivery plane"]
      Repo["GitHub Repository"]
      CI["Tests and Quality Gates"]
      Pages["GitHub Pages Pipeline"]
      Host["Managed Linux/EC2 host"]
    end

    Owner --> Operator
    Owner --> Scenario
    Method -. "guides humans" .-> Owner
    Gov -. "constrains reviewed change" .-> Repo
    Site --> Operator
    Operator --> Learn
    Scenario --> Loader --> Sim --> Result
    Operator -. "manual contract handoff" .-> Case
    Case --> API --> Core --> Semantic --> Analysis
    API --> Intake
    Core --> Runs
    Repo --> CI
    Repo --> Pages --> Site
    Repo -. "explicit reviewed ref" .-> Host
    Host -. "runtime state unknown" .-> API
```

## Project

- [[Project Overview]]
- [[Capabilities]]
- [[Limitations]]
- [[Glossary]]

## Frontend

- [[Frontend Architecture]]
- [[Public Static Site]]
- [[Operator PWA]]
- [[Operator Learning Store]]

## Backend

- [[Backend Architecture]]
- [[Scenario Contract and Loader]]
- [[Round-based Simulator]]
- [[Semantic Engine Contracts and CLI]]
- [[Controlled URL Intake]]
- [[Local HTTP API]]

## APIs

- [[Interface Catalogue]]
- [[GET health]]
- [[GET status]]
- [[POST intake url]]
- [[POST analyze]]
- [[Scenario CLI]]
- [[Semantic Engine CLI]]
- [[hub-core CLI]]

## Components

- [[Architecture Overview]]
- [[System Context]]
- [[Runtime Architecture]]
- [[Architecture Data Flow]]
- [[Dependency Graph]]

## Data

- [[Data Architecture]]
- [[Scenario Data Model]]
- [[Semantic Data Model]]
- [[Operator Learning Data]]
- [[Operational Records]]

## Infrastructure

- [[Infrastructure Boundary]]
- [[EC2 Release Operations]]
- [[EC2 Core Runner and Run Registry]]
- [[GitHub Pages Pipeline]]

## Deployment

- [[Deployment Architecture]]
- [[Operations Guide]]

## Security

- [[Security Boundaries]]
- [[Risk Register]]

## Dependencies

- [[Dependencies]]

## Source

- [[Source Map]]
- [[Evidence Index]]
- [[Repository Analysis]]
