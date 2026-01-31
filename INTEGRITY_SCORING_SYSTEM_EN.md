# Integrity Scoring System

This document describes a quantitative evaluation scheme for measuring the **integrity** of proposals and processes within scenarios simulated by HUB_Optimus.  Its goal is to provide a transparent metric that reflects how aligned an action or agreement is with the project's principles.

## Motivation

Integrity is a broad concept encompassing honesty, ethical coherence and sustainability.  For the simulation core to make data‑driven decisions rather than relying on subjective perceptions, we propose an **integrity scoring system** that breaks down integrity into several assessable components.

## Dimensions of integrity

The system is based on five main dimensions.  Each is scored in the range 0 to 1, where 0 represents the absence of the quality and 1 its maximum fulfilment.

1. **Fairness (EQ)** – Evaluates whether the proposal distributes benefits and costs fairly among the actors.  Elements such as reciprocity and the absence of disproportionate advantages are valued.
2. **Transparency (TR)** – Measures the degree to which the actions, incentives and conditions of a proposal are visible and comprehensible to all parties.
3. **Sustainability (SO)** – Captures an agreement’s ability to remain stable over the medium and long term without hidden incentives that erode it.
4. **Alignment of incentives (AI)** – Checks whether the actors’ incentives are aligned with overall stability and do not encourage opportunistic deviations.
5. **Verifiability (VE)** – Indicates how easily the agreed conditions can be verified and the existence of accountability mechanisms.

Each dimension can be broken down into specific sub‑criteria depending on the scenario (for example, in diplomatic negotiations the verifiability may include neutral observers and sanction mechanisms).

## Calculation formula

We define the **Integrity Index (II)** as a weighted mean of the five dimensions:

\[
II = w_{EQ} \cdot EQ + w_{TR} \cdot TR + w_{SO} \cdot SO + w_{AI} \cdot AI + w_{VE} \cdot VE
\]

where \(w_{EQ}, w_{TR}, w_{SO}, w_{AI}, w_{VE}\) are the weights assigned to each dimension.  A uniform weight (0.2 each) is suggested by default, but it can be adapted according to the priorities of a specific scenario.

The weights must satisfy:

\[
\sum_{i=1}^{5} w_i = 1\quad\text{and}\quad w_i \ge 0
\]

## Classification of results

To facilitate interpretation, we propose three qualitative categories based on the Integrity Index:

| II interval | Category        | Description                                                                                                                                                     |
|------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0 – 0.49   | **Low integrity**  | The proposal lacks fairness, transparency or verifiability.  It is considered unacceptable within the context of HUB_Optimus.                               |
| 0.50 – 0.79| **Medium integrity**| It meets several criteria, but has deficiencies that could compromise long‑term stability.  It requires revision and adjustments.                              |
| 0.80 – 1.00| **High integrity**  | The proposal is solidly aligned with HUB_Optimus principles.  It is fair, transparent, sustainable and verifiable.                                            |

## Evaluation procedure

1. **Define sub‑criteria** – For each dimension, define sub‑criteria tailored to the specific scenario (e.g. in a cease‑fire, sustainability may include international oversight mechanisms and realistic troop withdrawal timelines).
2. **Assign scores** – Each sub‑criterion is evaluated on a scale of 0 to 1.  These scores are aggregated to obtain the score for each dimension.
3. **Determine weights** – Agree on the weights \(w_i\) for the dimensions.  Absent specific preferences, use the uniform distribution.
4. **Calculate II** – Apply the formula above to obtain the Integrity Index.
5. **Interpret results** – Classify the proposal according to the corresponding interval and formulate recommendations (e.g. strengthen verifiability or adjust incentives).

## Example application

In a partial cease‑fire scenario between two factions:

* **Fairness (EQ)**: 0.8 (concessions are proportional and fair).
* **Transparency (TR)**: 0.9 (all conditions are documented and shared with a neutral mediator).
* **Sustainability (SO)**: 0.7 (the agreement is viable for six months, but requires a clearer de‑escalation plan for the long term).
* **Alignment of incentives (AI)**: 0.6 (there are incentives to maintain the cease‑fire, but some actors could benefit from minor violations).
* **Verifiability (VE)**: 0.8 (independent observers can confirm compliance).

With uniform weights (0.2 each), the index is:

\[
II = 0.2\times 0.8 + 0.2\times 0.9 + 0.2\times 0.7 + 0.2\times 0.6 + 0.2\times 0.8 = 0.76
\]

According to the table, the scenario would be classified as **Medium integrity**.  It would be recommended to strengthen the alignment of incentives and improve long‑term sustainability to achieve high integrity.

## Integration with the simulation core

The core should calculate the Integrity Index in each round or at the end of the negotiation.  This index should be included in the reports generated by the simulator and serve to:

* Alert users to agreements that appear successful but exhibit low integrity (false positives).
* Compare different policies or strategies within a common framework.
* Guide the improvement of proposals by identifying weak dimensions.

The quantitative evaluation of integrity does not replace human judgement, but provides an objective starting point for decision‑making.