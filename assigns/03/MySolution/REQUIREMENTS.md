# Requirements Specification: LAMBDA Web Testing Environment (Version 1)

*Source material:* `assigns/03/LAMBDA-UI-informal-requirements.md` (the "brief").
*Status:* Draft for stakeholder review, 2026-09-29.
*Stakeholder answers received:* **none yet.** Every decision not stated in the brief
is labelled as an **assumption (A-n)** or a **proposal**, never as a stakeholder decision.

Keywords: **shall** = mandatory for version 1; **should** = desirable, may be deferred;
**may** = optional.

---

## 1. Purpose

The brief asks for a small, locally run, browser-based environment in which people can
write or load LAMBDA programs, check or run them with the LAMBDA compiler, understand
the outcome, and keep examples as a repeatable collection of named tests. This document
states *what* version 1 of that environment must do, so that a development team can
build it and an independent reviewer can check it. It does not choose frameworks,
languages, or internal algorithms.

## 2. Stakeholders and goals

| Stakeholder | Role | Main goals |
| --- | --- | --- |
| Instructor | Requester; lecture user | Switch between prepared examples quickly in class; edit and rerun them live; show compiler details (AST, generated code) when useful; never lose prepared examples. |
| Student – program writer | Primary user | Write, paste, or load a program; check or run it; get understandable errors that point to the right place in the source; save work and return later. |
| Student – compiler developer | Primary user | Keep a collection of named tests; rerun it after changing the compiler; see quickly which tests broke and why. |
| First-time user | Any of the above, new to the tools | Get from opening the page to a first result without prior knowledge of the compiler. |
| Compiler provider | External team (separate project) | Agree on a stable interface through which the environment invokes the compiler. |
| Environment developers / installer | Build and set up the system | Clear, testable requirements; setup instructions another person can follow. |

## 3. Scope

### 3.1 System boundary

```
 +------------------------ Environment (this project) ------------------------+
 |  Browser page: editor, examples, results, test collections, detail panels   |
 |        |                                                                    |
 |  Local service / Compiler Adapter  ---- selects one backend ----+           |
 +-----------------------------------------------------------------|-----------+
                                                                   |
                    +----------------------------+     +-----------v-----------+
                    | Sample-response backend    |     | LAMBDA compiler       |
                    | (inside the environment)   |     | (external, separate   |
                    +----------------------------+     |  project; evolving)   |
                                                       +-----------------------+
```

- **The environment** (in scope) is the page plus whatever local component is needed to
  call the compiler. It owns editing, examples, persistence, result presentation,
  cancellation, test collections, and the sample-response backend.
- **The compiler** (out of scope) parses, type-checks, compiles, and executes LAMBDA
  programs and reports results. The environment never decides whether a program is
  correct; it only presents what the compiler reports. Developing or fixing the
  compiler is a separate project (brief, "The compiler is still evolving").

### 3.2 In scope for version 1

Program editing; built-in examples; loading/saving program files; check and run;
distinct result categories; error-location navigation; optional compiler-detail panels;
stop and time limits; result provenance; environment-failure handling; named test
collections with batch runs and summaries; automatic persistence; collection
import/export; a clearly labelled sample-response mode; local installation.
Items given *Should* priority in §8 may slip from version 1 if time runs short.

### 3.3 Out of scope for version 1

Public hosting, user accounts, authentication; real-time collaborative editing;
built-in class-wide sharing (deferred, see §8 — export files are the interim path);
full IDE features (auto-completion, debugger, refactoring, syntax-aware highlighting);
sophisticated visual effects; defining LAMBDA's concrete syntax; developing the compiler.

---

## 4. Clarification questions and assumptions

### 4.1 Questions

No answers have been received from the stakeholder at the time of writing. The column
"Working assumption" records what this specification uses in the meantime; each
assumption is listed again in §4.2 and is open to change.

