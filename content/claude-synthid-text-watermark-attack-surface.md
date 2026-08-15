Title: When the Output Carries the Signal: Claude, SynthID-Text, and the New Detection Attack Surface
Date: 2026-08-15
Author: Oliver Rivas
Category: Artificial Intelligence
Tags: AI Security, Anthropic, Claude, SynthID, Watermarking, EU AI Act, Adversarial ML
Slug: claude-synthid-text-watermark-attack-surface
Summary: Claude's planned text watermark is embedded through token selection rather than hidden characters. Once enterprises automate on its detector, that provenance feature becomes a security control plane with spoofing, evasion, oracle, key-management, supply-chain, and policy-abuse requirements.

Anthropic's planned watermark for future Claude models is embedded during token selection. There is no invisible Unicode string, metadata field, or marker appended after generation.

The text carries the signal.

Once an enterprise automates on the detector's output, the detector becomes a control plane. A provenance feature now influences access, alerts, investigations, employment decisions, and compliance workflows. It therefore inherits spoofing, evasion, oracle, key-management, supply-chain, and abuse-resistance requirements.

Copying the text does not remove the signal by itself, because the signal lives in the token relationships and there is no separate marker to delete. Detection remains probabilistic, depends on a secret configuration, and says nothing by itself about who generated the text or whether its use was authorized. From a security perspective, three assets must be protected: the watermark configuration, the detector's decision boundary, and the trust that downstream systems place in its result.

The watermark provides useful provenance evidence under controlled conditions. That same detection system carries bypass, forgery, side-channel, supply-chain, and operational-abuse paths. Enterprise teams should model all of them before connecting watermark detection to DLP, insider-risk, compliance, or incident-response workflows.

Anthropic introduced the change to support the EU AI Act's Article 50 transparency requirements and plans to apply it globally at launch. That regulatory context explains why the capability is shipping. It does not justify treating detector output as safe to automate against.

## How the Signal Is Embedded

An LLM generates text one token at a time. At each position, it produces logits representing the relative likelihood of possible next tokens. Sampling controls such as temperature, top-k, and top-p reshape or narrow that candidate set before a token is selected.

Claude will use a version of Google DeepMind's [SynthID-Text](https://www.nature.com/articles/s41586-024-08025-4). Anthropic describes the shared design principle as changing the source of randomness used to choose among plausible words. It has not disclosed Claude's exact tokenizer, key structure, thresholds, or production pipeline.

Public SynthID-Text designs work roughly like this: Google's documentation describes a [logits processor applied after top-k and top-p filtering](https://ai.google.dev/responsible/docs/safeguards/synthid). In the public implementation, a pseudorandom function uses preceding token context and a private watermark configuration to score candidates and adjust their logits before sampling.

```text
[Prompt Context] ──> [LLM Base Logits] ──> [Top-K / Top-P Filter]
                                                    │
[Private Configuration] ──> [Keyed Candidate Scores] ──┼──> [Logit Adjustment] ──> [Sampled Token]
                                                    │
                                             (Signal Embedded)
```

This diagram represents the public SynthID-Text design. Anthropic's production configuration remains undisclosed.

No single token proves anything. In the public design, the detector retokenizes a passage, reconstructs the expected keyed scores across its token sequences, and aggregates the evidence. Longer, higher-entropy passages provide more opportunities to embed a signal. Short answers, facts with one correct completion, proofreading, SQL, source code, and infrastructure templates provide fewer interchangeable choices and therefore less signal.

Google's reference design supports `watermarked`, `not watermarked`, and `uncertain` states, with thresholds calibrated for different false-positive and false-negative rates. The mechanism performs statistical classification, and its output is a calibrated confidence level. It provides likelihood rather than the deterministic guarantee of a cryptographic signature.

Base rates matter as much as the published error rate. A detector with a 0.1 percent false-positive rate sounds precise, yet across ten million scanned documents it produces roughly ten thousand false positives before any adversary intervenes. When genuine Claude-generated content is rare in a corpus, the positive predictive value of a single hit falls sharply, and a majority of positives can be false. Consider a detector with a 95 percent true-positive rate and a 0.1 percent false-positive rate. If 1 percent of a corpus is genuine Claude output, a positive hit carries a positive predictive value near 91 percent. If prevalence drops to 0.1 percent, the same detector's positive predictive value falls below 50 percent, so most positives are wrong even though the error rate never changed. Enterprise deployment must reason about prevalence and scanning volume together with the error rate.

