# Landscape: LLM security scanners, red teaming tools, benchmarks, and the Congressional App Challenge rules

Date: 2026-10-05
Scope: part 1 (tools and positioning) and part 2 (CAC 2026 rules, judging, past winners).
Method: every row below comes from a README, license file, source file, dataset or paper I downloaded and read on 2026-10-05. Anything I could not open is marked [unverified]. No live scan has ever been run by PolyGuard, so nothing here describes a PolyGuard result.

## 1. Summary

1. Multilingual prompt injection is already tested by several tools and papers (garak 5 languages, CyberSecEval 17 labels, promptfoo any list, DeepTeam one language per attack, Lakera claims 100+ observed). None of the sources I read run a per-language significance test or give a confidence interval around a language gap.
2. What PolyGuard has that I did not find elsewhere: language as the unit of analysis with a preregistered max-gap permutation test, benign capability controls per language, and remediation judged on a held-out phrasing. These are method claims, and they hold whether or not a gap is found.
3. What is not new: tier stratification (Yong et al. used the same Joshi et al. 2020 classes in 2023), canary tokens, LLM judges, machine translation labelled as such, CI gates.
4. Weaknesses: zero live data, machine-translated languages with no native validation, single turn only, canary as a proxy, one judge vendor, and a name collision with an existing paper called PolyGuard.
5. CAC: AI use must be "fully disclosed", the video is 3 minutes max, judges may demand the app and source code and disqualify if you refuse, and nothing in the rules bars a paid API. No past winner in 2023 to 2025 tested LLMs for security.

## 2. Tools: table and notes

Columns: what it tests, multilingual coverage and how built, human validation, statistics, defence evaluation, license and status (from the repo LICENSE file or the GitHub API license field, 2026-10-05).