| # | Question to the instructor | Why the answer matters | Answer | Working assumption |
| --- | --- | --- | --- | --- |
| Q1 | What interface will the compiler expose (command-line tool, Python function, network service), and what does a response contain — result value, error kind, line/column, AST, generated code? | Determines FR-09, FR-10, FR-14 and §7. If locations or artifacts are never provided, those features cannot be tested. | Not yet received | A1 |
| Q2 | What will users type while the concrete notation is undecided — a draft LAMBDA syntax, or Python code that builds ASTs (as in the current interpreter)? | Affects the built-in examples, editor expectations, and whether the environment must understand the language at all. | Not yet received | A2 |
| Q3 | In "change its input", is the input part of the program text (e.g. `fact 5` → `fact 6`) or a separate input value supplied at run time? | A separate input field adds a UI element, an interface parameter, and a field in each test. | Not yet received | A3 |
| Q4 | Which outcomes may a test expect (integer, Boolean, other values, runtime error)? For an "expected error" test, is *any* compile error a pass, or must the message/kind/location match? | Defines the pass/fail rule in FR-15/FR-17; a too-loose rule hides regressions, a too-strict one breaks whenever messages are reworded. | Not yet received | A4 |
| Q5 | Should work persist only in the same browser on the same computer, or must it move between computers? Are files on disk acceptable as the way to move it? | Chooses between browser-local storage and file-based storage; "another session" is ambiguous. | Not yet received | A5 |
| Q6 | What maximum run time is acceptable before a program is stopped automatically, and should users be able to change it? | FR-12 needs a concrete default to be testable; too short breaks legitimate examples, too long stalls lectures and test runs. | Not yet received | A6 |
| Q7 | Which browsers and operating systems must be supported? | "A browser students normally use" is not verifiable without a list. | Not yet received | A7 |
| Q8 | Is exporting a collection to a file an acceptable substitute for sharing in version 1? | Decides whether sharing is deferred entirely or partly delivered by FR-19. | Not yet received | A8 |

### 4.2 Assumptions (used until the stakeholder answers)

| ID | Assumption | Affects |
| --- | --- | --- |
| A1 | The compiler can be invoked locally with source text and a mode (check/run) and returns a structured response as described in §7.1. Location and artifact fields are **optional** in that response. | FR-06–FR-14, §7 |
| A2 | Programs are plain text. The environment treats the text opaquely: it does not parse or validate LAMBDA itself. | FR-01, FR-02 |
| A3 | Program input is written in the program text; there is no separate input field. | FR-02, FR-15 |
| A4 | A test expects one of: an integer value, a Boolean value, a compile error, or a runtime error. A value test passes when the compiler's reported value equals the expected value exactly (integers by number, Booleans by `true`/`false`). A compile-error test passes on any compile error; an optional expected message substring may narrow it. | FR-15, FR-17 |
| A5 | Persistence is per browser profile on the user's own computer; moving work between computers uses exported files (FR-04, FR-19). Private/incognito windows, which discard stored data, are not covered. | FR-05, FR-19 |
| A6 | *Proposal:* default time limit 10 s per run or per test, user-adjustable from 1 s to 120 s. | FR-12 |
| A7 | *Proposal:* current and previous major release of Chrome, Firefox, Edge and Safari; setup on Windows, macOS and Linux. | QR-06 |
| A8 | Built-in class sharing is deferred; exporting and importing collection files is the version-1 substitute. | FR-19, §8 |
| A9 | Only one check/run is active per editor at a time; starting a new one cancels the previous one (the brief requires clarity about which version produced a result, not concurrent runs). | FR-13 |
| A10 | *Proposal:* performance targets refer to a "reference laptop" (4 CPU cores, 8 GB RAM, running the environment and compiler locally). | QR-01 |

---

## 5. Functional requirements

Priority column uses MoSCoW (M = Must, S = Should, C = Could); rationale in §8.

### 5.1 Editing, examples, and saved programs

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-01 | The system shall provide a multi-line text editor in which the user can type, paste, and edit a program. Text shall be sent to the compiler exactly as it appears in the editor (no silent reformatting). Line numbers shall be displayed. | M |
| FR-02 | The system shall provide a list of at least three built-in examples, including a factorial program, selectable in at most two user actions from the main page. Selecting an example shall load an editable **copy** into the editor; built-in originals cannot be modified, and a "restore original" action shall reload the unmodified example. | M |
| FR-03 | The user shall be able to open a program from a text file on the local computer into the editor. If this would replace editor content that is not stored as a named program (FR-05) or in a file, the system shall ask for confirmation first. | M |
| FR-04 | The user shall be able to save the current editor content to a text file on the local computer. | S |
| FR-05 | The system shall keep a workspace consisting of the current editor content, the user's named programs (created with a "save as" action, then listed, reopened, renamed, deleted), and all test collections. The workspace shall be saved automatically, and shall be restored after a page reload, closing the browser, or restarting the computer (per A5). | M |