The narrow defensible interpretation is:

> The submitted text contains a statistical signal consistent with Claude having generated or substantially processed some portion of it, subject to detector calibration, passage length and language, input preprocessing, and the chosen threshold.

It does not identify the user, tenant, prompt, time of generation, authorization context, or owner. It cannot separate authorized use from policy violation. Anthropic also says it cannot distinguish "Claude wrote this" from "Claude heavily edited this."

## Threat Model: Assets, Adversaries, and Failure Modes

Two questions matter here. The first is whether a user can remove the watermark. The larger one is which new trust decisions depend on it and how an adversary can manipulate those decisions. The system exposes multiple trust boundaries, and each of them invites a different attack.

| Threat class | Security asset or trust decision | Resulting failure |
| --- | --- | --- |
| Removal | Watermark signal | Meaning-preserving edits erase enough evidence to produce a negative or uncertain result |
| Dilution | Aggregate detector score | Watermarked text mixed with human or unwatermarked text falls below the decision threshold |
| Spoofing | Provider attribution | Unrelated or harmful text is made to appear consistent with Claude generation |
| Oracle probing | Detector decision boundary | Repeated queries converge on low-edit bypasses or manufactured positives |
| Key/config compromise | Watermark configuration | Attackers gain scalable forgery, evasion, or selective watermark corruption |
| Detector supply-chain | Detector code, model, thresholds, or dependencies | Detection is silently weakened, biased, disabled, or manipulated |
| Calibration poisoning | Detector thresholds and any adaptive abuse or allow-block model | Crafted submissions skew tuning or feedback so the detector systematically mislabels a chosen class |
| Policy overreach | Enterprise decision workflow | A probabilistic indicator causes blocking, false accusations, or disciplinary action without corroboration |
| Privacy and retention | Text submitted to the detector | Sensitive content sent to a detection API is exposed, logged, or retained by a third party |

The likely adversaries range from a user running a local rewrite model to an insider with access to inference infrastructure. A mature threat model must also include compromised dependencies, malicious service operators, state actors targeting attribution systems, and external parties who never used Claude but can inject Claude-generated text into an enterprise ingestion path.

## Scrubbing Is an Automation Problem

Copying the output preserves the watermark when the byte sequence is carried verbatim, because the token sequence is the carrier. Copy paths that reflow or convert the text, such as Markdown rendering, PDF extraction, OCR, or Unicode and whitespace normalization, can shift token boundaries and weaken the signal without any deliberate rewrite. Regenerating or perturbing that sequence changes the evidence the detector evaluates.

Low-effort scrubbing paths include:

- Passing the passage through a non-watermarked local model, such as a Llama-family model served through Ollama, with instructions to preserve meaning while changing wording and sentence structure.
- Back-translation or chained translation through a different model.
- Automated synonym replacement, sentence reordering, compression, expansion, or style transfer.
- Character-level changes such as homoglyph substitution, zero-width characters, whitespace insertion, typos, or swaps that alter tokenization.
- Mixing generated passages with human or non-watermarked text to dilute the aggregate score.

Character-level attacks deserve attention because token watermarks depend on tokenization and preceding context. Homoglyphs, zero-width insertions, and other Unicode variations can change several token IDs and disturb keyed scores beyond the visible edit. Google's public documentation recommends an `ngram_len` of 5 as a default, but the precise effect is tokenizer- and configuration-dependent, and Anthropic has not disclosed Claude's values.

