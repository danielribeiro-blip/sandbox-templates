# Legal AI Evaluation Rubric — Public Sample

A compact practitioner rubric for reviewing legal-AI outputs. This sample is intentionally generic and does not contain client-confidential material.

## Scoring scale

Each dimension is scored from **0 to 4**:

- **0 — Failed:** materially unusable or unsafe.
- **1 — Major defects:** substantial correction required.
- **2 — Mixed:** partially useful but unreliable without expert repair.
- **3 — Strong:** minor corrections only.
- **4 — Production-grade for the stated task:** accurate, complete enough, traceable and appropriately qualified.

## Evaluation dimensions

### 1. Issue recognition
Does the output identify the legal and procedural questions that actually control the task?

Common failure modes:
- answers a neighboring but different question;
- misses a dispositive procedural issue;
- collapses multiple claims or defenses into one;
- assumes a remedy without establishing its prerequisites.

### 2. Factual fidelity
Does every consequential factual proposition remain anchored to the supplied record?

Common failure modes:
- invents dates, parties, amounts, events or procedural posture;
- silently resolves disputed facts;
- treats an allegation as an established fact;
- overlooks contradictory evidence.

### 3. Source and citation integrity
Are authorities real, current enough for the task, jurisdictionally relevant and accurately characterized?

Common failure modes:
- nonexistent or mismatched citations;
- authority does not support the proposition stated;
- persuasive authority presented as binding;
- obsolete rule applied without qualification.

### 4. Rule formulation
Is the controlling rule stated with the right elements, exceptions and burden structure?

Common failure modes:
- oversimplified legal test;
- omission of an exception or threshold requirement;
- incorrect allocation of burden;
- mixing substantive and procedural standards.

### 5. Application quality
Does the reasoning connect the established facts to the legal rule instead of merely repeating both?

Common failure modes:
- conclusion appears without intermediate reasoning;
- analogy is asserted but not tested;
- adverse facts are ignored;
- decisive uncertainty is concealed.

### 6. Procedural posture
Does the answer respect what can actually be decided, requested or proved at the current stage?

Common failure modes:
- seeks relief unavailable in the posture;
- relies on evidence not yet admitted or established;
- confuses interlocutory and final effects;
- overlooks pending appeals, preclusion or jurisdictional limits.

### 7. Counterargument resilience
Does the output identify and answer the strongest plausible adverse reading?

Common failure modes:
- straw-man opposition;
- ignores obvious contrary authority or evidence;
- overstates certainty where the record is contested;
- fails to distinguish a facially similar precedent.

### 8. Remedy alignment
Does the requested result follow from the facts, rules and procedural stage actually analyzed?

Common failure modes:
- remedy exceeds the demonstrated entitlement;
- reasoning supports one conclusion while the requested relief assumes another;
- no fallback or alternative relief where uncertainty is material.

### 9. Epistemic discipline
Does the output distinguish what is confirmed, inferred, pending or disputed?

A useful reviewer can label consequential propositions as:
- **CONFIRMED** — directly supported by a qualified source;
- **PENDING** — depends on a future event or unavailable evidence;
- **CONTROVERTED** — materially disputed;
- **INFERRED** — reasoned conclusion not directly stated by a source.

### 10. Reviewer usability
Can a lawyer quickly verify why the answer reached its conclusion?

Signals of a strong output:
- source-to-claim traceability;
- concise issue structure;
- explicit uncertainty;
- precise correction points;
- no unnecessary confidence inflation.

## Suggested pass rule

For high-stakes legal use, a single aggregate score is not enough. A practical pass gate can require:

1. no score below **3** for factual fidelity, citation integrity, procedural posture or epistemic discipline;
2. no unsupported high-impact factual proposition;
3. no nonexistent authority;
4. no unresolved contradiction hidden by the final conclusion;
5. a human reviewer explicitly approving the final external legal act.

## Example reviewer output

**Overall:** 26/40 — not ready for external use.

**Material defects:**
1. The answer treats a disputed factual premise as established.
2. One cited authority is relevant to the topic but does not support the proposition attributed to it.
3. The requested remedy assumes a procedural consequence not demonstrated by the record.

**Repair path:**
- relabel the disputed proposition;
- replace or narrow the citation-dependent statement;
- rewrite the remedy section to match the procedural posture;
- re-score only the affected dimensions after correction.

---

This rubric is a public methodology sample. Project-specific evaluation should be adapted to the governing jurisdiction, task, source set, confidentiality requirements and risk profile.