### 5.2 Checking, running, and understanding results

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-06 | **Check:** the user shall be able to request compile-only processing. The result shall be either **Success** with the text "Compiled successfully" or **Compile error** with the errors reported by the compiler. The program shall not be executed. | M |
| FR-07 | **Run:** the user shall be able to request that the program be compiled and executed. On success the system shall display the resulting value reported by the compiler. | M |
| FR-08 | Every result shall be shown with exactly one of these outcome labels, in text: **Success**, **Compile error**, **Runtime error**, **Stopped by user**, **Time limit exceeded**, **Environment problem**. Compile and runtime errors shall be visibly distinct from each other and from environment problems. Compiler messages shall be shown in full. | M |
| FR-09 | When the compiler reports a source location for an error, the system shall display the line (and column, if given) and provide a single action that moves the editor cursor to that location and highlights the line. When no location is reported, the system shall say "location not reported by the compiler". | M |
| FR-10 | When the compiler supplies additional information (e.g. AST, generated code), the system shall offer it in panels that are **collapsed by default** and opened on request. If a kind of information is unavailable, its panel shall state "not provided by the compiler" rather than appear empty. | S |
| FR-11 | While a check or run is in progress, the system shall show that it is in progress and provide a **Stop** action. After Stop, the result shall be labelled "Stopped by user", the editor content shall be unchanged, and a new check/run shall be possible. | M |
| FR-12 | The system shall automatically stop any check, run, or test that exceeds the configured time limit (A6) and label it "Time limit exceeded", stating the limit that applied. | M |
| FR-13 | Each displayed result shall identify the program version that produced it (time of submission and a way to view the exact submitted text). If the editor content has changed since submission, the result shall be marked "**Out of date: program changed since this result**". Results from a cancelled or superseded request shall never replace a newer result (A9). | M |
| FR-14 | If the compiler cannot be reached, crashes, or returns a response the environment cannot interpret, the system shall report an **Environment problem** that explicitly says the program itself has not been judged, shall keep all editor and workspace content, and shall offer a "Try again" action that resubmits the same program. | M |

### 5.3 Test collections

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-15 | The user shall be able to create, rename, and delete named test collections, and within a collection create, edit, rename, and delete tests. Each test has a name unique within its collection, a program, and an expected outcome of one of the kinds in A4. The system shall reject a duplicate name with an explanatory message. | M |
| FR-16 | The user shall be able to create a test from the current editor content, pre-filling the expected outcome from the most recent up-to-date result, which the user can edit before saving. | S |
| FR-17 | The user shall be able to run all tests in a collection with one action. Each test shall be judged independently as **Passed**, **Failed** (outcome differs from expectation), or **Could not complete** (time limit, environment problem). A test that fails, times out, or crashes shall not prevent the remaining tests from running. The user shall be able to stop the batch; tests not yet run are then reported as "Not run". | M |
| FR-18 | After a collection run the system shall show a summary with counts per verdict, and for every test that did not pass: expected outcome, actual outcome, compiler messages, and an action to open that test's program in the editor. | M |
| FR-19 | The user shall be able to export a test collection to a single file and import such a file, producing an identical collection (names, programs, expectations). Import of a malformed file shall be rejected with a message and shall not alter existing collections. | S |

### 5.4 Compiler backends

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-20 | The system shall be able to operate with a **sample-response backend** instead of the real compiler. While it is active, a persistent, text-based indicator shall be visible, and every result and test verdict produced by it shall carry the label "SAMPLE RESPONSE – not a real compilation result". The active backend shall be chosen by configuration, not by editing source code. | M |

## 6. Quality requirements