| Tool | What it tests | Multilingual | Human validation of languages | Statistics | Defence evaluation | License, status |
|---|---|---|---|---|---|---|
| garak (NVIDIA) https://github.com/NVIDIA/garak | Probe library: prompt injection, jailbreaks, encoding, latent injection, system prompt extraction, leakage and more (garak/probes has 44 modules) | One buff, garak/buffs/low_resource_languages.py: DeepL machine translation into 5 languages (ET, ID, LV, SK, SL), outputs translated back to English before detection. The sysprompt_extraction probe is lang "en" | None found | Yes: garak/analyze/bootstrap_ci.py is "Non-parametric bootstrap with Se/Sp correction" (detector sensitivity and specificity); calibration.py gives z-scores against reference models | No hardening loop | Apache-2.0, active (pushed 2026-10-02, 9,435 stars) |
| PyRIT (Microsoft) https://github.com/microsoft/PyRIT | Orchestrated red teaming framework: attacks, converters, scorers, memory | TranslationConverter: "Translates prompts into different languages using an LLM", one language per converter instance, no language list shipped | Scorer evaluation against human labelled data exists (scorer_evaluation/human_labeled_dataset.py, krippendorff.py), for scorers, not translations | I grepped analytics/result_analysis.py for confidence, Wilson, bootstrap and interval: no hits | No hardening loop | MIT, active (pushed 2026-10-05) |
| promptfoo red team https://github.com/promptfoo/promptfoo | Plugins and strategies for prompt injection, jailbreaks, hijacking, leakage, agents | Global `language` field takes one language or a list; "test cases are generated for each language". Docs suggest "Bengali (bn), Swahili (sw), or Javanese (jv)" as low-resource examples (site/docs/red-team/configuration.md) | None found | None found in the red team docs I read (grep for p-value, confidence interval, statistical) | Compares prompts and models side by side; CI/CD integration listed in README | MIT, active. README banner: "Promptfoo is now part of OpenAI. Promptfoo remains open source and MIT licensed." |
| Giskard https://github.com/Giskard-AI/giskard-oss | v3 giskard-scan: agent vulnerability scanner (red teaming, prompt injection, jailbreaks, harmful content), RAG evaluation, LLM judge checks | No multilingual statement in the README [rest unverified] | None found | Not documented in README [unverified] | Test and check framework | Apache-2.0, active. v2 "no longer actively maintained" |
| DeepTeam (Confident AI) https://github.com/confident-ai/deepteam | 50+ vulnerabilities (including Prompt Leakage), 20+ attacks, guardrails, OWASP, NIST and MITRE ATLAS mappings | Multilingual attack: "converts prompts into low-resource or non-English languages". One LLM rewrites one attack into a chosen or auto-picked language and checks "is_translation" (deepteam/attacks/single_turn/multilingual) | None | None in README | Guardrails, no measured hardening loop | Apache-2.0, active |
| Rebuff (Protect AI) https://github.com/protectai/rebuff | Defence: heuristics, LLM detector, vector DB, canary tokens | None stated | None | None | It is a defence. README: "still a prototype and cannot provide 100% protection" | Apache-2.0, ARCHIVED (last push 2024-08-07) |
| LLM Guard (Protect AI) https://github.com/protectai/llm-guard | Input and output scanners (prompt injection, leakage, toxicity) | None stated in README | None | None | It is a defence | MIT, ARCHIVED ("no longer under active development or maintained") |
| Vigil https://github.com/deadbits/vigil-llm | Detection scanners: vector similarity, YARA heuristics, transformer model, canary tokens | None stated | None | None ("Vigil-Eval" listed as coming soon) | Defence | Apache-2.0, "alpha", last push 2024-01-31 |
| Purple Llama CyberSecEval https://github.com/meta-llama/PurpleLlama | Cyber risk suite: insecure code, cyberattack helpfulness, prompt injection (textual and visual), false refusal rate | Dataset prompt_injection_multilingual_machine_translated.json: I counted 1,004 rows and 17 speaking_language labels; the English set has 251 rows. README: "multilingual prompts were created using automated machine translations of the english prompts and therefore may not be entirely accurate". Each prompt_id appears once, so languages are not paired case by case, and Hindi has 251 rows against 36 to 57 for most others | None; README disclaims accuracy. The CyberSecEval 2 paper footnote lists non-English as a non-goal ("We also do not consider prompts given in languages other than English") | Output is counts and percentages per model, variant, type, risk category and speaking language. No interval or test in the documented format | Reports False Refusal Rate as a safety-utility tradeoff (arXiv:2404.13161) | Repo LICENSE is the Llama 3.2 Community License (GitHub says NOASSERTION); per-component terms [unverified]. Active |
| HarmBench https://github.com/centerforaisafety/HarmBench | Standardised comparison of 18 red teaming methods against 33 models and defences (arXiv:2402.04249) | None in README (0 hits) | Judge classifier checked against human labels: 88.6% agreement for the validation classifier, 93.2% for the test classifier (paper) | Attack success rates | Includes an adversarial training defence experiment | MIT, last push 2024-08-16 |
| AgentDojo https://github.com/ethz-spylab/agentdojo | Agent prompt injection through tool outputs: 97 tasks, 629 security test cases (arXiv:2406.13352) | None | n/a | "We report 95% confidence intervals" in the paper tables | Evaluates defences, plots utility against attack success on a Pareto frontier | MIT, last push 2026-06-02 |
| InjecAgent https://github.com/uiuc-kang-lab/InjecAgent | Indirect injection against tool agents: 1,054 test cases, 17 user tools, 62 attacker tools; ReAct GPT-4 vulnerable 24% (arXiv:2403.02691) | None | n/a | Cramer's V association tests with p-values between factors, no per-language analysis | Not a defence study | MIT per GitHub API (no LICENSE file at the path I fetched), last push 2024-07-02 |
| BIPIA https://github.com/microsoft/BIPIA | First benchmark for indirect prompt injection; proposes boundary awareness and explicit reminder defences (arXiv:2312.14197) | None | n/a | None found in the paper (0 hits) | Yes, two defences evaluated | MIT text plus separate dataset licenses (GitHub says NOASSERTION), ARCHIVED, last push 2024-04-15 |
| Tensor Trust https://github.com/HumanCompatibleAI/tensor-trust-data | 126,000+ human attacks and 46,000+ defences from an online game; benchmarks for prompt extraction and prompt hijacking (arXiv:2311.01011) | Not multilingual by design | Human generated, not translated | Not found | Defences are player written | Data repo has no LICENSE file at the path I fetched; code repo BSD-2-Clause |
| Gandalf and Gandalf the Red (Lakera), arXiv:2501.07927 | Crowd-sourced password extraction game, 279k released prompt attacks, D-SEC threat model that separates attackers from legitimate users | The paper tags "Non-English input" as one attack category among others. No per-language analysis found in the text | Human players | Yes: "95% confidence intervals" on attacker success rates and on utility tables | Yes, the strongest defence evaluation I read: security and utility together, finding that "defenses integrated in the LLM (e.g., system prompts) can degrade usability even without blocking requests" | Dataset released with paper (license [unverified]) |

