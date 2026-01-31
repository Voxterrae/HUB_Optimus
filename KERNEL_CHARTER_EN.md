# HUB_Optimus Core Charter

This charter defines the immutable rules governing the simulation core of **HUB_Optimus**.  Its purpose is to transform the project's philosophical principles into explicit technical constraints.  Any component integrated into the core (`Simulator`, `Scenario` or `Actor`) must respect these rules in order to preserve the project's mission: to promote systemic stability and integrity in diplomatic contexts.

## Foundational principles

The project is guided by five core principles that serve as its ethical and technical compass:

1. **Stability over optics** – mid‑ and long‑term systemic stability takes precedence over short‑term wins.
2. **Integrity first** – influence and authority are earned through ethical coherence, not by position, credentials or temporary power.
3. **Evaluation over narrative** – outcomes are valued according to structural criteria (incentives, verification, sequencing) rather than rhetoric.
4. **Prevention over reaction** – early and discreet mediation is preferred over public escalation and reactive behaviour.
5. **No blame** – errors and failures are treated as systemic symptoms, not as personal shortcomings.

## Technical constraints of the core

To translate these principles into concrete software behaviour, the core incorporates the following rules:

### 1. Capability ≠ Permission

The core can simulate negotiation dynamics and evaluate their consequences, but **it is not allowed to recommend actions that seek to dominate, exploit or manipulate other actors**.  Computational power should improve the clarity of diagnosis, not the aggressiveness of strategies.

* **Prohibition of exploitation** – any policy that optimises individual benefit at the expense of the deterioration of other actors is automatically marked as a *high‑risk outcome* and discouraged.
* **Tactical neutrality** – the core does not generate tactical instructions for real actors; it only describes consequences, risks and alternative scenarios.

### 2. Focus on multi‑actor stability

Utility functions and success criteria in the simulator are defined in terms of **joint stability** rather than maximisation of individual payoffs.  Evaluations must consider:

* Medium and long‑term coherence of agreements.
* Balance of incentives among actors.
* Viability of verification and compliance.

### 3. Transparency and auditability

All internal decisions of the core must be traceable.  This implies:

* **Action history** – each negotiation round records offers, concessions and justifications.
* **Explicit criteria** – the criteria that lead to declaring success or failure of a scenario are clearly exposed in the reports.
* **No opaque results** – the core does not return encrypted or inscrutable results; users can review why a particular diagnosis was reached.

### 4. Integration isolation

The core is designed to be extensible through external *plugins* (for example, negotiation libraries such as NegMAS or multi‑agent orchestrators such as CrewAI).  However, such integrations **can never modify the base rules**.  They must meet the following requirements:

* **Non‑invasiveness** – extensions are loaded as secondary modules and communicate with the core through well‑defined interfaces.
* **Charter compliance** – any integrated strategy or algorithm must adhere to the prohibition on exploitation and the focus on stability.

### 5. Information security

The core may incorporate encryption mechanisms (for example, MLKEM/Kyber) to protect the confidentiality of proposals and results during the simulation.  Nevertheless:

* **Encryption applies to the channel** – not to the final content of the reports.
* **Results are always auditable** – encryption is not used to hide evaluations or recommendations.

### 6. Didactic mode and functional mode

The core distinguishes between two modes of use:

* **Didactic mode** – transparent and oriented towards training.  It displays the full history of rounds, integrity metrics and explanations.  Recommended for research and teaching.
* **Functional mode** (future enterprise fork) – maintains the same logic but automates the execution of multiple scenarios and offers summarised reports.  Under no circumstances does it enable control of external systems or generate actionable strategies in real time.

## Governance and maintenance

Compliance with this charter must be verified through automated tests and code reviews.  Contributions to the core should:

* Include **unit tests** demonstrating that new functionality respects these rules.
* Clearly document any changes to utility functions or to the definition of stability.
* Be reviewed by at least two collaborators familiar with the project's mission.

## Conclusion

This charter transforms the ethical principles of HUB_Optimus into binding technical constraints.  It ensures that as the project grows and new tools are incorporated, **the original purpose—promoting integrative diplomacy and stability—will not be perverted**.  Any expansion of the core must begin by evaluating its compliance with this charter.