| ID | Requirement and how it will be assessed | Pri |
| --- | --- | --- |
| QR-01 | **Responsiveness.** *Proposal:* on the reference laptop (A10), ordinary interface actions (typing, selecting an example, opening a panel or test) shall show their effect within 0.2 s, and Stop shall take visible effect within 1 s — including while a compiler request is running. Assessed by timing the actions during a run of a non-terminating program. | M |
| QR-02 | **Keyboard and non-colour access.** All main tasks — select example, edit, check, run, stop, jump to error, run collection, open a failed test — shall be possible using only the keyboard, with documented shortcuts for check, run, stop, and next/previous example. Every status shall be conveyed by text or symbol, not colour alone. Assessed by a keyboard-only walkthrough and a greyscale screenshot review. | M |
| QR-03 | **No loss of work.** Edits shall be persisted within 2 s of the last change (*proposal*). No user content shall be lost as a result of page reload, compiler crash, compiler unavailability, or a time-out. Assessed by fault-injection scenarios AC-4, AC-5, AC-8. | M |
| QR-04 | **Learnability and setup.** *Proposal:* (a) a person who has not seen the project follows the written setup instructions and has the environment running within 15 minutes on a supported OS; (b) a first-time user, without help, runs a built-in example and sees its result within 2 minutes. Assessed with at least three students not on the team. | S |
| QR-05 | **Replaceable compiler.** Switching between the sample backend and the real compiler, or to a newer compiler version that honours §7.1, shall require only configuration or changes confined to the Compiler Adapter — no changes to the browser page. Assessed by design review and by performing the switch. | M |
| QR-06 | **Compatibility.** The environment shall work in the browsers and operating systems listed in A7. Assessed by running AC-1 to AC-3 on each. | S |

## 7. External interfaces and dependencies

### 7.1 Compiler interface (to be agreed with the compiler provider — see Q1)

Proposed *logical* contract; transport and data format are unresolved.

| Direction | Content |
| --- | --- |
| Request | source text; mode (`check` or `run`); time limit; request identifier |
| Response | request identifier; status (`ok`, `compile_error`, `runtime_error`; the time limit is enforced by the environment, so no time-out status is needed); value (for `run` + `ok`); list of diagnostics, each with message and **optional** line/column; **optional** named artifacts (e.g. `ast`, `generated_code`) as text; compiler name/version |
| Cancellation | the environment must be able to stop an in-progress request (or abandon it and terminate the compiler process) |

Anything else the compiler does (no reply, malformed reply, process exit) is treated as an Environment problem (FR-14).

### 7.2 Other interfaces and dependencies

- **Sample-response backend:** implements the same contract as §7.1 with canned
  responses, including at least one of each status, one diagnostic with a location,
  and one response with artifacts, so all presentation features can be demonstrated.
- **Web browser:** the only user interface; see A7.
- **Local file system:** for opening/saving programs (FR-03, FR-04) and
  importing/exporting collections (FR-19). The collection file format shall be
  documented and plain-text so it can be versioned and emailed.
- **Browser/local storage:** for workspace persistence (FR-05).
- **Current course interpreter:** Python-based, works on ASTs built in Python; a
  likely first real backend, subject to Q1/Q2.

## 8. Priorities

| Priority | Requirements | Rationale |
| --- | --- | --- |
| Must | FR-01–03, FR-05–09, FR-11–15, FR-17, FR-18, FR-20; QR-01–03, QR-05 | The brief ranks "reliable editing, understandable results, and repeatable tests" above everything else; losing prepared examples and misreading environment failures are named frustrations; the sample backend is needed to start before the compiler is ready. |
| Should | FR-04, FR-10, FR-16, FR-19; QR-04, QR-06 | Valuable for teaching and convenience, but version 1 is still useful without them (e.g. FR-10 depends on what the compiler exposes). |
| Could / deferred | Built-in sharing with the class; separate program-input field; comparison of AST/code across compiler versions | Brief: sharing "I could live without"; an input field is only needed if Q3 is answered that way; cross-version comparison goes beyond the brief. |
| Won't (v1) | Public website, accounts, collaborative editing | Explicitly excluded by the brief. |

---

## 9. Acceptance criteria

These are *future* checks. "Sample backend" means the backend of FR-20 configured with the stated response.