### Commercial products

- Lakera Guard and Lakera Red. https://www.lakera.ai/ says "Learning from 1M+ hackers around the world", "Observing 100+ languages in real-time" and "Delivering sub-50 ms runtime latency". https://www.lakera.ai/lakera-red lists "Multilingual & Multimodal Attacks" as a risk category. The Check Point press release (https://www.checkpoint.com/press-releases/check-point-acquires-lakera-to-deliver-end-to-end-ai-security-for-enterprises/) says "Supports more than 100 languages". Lakera is now part of Check Point (page footer: Check Point Software Technologies). The 100+ figure is a vendor claim about languages observed in traffic. I found no public method for how many languages the red team tests, how they were built, or any validation or statistics. [unverified beyond the marketing claim]
- Protect AI: acquired by Palo Alto Networks, completed July 22, 2025 (https://www.paloaltonetworks.com/company/press/2025/palo-alto-networks-completes-acquisition-of-protect-ai). The release says Prisma AIRS brings "model scanning, posture management, AI red teaming, runtime protection, and AI agent security". No language or statistics detail. [unverified]
- HiddenLayer: Automated Red Teaming for AI launched November 2024 (https://www.helpnetsecurity.com/?p=317463, https://hiddenlayer.com/autortai). Marketing only. [unverified]
- Mindgard: automated AI red teaming (https://mindgard.ai/). Marketing only. [unverified language coverage]
- All four are closed products with no methodology I could open. They can be compared on feature claims only, not rigor.

### Multilingual safety work PolyGuard must be measured against (papers I opened)

- Yong, Menghini and Bach, "Low-Resource Languages Jailbreak GPT-4" (arXiv:2310.02446): 12 languages grouped low, mid and high resource "based on their data availability [24]", and reference 24 is Joshi et al. (2020), the same source PolyGuard uses. Human annotation with BYPASS, REJECT and UNCLEAR labels. It reports an adaptive "combined attack" that counts success if any language in a group succeeds, which is itself a max over languages. 79% combined success on AdvBench for low-resource languages.
- Deng et al., MultiJail (arXiv:2310.06474): 3,150 samples, 315 English plus parallel samples in 9 languages, translated "by native speakers", with a separate group of native speakers verifying a random subset aiming for "a pass rate of over 97%". On translation method: machine translation gave a slightly higher unsafe rate, "11.15% on average, compared to human translation, which is 10.19%". The African languages paper (arXiv:2605.18239, abstract) goes the other way: human red teaming raised the average jailbreak rate from 59.8% to 75.8%. So the direction of machine translation bias is not settled.
- Aya red teaming, "The Multilingual Alignment Prism" (arXiv:2406.18682): seed harmful prompts per language come from a human annotated dataset (100 seeds per language, 50 global and 50 local) and are expanded with a multilingual model. Number of languages not rechecked [unverified].
- PolyGuard, a different project (arXiv:2504.04377, Kumar et al.): "A Multilingual Safety Moderation Tool for 17 Languages", a trained guard model with 1.91M training samples and a 29K prompt benchmark, with translations "verified by a high average translation score of 81.15 as rated by human annotators". Same name as this project. A judge searching "PolyGuard" may find it first.
- Abstracts opened: arXiv:2606.29602 ("non-English languages consistently exhibit higher compliance rates than English"), 2607.10080 (8 languages across resource levels), 2512.23684 (4 languages, Arabic injections had "little to no effect"), 2409.19521 (GenTel-Bench, 84,812 attacks). Other papers cited in RELATED_WORK.md (MIPIAD, the Turkish assessment) are [unverified here].

## 3. Positioning

Genuinely new, relative to what I read ("new" means I did not find it, not that it cannot exist):

1. Language as the statistical unit, with a preregistered max-gap permutation test. CyberSecEval buckets results per language but the languages are not paired on the same cases and no test is documented. Yong et al. use a max over languages as an attacker model, with no correction for how many languages were tried. That is a legitimate threat model but it cannot be read as a gap estimate. PolyGuard's own simulation (engine.py docstring, reproducible with selection_bias_demo.py) says a naive worst-minus-English rule fires 98% of the time against a model with no gap. That number is PolyGuard's own, not an external source.
2. Per-language capability controls (6 benign requests per language) used to exclude languages where the bot cannot follow instructions at all. Related ideas exist: CyberSecEval 2 reports False Refusal Rate and Gandalf the Red measures utility loss. I did not find a per-language incapacity check in any tool.
3. A pasted system prompt as the target, 5 categories x 3 phrasings, with the third phrasing held out when judging the hardened prompt, plus a benign follow-through check on the hardened prompt. Gandalf the Red and AgentDojo evaluate defences with utility, but I did not see a held-out phrasing in a multi-language grid.
4. A reproducibility package: instrument record (bank SHA-256, judge wording fingerprint, scoring version), replay that recomputes every number from stored evidence, and an exit code for incomparable baselines. garak keeps JSONL reports and has bootstrap tooling; I did not find an equivalent of replay or the baseline gate [unverified absence].
5. Breadth by design (87-language catalog with sourced tiers) is a plan, not data.

Not new, do not claim:
- The multilingual safety gap itself, tier stratification (Yong et al. use Joshi classes), canary tokens (Rebuff and Vigil), LLM judges (CyberSecEval), labelling machine translation as such (CyberSecEval does), CI integration (promptfoo README), the 5 injection families.
- A language count record: Lakera claims 100+ languages observed, though that is traffic, not a test grid.

Where PolyGuard is weaker:
- Zero live scans. The central low-resource hypothesis is untested (STATE.md, README).
- Translation: README and STATE.md say 20 author written languages with native feedback integrated for 3 (Spanish, Vietnamese, Arabic), none validated. Working tree check on 2026-10-05: attack_bank.json holds 52 languages (20 author, 32 machine, all native_reviewed false) and 780 attacks, and git shows the file modified and uncommitted, so README and STATE.md counts are stale against the working tree. MultiJail used native translators with a 97% pass target. PolyGuard has reverse-translation gates only.
- No judge error correction in the statistics. garak's bootstrap corrects for detector sensitivity and specificity, and HarmBench reports judge agreement with humans. PolyGuard's per-language judge error is unmeasured (README limits section).
- Single turn only. promptfoo, PyRIT and DeepTeam have multi-turn and adaptive attacks. AgentDojo and InjecAgent use real tool outputs, while PolyGuard's indirect injection is "simulated inside a message".
- One fixed judge vendor. A deliberate control, but also one blind spot.
- No attack adaptivity, which is Gandalf the Red's central point.
- Name collision with arXiv:2504.04377.

## 4. CAC 2026 rules and judging (primary sources)

Rulebook: https://www.congressionalappchallenge.us/wp-content/uploads/2026/05/2026-CAC-Rules.pdf (6 pages, downloaded and read in full 2026-10-05). The rules page https://www.congressionalappchallenge.us/students/rules/ points to it as the "COMPLETE RULEBOOK". The FAQ page https://www.congressionalappchallenge.us/congress/frequently-asked-questions/ has nothing on AI, paid services, source code or testing (it is aimed at Members of Congress).

Deadline, quoted: "12:00 pm EDT, Monday, October 26th, 2026." Also: "After the Submission Period has ended, the Submission cannot be modified in any way."

AI USAGE, quoted in full: "The use of AI tools in app development for the Congressional App Challenge is permitted, provided that all AI usage is fully disclosed in the submission materials. AI may only be used to support specific aspects of the project and must not constitute the entirety of the technical development. Participants are expected to demonstrate significant individual contributions and technical understanding of their app."

ORIGINALITY, quoted: "The app must be original and solely created by the contestant. All coding and technical development must be done by the student or student team. While participants may use open-source libraries, frameworks, and external tools, they must clearly document any such usage and ensure their project reflects significant personal effort and technical understanding. No other party should have any rights or interest in the app, whether known or unknown."

PRIOR PROJECTS, quoted: "Students may submit any app they've created after October 30th, 2025. If submitting a 2.0 version of an app, only the new coding should be highlighted for consideration." (PolyGuard's first commit is 2026-09-19, so it qualifies.)

TEAMS and ENTRIES, quoted: "Students can compete as individuals, or in teams of up to four (4) students." and "Students may only submit ONE app per year. Multiple entries across multiple teams is not allowed."

FUNCTIONALITY, quoted: "The app must demonstrate some degree of functionality to be considered competitive."

CONTENT, quoted in part: "the app must not violate any Intellectual Property, common law, or privacy rights of third parties."

DEMONSTRATION VIDEO, quoted: "DEMONSTRATION VIDEO (max 3 min)". Required content: "The name(s) of each participant", "The name of the app", "Clearly explain the purpose of the app (Students should do this in one, clear sentence)", "Explain the app's target audience (who the app is intended for?)", "The tools and coding languages used to create the app", "Showcase the functionality of the app". Also: "The video should be 1-3 minutes long. Video submissions which do not adhere to the time constraints may be penalized by the judges at their discretion. This is not a video-creation competition. However, the judges view the demonstration video to learn about the app. The video should be as clear and compelling as possible." And: "Upload the completed video to YouTube or Vimeo. The video must be set to "public"."

WRITTEN QUESTIONS, quoted ("similar to the following"): "What is the title of your app?", "Explain the app's purpose.", "What inspired you to create this app?", "What technical/coding difficulty did you face in programming your app, and how did you address this technical challenge?", "What did you learn while participating in the CAC? What was your biggest takeaway?", "What would you change about your app if you were to create a 2.0 version?"

JUDGING (section 7), quoted: "Demonstration Videos and Submission Answers will be reviewed and evaluated by the Member of Congress and their office. Members of Congress may opt to use a panel of judges to evaluate applications." "Apps can be judged based on the following criteria: a. Quality of the idea (including creativity and originality) b. Implementation of the idea (including user experience and design) c. Demonstrated excellence of coding and programming skills." "The Judges have the right to request access to the App and source code in person or via any reasonable manner to verify that the App functions and operates as stated in the Submission Form. Failure by a Contestant to honor such a request will result in the Submission's immediate disqualification." "Members of Congress and their staff reserve the right to substitute or modify the judging process or criteria at any time for any reason."

Paid APIs and external services: no rule, FAQ entry or page I opened mentions them, so nothing bars a paid API. Winners that integrate OpenAI and Gemini APIs are listed in 4b. My inference, not a rule: because judges may verify "that the App functions and operates as stated", a hosted demo that refuses requests when the spend guard trips or the key is absent could look broken. The app should state clearly what is simulated (it already does).

Judging window and embargo (judges page, https://www.congressionalappchallenge.us/get-involved/judges/): the judging period is printed as October 30 to November 23 with evaluations due November 23; judges "Watch Demonstration Videos" of "no longer than 3 minutes each" and "Review short answer questions". Rulebook section 8: results embargoed until January 15, 2027.

Older rubric (a guide titled "2021 CAC RUBRIC GUIDE", https://www.congressionalappchallenge.us/wp-content/uploads/2022/09/CAC-Judging-Rubric.pdf): 30 points, Concept (Ideology, Impact, Structure) and Technology (Function, Code, UI), each scored 1 to 5. Top score wording includes "Video is innovative and engaging", "App is functional with complex features", "Explanation of code indicates immense understanding", "App is highly innovative in design and interface". The 2026 rulebook says criteria may change, so treat this as a hint only.

District: the participating districts page (https://www.congressionalappchallenge.us/students/participating-districts/) showed a check mark for WA01 (DelBene), WA08 (Schrier) and WA09 (Smith) when fetched on 2026-10-05. Ishaan should confirm which district he lives in or attends school in, and that its Member shows as participating. [unverified which district Sammamish and Eastlake map to] Registration needs a personal (non-school) email and a parent or guardian contact (rulebook section 2).

### 4b. Past winners 2023 to 2025 (verified by scan)

Method: from https://www.congressionalappchallenge.us/2023-winners/ , /2024-winners/ and /2025-winners/ I downloaded every linked district winner page (1,049 pages, for example https://www.congressionalappchallenge.us/25-MI02/) and searched the text. Each page is a short write-up: app name, team, a one-sentence description, and a quoted answer to "what inspired you". The site publishes no judge scores or comments, so what made winners stand out is not published.

Participation printed on the pages: 2023, 374 Members hosting, 11,334 students, 3,645 apps. 2024, 382 Members, 12,682 students, 3,881 apps. 2025, 394 Members, "More than 13,800 students", "over 4,600 original apps".

Security flavoured district winners (all consumer education or utility tools, none about testing an AI system):
- 2023 CA-13 "SafeNet CyberSecurity" (https://www.congressionalappchallenge.us/23-CA13/): "password control and awareness about security risks, coupled with instant alerts".
- 2024 MI-02 "Security Operations" (https://www.congressionalappchallenge.us/24-MI02/).
- 2024 MD-05 "YourPasswordStrong" (https://www.congressionalappchallenge.us/24-MD05/), a password generator.
- 2025 MI-02 "Phishing Hook" (https://www.congressionalappchallenge.us/25-MI02/): "personal phishing training through games alongside a scam email simulation". The same lead student (Levi Willette) won MI-02 in 2024 and 2025.
- 2025 CA-43 "SCAMBIO" (https://www.congressionalappchallenge.us/25-CA43/): "Scam Detection, Prevention, and Simulation".

No winner among the 1,049 pages mentions prompt injection, jailbreaking, red teaming or adversarial testing of LLMs. [Limit: a keyword scan of published write-ups.] PolyGuard would be unusual in topic. The security winners were interactive, explain-it-to-anyone tools (games, simulations), the same shape as PolyGuard's "spot the attack" game and permutation test page.

Apps calling third party AI APIs did win: 2025 TX-20 "GlobaLingo" ("By integrating OpenAI's API", https://www.congressionalappchallenge.us/25-TX20/), 2025 IL-06 "HeadacheWise" (Gemini API), 2024 TX-34 "DreamHaven" (Gemini API), 2025 FL-06 "Visionary Notes" (OpenAI), 2025 TX-22 "PoliDebater" (a large language model debate app). A technically deep winner: 2025 NH-01 "Edge(u)cation" (https://www.congressionalappchallenge.us/25-NH01/), "I created my own inference framework from scratch: mistral.rs".

Pattern (my reading, not a published criterion): the quoted inspiration is nearly always a personal or community story. PolyGuard's inspiration answer should be concrete and personal.

## 5. What PolyGuard should do

Ranked, with effort in hours. Everything here works offline without a key unless noted.

Framing and compliance first (highest value, cheapest):
1. Add a short "what is and is not new" block to the video script and submission answers using the claims below. Never say the gap was discovered. (1 h)
2. Disambiguate the name: put "multilingual prompt injection scanner" in every title line and state once that it is unrelated to the PolyGuard guard model (arXiv:2504.04377). A rename is cheapest now. (1 h to decide, 2 to 4 h to rename)
3. Fix stale counts: README and STATE.md say 20 languages in the bank while the working tree has 52 (32 machine). Reconcile and rerun consistency.py before submitting, since judges may request the source. (1 to 2 h)
4. AI disclosure: the rules require "all AI usage is fully disclosed in the submission materials" and "significant individual contributions". Write a plain section in the submission and README naming every tool used and exactly which parts it supported, and keep Ishaan's own contributions front and center in the video (statistics design, preregistration, the game, the audit decisions). (2 h)

Cheap features, ranked by benefit per hour:
1. Tag the 5 categories with OWASP LLM01 and MITRE ATLAS ids in the report and CSV. garak tags probes (for example "owasp:llm01") and DeepTeam maps to OWASP, NIST and ATLAS. (2 h)
2. Publish the attack bank as a dataset with a card: provenance per language, SHA-256, license, and explicit "machine translated, unvalidated" flags. CyberSecEval ships a machine translated set with a caveat. (2 h)
3. A security versus utility readout for remediation: Wilson intervals on break rate and benign follow-through before and after hardening, per tier. Gandalf the Red and AgentDojo set this standard (95% intervals, Pareto view). The engine already has the pieces. (3 h)
4. Judge error correction: a sensitivity and specificity corrected interval (as garak's bootstrap does) once a bilingual gold set exists, plus agreement with human labels as HarmBench reports. Needs the key and labels, and fits the dual judge kappa run already planned in STATE.md. (5 h)
5. Paired analysis: the same 15 attacks appear in every language and the current max-gap test does not use that pairing (docs/research/statistics.md notes this). Pairing would add power and removes the CyberSecEval style confound of different cases per language. Validate with calibrate_stats.py. (4 to 6 h)
6. Back-translation robustness judge: translate replies to English and re-judge, as garak's low resource buff does on output. Costs extra calls, so make it a flag. (4 h)
7. One code-switching and one transliteration phrasing for the 20 author written languages. (8 h, lowest priority before October 26)

Do not do before the deadline: adaptive multi-turn attacks (PyRIT, DeepTeam territory), real tool-agent environments (AgentDojo territory), a trained detector. They add risk and no judging value.

The three strongest claims once real data exists (all conditional, none is a result today):
1. "We measured per-language gaps with language as the unit and a preregistered correction for choosing the worst of N," reported for at least one real model and prompt, including if the answer is no gap. The method claim is true even on a null result, and the preregistration makes the null reportable.
2. "N of M languages were capability-limited, so a raw break rate would have scored them as safe." Checkable from the evidence bundle. Only valid if live scans show such languages, so do not pre-write it.
3. "A hardened prompt closed X of Y holes on a held-out phrasing while benign follow-through stayed at Z%," with intervals, per tier.
Never write any of these as found until the evidence bundle exists and `python cli.py replay` reproduces it.

What not to claim:
- Not "first multilingual prompt injection scanner" (garak, promptfoo, DeepTeam and CyberSecEval all have multilingual features).
- Not "87 languages tested" until 87 are in the bank and scanned. Not "native speaker validated" for any language (feedback received is not validation).
- Not that machine translation understates vulnerability as a general fact: MultiJail measured machine translation at 11.15% against human 10.19%. Say the direction is unsettled in the literature.
- Not that low-resource languages are less defended in this bot, until data says so.
- Nothing about Lakera, HiddenLayer, Mindgard or Protect AI beyond their own marketing statements.

CAC checklist from the rules: demo video under 3 minutes (aim for 2:45) with participant name, app name, one sentence purpose, audience, tools and languages, and a public YouTube or Vimeo link; keep the live site working for judges and state what is simulated; answer the technical difficulty question with the max-gap bias story (98% false alarm), the clearest evidence of coding excellence and technical understanding; submit well before 12:00 pm EDT on October 26 (9:00 am Pacific) because the submission cannot be modified afterward.

## 6. Sources

CAC (all opened 2026-10-05):
1. https://www.congressionalappchallenge.us/wp-content/uploads/2026/05/2026-CAC-Rules.pdf
2. https://www.congressionalappchallenge.us/students/rules/
3. https://www.congressionalappchallenge.us/congress/frequently-asked-questions/
4. https://www.congressionalappchallenge.us/get-involved/judges/
5. https://www.congressionalappchallenge.us/wp-content/uploads/2022/09/CAC-Judging-Rubric.pdf
6. https://www.congressionalappchallenge.us/students/participating-districts/
7. https://www.congressionalappchallenge.us/students/past-winners/ , /2023-winners/ , /2024-winners/ , /2025-winners/ and 1,049 district pages such as /25-MI02/, /25-CA43/, /25-TX20/, /25-NH01/, /23-CA13/, /24-MI02/, /24-MD05/

Tool repos (README, LICENSE and source read; GitHub API for status and stars):
8. https://github.com/NVIDIA/garak (garak/buffs/low_resource_languages.py, garak/analyze/bootstrap_ci.py, garak/analyze/calibration.py, garak/probes/sysprompt_extraction.py)
9. https://github.com/microsoft/PyRIT (pyrit/converter/translation_converter.py, pyrit/score/scorer_evaluation/)
10. https://github.com/promptfoo/promptfoo (README, site/docs/red-team/configuration.md)
11. https://github.com/Giskard-AI/giskard-oss
12. https://github.com/confident-ai/deepteam (deepteam/attacks/single_turn/multilingual/)
13. https://github.com/protectai/rebuff
14. https://github.com/protectai/llm-guard
15. https://github.com/deadbits/vigil-llm
16. https://github.com/meta-llama/PurpleLlama (CybersecurityBenchmarks/README.md, datasets/prompt_injection/prompt_injection_multilingual_machine_translated.json)
17. https://github.com/centerforaisafety/HarmBench
18. https://github.com/ethz-spylab/agentdojo
19. https://github.com/uiuc-kang-lab/InjecAgent
20. https://github.com/microsoft/BIPIA
21. https://github.com/HumanCompatibleAI/tensor-trust-data

Papers (PDF or abstract opened):
22. garak, arXiv:2406.11036
23. PyRIT, arXiv:2410.02828
24. HarmBench, arXiv:2402.04249
25. AgentDojo, arXiv:2406.13352
26. InjecAgent, arXiv:2403.02691
27. BIPIA, arXiv:2312.14197
28. Tensor Trust, arXiv:2311.01011
29. CyberSecEval 2, arXiv:2404.13161
30. Gandalf the Red, arXiv:2501.07927
31. Yong et al., arXiv:2310.02446
32. MultiJail, arXiv:2310.06474
33. Aya red teaming, arXiv:2406.18682
34. PolyGuard guard model, arXiv:2504.04377
35. African languages multilingual jailbreaking, arXiv:2605.18239 (abstract)
36. arXiv:2606.29602, arXiv:2607.10080, arXiv:2512.23684, arXiv:2409.19521 (abstracts)

Commercial (vendor pages, marketing claims only):
37. https://www.lakera.ai/ , https://www.lakera.ai/lakera-red , https://docs.lakera.ai/
38. https://www.checkpoint.com/press-releases/check-point-acquires-lakera-to-deliver-end-to-end-ai-security-for-enterprises/
39. https://www.paloaltonetworks.com/company/press/2025/palo-alto-networks-completes-acquisition-of-protect-ai
40. https://hiddenlayer.com/autortai and https://www.helpnetsecurity.com/?p=317463
41. https://mindgard.ai/

PolyGuard repo files read: README.md, STATE.md, RELATED_WORK.md, docs/research/statistics.md, attack_bank.json (counts), engine.py (function names and the max-gap docstring). AUDIT.md was not read in full.