Research has found that [homoglyph substitutions can degrade multiple AI-text detectors](https://arxiv.org/abs/2406.11239), including evaluated watermarking methods. A later study found [character-level perturbations more effective than token-level or sentence-level edits](https://arxiv.org/abs/2509.09112) across several watermark schemes under limited-query threat models.

Canonicalizing Unicode and removing zero-width characters should defeat naive versions of these attacks, but normalization must occur at detector ingress before the detector tokenizes the passage. The normalization policy must also be language-aware and consistent with the detector's expected input; aggressive canonicalization can destroy meaningful distinctions in some scripts. Normalization is a necessary input-control layer with clear limits. It does nothing against a semantically equivalent rewrite produced by another model.

Google acknowledges that thorough rewriting and translation can substantially reduce detector confidence. ETH Zurich researchers found that a default SynthID-Text configuration was [comparatively easy to scrub through paraphrasing](https://www.sri.inf.ethz.ch/blog/probingsynthid), reporting greater than 90 percent success in their specific setup. These results do not establish that Anthropic's unreleased configuration has the same parameters or performance. They establish that meaning-preserving transformation is a practical attack class.

The strategic implication is that watermark survival depends on how much control the provider retains over the text's transformation path. Once an untrusted system can regenerate the semantics, token-level provenance becomes fragile.

## The Detector as a Side-Channel Oracle

Anthropic says it will expose a watermark detection API, with implementation details still under development. That interface creates a black-box optimization surface.

Let `D(x)` be the detector's output for text `x`. An attacker wants to find a modified passage `x'` that minimizes the watermark result while keeping semantic similarity and readability above acceptable thresholds:

```text
minimize:    D(x')
subject to:  semantic_similarity(x, x') >= tau
             readability(x') >= rho
             edit_distance(x, x') <= epsilon
```

If the API returns a confidence value, that score becomes a fitness function. The attacker can generate candidate rewrites, retain the changes that reduce confidence, and repeat. Gradient access is unnecessary. Genetic algorithms, evolutionary search, bandit optimization, or reinforcement-learning policies can use the detector's response as feedback.

Recent ACL research demonstrates the shape of this attack. [TSAPA](https://aclanthology.org/2026.findings-acl.459/) formulates watermark removal as a constrained multi-objective optimization problem and uses a genetic algorithm to balance erasure, semantic fidelity, naturalness, and lexical diversity. Other work shows that a lightweight reference detector trained from a limited query budget can guide later perturbations.

A binary endpoint still leaks information. The attacker can mutate a candidate until `D(x')` crosses from `1` to `0`, then minimize the edits while staying on the unwatermarked side of the boundary. A ternary `uncertain` state is safer for downstream interpretation but still exposes boundary information if repeated near-duplicate queries are allowed.

Granular confidence scores reduce the query cost because every response reveals direction as well as outcome. Stable thresholds, anonymous access, high quotas, and token-level explanations would further amplify the side channel.

This section is a threat model for Anthropic's forthcoming API. It describes how such an interface could be attacked, and the actual risk will depend on response granularity, threshold stability, authentication, rate limits, similarity clustering, abuse monitoring, and key segmentation.

Calibration poisoning targets any part of the detection pipeline that adapts from prior inputs rather than the query interface itself. The exposure lives in the adaptive layers. A static vendor detector faces little direct risk, while provider-side threshold tuning, an abuse model, or an enterprise allow-and-block policy that learns from a stream of submissions can be steered. An adversary who seeds crafted text over time can shift the decision boundary, suppress a target class of positives, or manufacture false positives against a chosen source. Any feedback loop that tunes on unauthenticated input becomes part of the attack surface and should be trained only on curated, provenance-bound data.

## Spoofing and Watermark Stealing

Evasion is one attacker goal. Spoofing is its reverse: an adversary may want unrelated text to test positive.

Successful spoofing could associate Claude with fraudulent instructions, disinformation, malware documentation, fabricated evidence, or politically sensitive material. The impact rises if employers, platforms, regulators, or courts treat detector output as authoritative.

At ICML 2024, researchers demonstrated that [black-box watermark stealing](https://proceedings.mlr.press/v235/jovanovic24a.html) could approximately learn watermark behavior through repeated model queries, supporting both spoofing and more effective scrubbing against evaluated schemes. Follow-up work found SynthID-Text harder to spoof than earlier approaches in its experimental setup, but increased query budgets improved attacker performance.

The security objective must therefore include unforgeability alongside detectability and resistance to removal. A detector with a low false-positive rate under benign evaluation can still be unsafe if an adaptive adversary can intentionally manufacture positives.

## Radioactivity: When the Signal Survives Training

A watermark placed at generation time can outlive the text that carried it. Research on watermark radioactivity shows that training a model on watermarked outputs leaves a detectable statistical trace in the resulting model, which then emits weakly watermarked text of its own ([Sander et al., Watermarking Makes Language Models Radioactive](https://arxiv.org/abs/2402.14904)). The signal propagates from teacher to student even when the original training passages are unavailable to the examiner.

This cuts in two directions.

As a provenance tool, radioactivity is useful. A provider that suspects a competitor distilled its model can look for the watermark's imprint in the competitor's outputs and gather evidence of unauthorized training on protected generations. Detection remains feasible at modest watermarked-data fractions, so a distillation attempt does not need to copy a large corpus to become detectable.

As a contamination risk, radioactivity is a problem the whole ecosystem inherits. Claude-watermarked text will spread across the public web, and general-purpose models trained on scraped data will absorb some of it. A model that never had a licensing relationship with Anthropic can therefore become weakly radioactive and produce outputs that a detector might flag. A positive result may then reflect model lineage rather than a person choosing to use Claude for the task under investigation.

Distillation also degrades the signal in ways that are hard to predict. A student model trained through temperature sampling, aggressive filtering, or reinforcement learning may inherit an attenuated, shifted, or partially erased version of the teacher's watermark. The examiner sees a weaker or ambiguous signal without a reliable way to separate deliberate use from inherited contamination.

The evidentiary consequence is direct. A detector hit can indicate several different histories: direct generation, heavy editing of Claude output, retrieval of watermarked source, or training lineage that passed the signal through one or more models. An investigation that treats a positive as "this person used Claude here" ignores every path except the first.

## Attribution in RAG and Agentic Pipelines

Modern systems rarely present a single model's raw output. Retrieval-augmented generation pulls in source documents, agents call tools and other models, memory and summarization compress prior turns, and orchestration layers stitch the pieces together. The final artifact is often a blend of user-authored text, retrieved passages, tool results, and tokens generated by more than one model.

A watermark detector evaluates that blend as one string. A positive result tells you a watermarked span exists somewhere in the artifact's lineage. It does not tell you which stage produced it, which model held the key, or whether the watermarked span was authored, retrieved, or injected.

Several pipeline behaviors make attribution harder:

- Retrieval can insert watermarked Claude text into an output that a different model assembled, so the assembling system reads as Claude-influenced even though Claude never ran in that request.
- Summarization and compression of a watermarked source may preserve, weaken, or destroy the signal depending on how much of the original token sequence survives.
- Memory compaction and multi-turn context let a watermarked span persist across a session and resurface in later outputs, spreading a single generation's signal across many artifacts.
- Agentic systems that call Claude as one tool among many produce outputs where only a fraction of the tokens carry signal, which dilutes the aggregate score and blurs which component was responsible.
- Prompt injection turns this into an attack. An adversary who seeds watermarked text into a retrieval corpus, a tool response, or a scraped page can force a downstream positive on demand, which connects directly to the watermark-pollution problem described later.

For enterprise detection, the practical rule is that a hit describes the composed artifact and cannot single out one actor. Attribution has to account for pipeline topology and custody at each hop: what was retrieved, what each agent generated, which model served each step, and where the text entered the system. Without that lineage, a positive on a RAG or agent output is a statement about the corpus, and it reads as a statement about a person only by accident.

## Key, Seed, and Inference-Pipeline Compromise

Google's public SynthID configuration uses a list of integer keys, an n-gram length, a sampling-table seed, and related parameters. These are not necessarily cryptographic signing keys, but their operational security role is comparable: Google warns that a disclosed configuration may make the watermark trivially reproducible. The analogy is operational rather than cryptographic. A signature is deterministic and publicly verifiable, while a watermark configuration behaves more like a shared secret whose disclosure both breaks detection integrity and enables forgery, though forging a chosen passage may still require model or logit access and a search budget.

Unlike an offline signing key, the watermark configuration must be available in the model-serving path at generation time. That creates practical extraction and manipulation opportunities:

- An insider or compromised workload reads the configuration from process memory, environment variables, mounted files, or an adjacent service.
- CI/CD logs, crash dumps, profiling data, support bundles, or observability payloads capture seed material.
- A privileged container, debug endpoint, sidecar, or node-level agent observes the post-processing layer or modifies it in memory.
- A compromised inference dependency changes the PRNG implementation, disables repeated-context masking, or selectively bypasses watermarking.
- An attacker compromises the detector service and uses its access to recover configuration or submit unmetered adaptive queries.
- A state actor steals historical keys, then forges or disputes attribution for content generated during that key epoch.

The configuration should be governed like high-impact signing material even if the implementation cannot place every token decision behind an HSM call. Minimum controls include workload-identity-based retrieval, envelope encryption, memory-only injection, strict separation between generation and detection services, locked-down debugging, short key epochs, versioned rotation, immutable audit records, and tested compromise recovery.

Rotation also creates an evidentiary requirement. A future detector must know which configuration and threshold apply to a given model generation. If old keys are destroyed, historical verification may become impossible. If they are retained indefinitely, the compromise window expands.

> **Key retention under two models.** Public-key signatures can preserve historical verification through certificates, revocation records, and trusted timestamps after the private signing key is retired. SynthID-style detection stays dependent on secret watermark configurations. Keeping every historical epoch online therefore expands the material that could enable forgery or more efficient evasion if compromised. A safer design keeps only active and recent epochs online and moves older configurations to encrypted, dual-control escrow for isolated historical verification.

## What This Means for Enterprise DevSecOps and Incident Response

Most enterprises will consume watermark results rather than operate the watermark. Their largest risk is turning a probabilistic indicator into a deterministic control.

### Do Not Do This

- Do not block employees or content solely on detector output.
- Do not treat a detector hit as proof of authorship, misconduct, or policy violation.
- Do not expose confidence scores or token-level explanations interactively to untrusted users.
- Do not centralize raw sensitive text in a third-party detector without a data-flow, retention, residency, and access-control review. A detection API often receives the exact text DLP already considers sensitive, which turns detection into a "send suspect data to a third party" pattern unless the contract and controls forbid it.
- Do not assume paraphrasing, translation, summarization, or format conversion preserves the signal.

### DLP and CASB policy

Do not configure DLP, CASB, secure web gateway, email, or source-control controls to block content solely because a watermark detector returns positive. A Claude watermark indicates likely model involvement at some point. It does not show that regulated data was submitted to Claude, that the user violated policy, or that the detected content came from the employee being investigated.

A negative result is also unsafe to rely on, because it does not establish that AI was absent. Constrained outputs such as SQL, shell commands, concise functions, Kubernetes manifests, and IaC templates contain less sampling freedom and may carry a weaker signal. A local rewrite or translation layer may remove what remains. An attacker can even weaponize watermark absence as exculpatory theater: a user or vendor scrubs the content and then claims non-use.

Use watermark detection as enrichment alongside egress telemetry, sanctioned-AI gateway logs, browser and endpoint events, SaaS audit records, data-classification findings, and identity context.

### Watermark pollution and alert denial of service

Any enterprise workflow that automatically escalates watermarked text can be intentionally triggered. An external actor could place Claude-generated text in support tickets, inbound email, pull-request comments, documents, threat-intelligence feeds, scraped webpages, or prompt-injection payloads. A downstream scanner may then create a compliance case or insider-risk alert against the employee or system that merely received or processed it.

This is watermark pollution: attacker-controlled provenance contaminates a trusted decision path. At scale, it becomes an alert-denial-of-service technique that consumes analyst time, blocks ingestion, or forces business processes into manual review.

Controls should bind the detector result to source and custody. Distinguish authored, pasted, received, retrieved, and transformed content. Rate-limit alert creation, correlate duplicate passages, and avoid assigning attribution based solely on where the text was found.

### DFIR and evidentiary handling

In an investigation, preserve the original bytes before normalization or editing. Record a hash of the submitted text, detector and model versions, threshold, result state, timestamp, language, token count, and any preprocessing performed. Retain the `uncertain` result rather than collapsing it into a Boolean field. The result should be reproducible later from the preserved original bytes with the recorded detector configuration; if it cannot be reproduced, its evidentiary value drops sharply.

A positive detection can support the hypothesis that Claude interacted with the content. It does not establish intent, execution context, user identity, policy violation, or chain of custody. Corroboration should come from provider audit logs where available, enterprise proxy or AI gateway records, endpoint telemetry, identity events, document history, and witness context.

Anyone presenting this in a legal or disciplinary setting should expect the same scrutiny applied to other forensic classifiers: known error rates, threshold disclosure, reproducibility, operator bias, peer-reviewed validity, and adversarial robustness. Security teams should prohibit detector scores from appearing as a standalone "AI probability" figure in executive or legal reporting. The wording should state exactly what the detector measured and list the known limitations.

## Strategic Takeaways

For model providers:

1. Treat the detector as a hostile public interface and red-team it with adaptive, near-duplicate queries.
2. Prefer coarse states over raw confidence and never expose token-level contribution scores.
3. Normalize inputs, enforce minimum evidence requirements, authenticate callers, and cluster similar submissions across accounts and networks.
4. Separate generation, detection, and key-management duties; version every key, detector, threshold, and model combination.
5. Measure targeted false-positive and false-negative rates across languages, lengths, code, factual text, human-AI mixtures, and adversarial transformations.
6. Test spoofing and pollution scenarios alongside watermark removal.

For enterprise security teams:

1. Treat watermark detection as low-fidelity provenance metadata, and keep it out of any standalone enforcement path.
2. Keep it out of inline blocking paths until false-positive, false-negative, evasion, and pollution behavior are measured in your environment.
3. Correlate results with identity, egress, endpoint, SaaS, and content-classification telemetry.
4. Update incident-response procedures to preserve detector inputs, versions, thresholds, and uncertainty.
5. Threat-model inbound watermarked content as attacker-controlled data capable of triggering internal controls.
6. Establish human review and an appeal path before using detection in employment, academic, legal, or disciplinary decisions.

## The Signal and the Systems Around It

SynthID-Text is materially stronger than invisible Unicode or removable metadata for plain text. It embeds a probabilistic, content-carried signal during generation and can survive transport and light editing without visible artifacts. Content Credentials such as C2PA offer a different guarantee: explicit, signed provenance that is strong where a format, signing chain, and custody are preserved, and absent once content is retyped or copied as plain text. The two approaches cover different failure modes and are best deployed together.

The reliability of watermarking ends where its threat model ends. Semantic regeneration can erase the token pattern. Adaptive access can turn the detector into an optimization oracle. Configuration compromise can enable evasion or forgery. Enterprise automation can transform a weak provenance indicator into a high-impact false accusation or an attacker-controlled denial-of-service condition.

The useful security objective is defensible provenance under documented conditions. Achieving it requires watermarking, explicit disclosure, content credentials where formats support them, provider and enterprise audit trails, calibrated uncertainty, and human review.

The text carries the signal. The surrounding systems determine whether that signal becomes evidence, noise, or an attack primitive.

## Sources

- Anthropic, [How Claude's text watermark works](https://www.anthropic.com/news/claude-text-watermark), August 14, 2026.
- European Commission, [Code of Practice on Transparency of AI-Generated Content](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content), updated July 31, 2026.
- European Commission, [Guidelines on transparency obligations for providers and deployers of certain AI systems](https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations), August 6, 2026.
- Sumanth Dathathri et al., [Scalable watermarking for identifying large language model outputs](https://www.nature.com/articles/s41586-024-08025-4), *Nature*, 2024.
- Google AI for Developers, [SynthID: Tools for watermarking and detecting LLM-generated text](https://ai.google.dev/responsible/docs/safeguards/synthid).
- Google DeepMind, [SynthID-Text reference implementation](https://github.com/google-deepmind/synthid-text).
- Nikola Jovanovic, Robin Staab, and Martin Vechev, [Watermark Stealing in Large Language Models](https://proceedings.mlr.press/v235/jovanovic24a.html), ICML 2024.
- Tom Sander, Pierre Fernandez, Alain Durmus, Matthijs Douze, and Teddy Furon, [Watermarking Makes Language Models Radioactive](https://arxiv.org/abs/2402.14904), NeurIPS 2024.
- Nikola Jovanovic, Thibaud Gloaguen, and Martin Vechev, [Probing Google DeepMind's SynthID-Text Watermark](https://www.sri.inf.ethz.ch/blog/probingsynthid), December 20, 2024.
- Aldan Creo and Shushanta Pudasaini, [Evading AI-Generated Content Detectors Using Homoglyphs](https://arxiv.org/abs/2406.11239), 2024.
- Zhaoxi Zhang et al., [Character-Level Perturbations Disrupt LLM Watermarks](https://arxiv.org/abs/2509.09112), NDSS 2026.
- Yusheng Zhao et al., [The Mark Fades: Adaptive Evolutionary Paraphrase-Based Attack Against LLM Watermarks](https://aclanthology.org/2026.findings-acl.459/), Findings of ACL 2026.