| ID | Req(s) | Starting conditions | Action / input | Expected observable result |
| --- | --- | --- | --- | --- |
| AC-1 | FR-02 | Fresh workspace; real compiler (or sample backend set to return 720). | Select the factorial example; change its argument from 5 to 6; run; then choose "restore original". | Editor shows the example; after the edit, the run result is 720 labelled **Success**; after restore, the editor shows the original text with argument 5; the example list still shows the unmodified factorial. |
| AC-2 | FR-06, FR-08, FR-09 | Real or sample backend that reports a compile error at line 3, column 7. | Check a 5-line program; activate "go to error". | Label **Compile error**; message and "line 3, column 7" shown; cursor moves to line 3 col 7 and line 3 is highlighted; program was not executed. |
| AC-3 | FR-07, FR-08 | Backend returns `runtime_error` "division by zero" for a program that compiled. | Run the program. | Label **Runtime error** (not "Compile error"); full message visible; labels distinguishable in a greyscale screenshot. |
| AC-4 *(failure)* | FR-14, QR-03 | Editor contains unsaved-to-file edits; compiler process stopped / unreachable. | Run; then restart the compiler; choose "Try again". | First result is **Environment problem** stating the program was not judged; no Compile/Runtime error label appears; editor text unchanged. After retry the program's real result appears. |
| AC-5 *(failure)* | FR-11, FR-12, QR-01 | Time limit 10 s; a program that recurses forever. | (a) Run and press Stop after 3 s. (b) Run and wait. | (a) Within 1 s: label **Stopped by user**; editing and running possible again. (b) Between 10 s and 11 s after starting: label **Time limit exceeded (10 s)**. In both, typing in the editor during the run shows characters within 0.2 s. |
| AC-6 | FR-13 | Sample backend configured with a 5 s delay. | Run version A; within 5 s edit the text to version B; wait for the result. | The result shown is marked as belonging to version A and **Out of date**; "view submitted text" shows version A. If B is then run, A's late result never replaces B's. |
| AC-7 *(failure)* | FR-17, FR-18 | Collection of 4 tests: T1 expects 120 (gets 120); T2 expects `true` (gets `false`); T3 never terminates; T4 expects compile error (gets one). Time limit 5 s. | Run the collection. | All four are judged: T1 **Passed**, T2 **Failed**, T3 **Could not complete (time limit)**, T4 **Passed**. Summary: 2 passed, 1 failed, 1 could not complete. T2's detail shows expected `true`, actual `false`; "open in editor" loads T2's program. |
| AC-8 | FR-05, QR-03 | Workspace with 2 named programs and 1 collection of 3 tests; last edit made 3 s ago. | Reload the page; then close and reopen the browser. | After each step, both programs, the collection with all 3 tests, and the latest editor text are present unchanged. |
| AC-9 | FR-20 | Environment configured with the sample backend. | Run any example; run a collection. | Persistent "sample mode" indicator visible; every result and verdict labelled "SAMPLE RESPONSE – not a real compilation result". |
| AC-10 *(failure)* | FR-19 | One existing collection. | Import a file that is truncated / not in the documented format. | Import rejected with an explanatory message; existing collection unchanged; no partial collection created. |
| AC-11 | QR-02 | Mouse disconnected. | Using documented shortcuts only: select next example, run, stop, jump to error, run a collection, open a failed test. | Every step completes without a pointing device. |

## 10. Traceability

Brief sections: **[Intro]** opening paragraphs; **[Try]** "Trying a program";
**[Understand]** "Understanding what happened"; **[Tests]** "Keeping examples as tests";
**[Compiler]** "The compiler is still evolving"; **[Manage]** "Keeping the project manageable".

| Req | Source(s) |
| --- | --- |
| FR-01 | [Try] "typing or pasting a short program"; [Manage] "Reliable editing"; A2 |
| FR-02 | [Try] "a few examples… factorial… change its input… modify an example without losing access to the original"; [Manage] "move between examples without spending much time"; A3 |
| FR-03 | [Try] "programs saved in files… should not have to retype them" |
| FR-04 | [Try] "keep a program they have written"; A5 |
| FR-05 | [Try] "return to it later"; [Tests] "refreshing the page meant losing the examples… come back… in another session"; A5 |
| FR-06 | [Try] "Sometimes I only want to check whether a program compiles" |
| FR-07 | [Try] "run it and see the answer" |
| FR-08 | [Understand] "result should be easy to understand"; "compilation error and a failure while running… should not look like the same thing"; [Manage] "not depending only on colors" |
| FR-09 | [Understand] "help the student find that place in the source"; A1 |
| FR-10 | [Try] "inspect… abstract syntax tree or generated code, when that information is available… not… get in the way"; A1 |
| FR-11 | [Understand] "a way to stop it and move on"; "remain usable while work is in progress" |
| FR-12 | [Understand] "might never finish"; A6 |
| FR-13 | [Understand] "which version produced the result I am seeing"; A9 |
| FR-14 | [Understand] "cannot reach the compiler… not… think their program is wrong… keep their work and try again" |
| FR-15 | [Tests] "named tests… a program and some record of what should happen… an integer or a Boolean… expect the compiler to reject"; A4 |
| FR-16 | [Tests] "keeping examples as tests" (heading); proposal to reduce effort |
| FR-17 | [Tests] "run the collection again"; "One troublesome test should not make the rest… useless"; A4, A6 |
| FR-18 | [Tests] "quick summary… enough detail to investigate the ones that did not" |
| FR-19 | [Tests] "Sharing… could live without"; A5, A8 |
| FR-20 | [Compiler] "sample compiler responses… as long as nobody mistakes them for actual compilation results"; "connect the real compiler without starting the interface over" |
| QR-01 | [Understand] "remain usable while work is in progress"; [Manage] "respond promptly… even when the compiler takes longer"; A10 |
| QR-02 | [Manage] "main tasks with a keyboard… not depending only on colors"; "move between examples…" |
| QR-03 | [Understand] "keep their work"; [Tests] "frustrated if refreshing… losing the examples"; [Manage] "Reliable editing" |
| QR-04 | [Intro] "easy to get started… not used the compiler before"; [Manage] "another person can follow the instructions" |
| QR-05 | [Compiler] "connect the real compiler without starting the interface over again"; "coordinate with whoever provides the compiler interface" |
| QR-06 | [Manage] "work in a browser students normally use"; A7 |

## 11. Review notes

### 11.1 Issues found when reviewing the written draft

| # | Issue found | How it was addressed |
| --- | --- | --- |
| R1 | **Contradiction:** §3.3 put syntax highlighting out of scope, while §8 listed it as "Could". | Removed it from §8; it stays out of scope with the other IDE features. |
| R2 | **Inconsistent wording:** FR-06 reported "Compiled successfully", but FR-08 says every result carries one of six fixed outcome labels, and that phrase is not one of them. | FR-06 now says a successful check is labelled **Success** with the text "Compiled successfully". |
| R3 | **Ambiguous term:** FR-03 asked for confirmation before replacing "unsaved changes", but FR-05 saves the workspace automatically, so nothing is ever "unsaved". | FR-03 now asks for confirmation when the content is not stored as a named program or in a file. |
| R4 | **Unverifiable check:** AC-5 expected a time-out "at ~10 s", which has no pass/fail boundary. | Replaced with "between 10 s and 11 s after starting". |
| R5 | **Hidden dependency:** AC-1 expected the value 720 without saying which backend was used, and a sample backend would only return 720 if configured to. | AC-1 now states the backend in its starting conditions. |
| R6 | **Missing behaviour:** §7.1 did not say who enforces the time limit, so it was unclear whether the compiler needs a time-out status. | §7.1 now says the environment enforces the limit. A5 now notes that private/incognito windows are not covered by persistence. |

### 11.2 Decisions made while drafting

- **Concurrency vs. one result area:** allowing several runs at once would let an old
  result overwrite a newer one. Resolved by A9 and FR-13, tested by AC-6.
- **Features that depend on the compiler:** error locations and AST/code panels can only
  be required *when the compiler supplies them* (FR-09, FR-10; optional fields in §7.1; Q1).
- **"One troublesome test":** Passed/Failed alone cannot express time-outs and crashes, so
  FR-17 adds "Could not complete" and "Not run" (AC-7).
- **Ambiguous brief phrases:** "expected error" and "change its input" are handled by
  working assumptions A4 and A3, and the stakeholder is asked about them in Q4 and Q3.
- **Vague quality terms:** "promptly" and "easy to get started" are turned into
  measurable *proposals* with an assessment method (QR-01, QR-04).

## 12. Unresolved issues

| Issue | Blocking? | Linked to |
| --- | --- | --- |
| Transport and format of the compiler interface; whether locations and artifacts will exist | Blocks integration with the real compiler, not UI work (sample backend) | Q1, A1, §7.1 |
| Concrete source notation of LAMBDA and content of built-in examples | Blocks final examples, not the editor | Q2, A2 |
| Rule for matching expected errors and values beyond integer/Boolean | Affects FR-15/FR-17 | Q4, A4 |
| Default time limit; performance and setup targets | Numbers are proposals | Q6, A6, A10, QR-01, QR-04 |
| Supported browsers/OS | Affects QR-06 test matrix | Q7, A7 |
| Whether export files satisfy the sharing wish for version 1 | Affects FR-19 priority | Q8, A8 |
