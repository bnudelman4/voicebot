# Bug Report, Pivot Point Orthopedics Voice Agent

Tested by placing automated patient calls to the Pretty Good AI test line
(+1-805-439-8008) across 14 scenarios covering scheduling, rescheduling,
cancellation, refills, insurance/hours/location questions, and adversarial edge
cases (closed-day booking, ambiguous dates, nonexistent records, controlled
substances, topic switches, identity corrections, out-of-scope requests, and
barge-in). The caller acted as patient Benjamin Nudelman (DOB March 31, 2006),
whose account had only a name and DOB on file.

Issues are ordered by severity. Timestamps refer to the matching
transcript-NN.txt / recording-NN.mp3 pair.

---

## High

### 1. Incoherent identity verification and record handling

- **Severity:** High
- **Scenario:** Recurring across hours_location_insurance, new_appointment, wrong_then_corrected_dob, reschedule, ambiguous_date
- **Where:** transcript-03 at 00:34; transcript-02 at 01:44; transcript-12 at 00:37; cross-call (transcript-02, -04, -08)
- **What happened:** The agent's handling of patient identity is internally contradictory across every call.
  - It states at the start of every call that it has no record of the patient.
  - Yet it tells the patient their date of birth "doesn't match our records," records it just said don't exist. Verbatim: "the birthday doesn't match our records, but for demo purposes I'll accept it" (transcript-03, 00:34).
  - When the patient gives a wrong DOB and then corrects it to the right one, the correction changes nothing. The agent routes it into new-patient creation regardless, because there is no record to verify against (transcript-12, 00:37).
  - During booking it refused to schedule a new appointment, saying the patient "already has one scheduled" (transcript-02, 01:44), despite the "no record" claim.
  - It nonetheless persists appointment state across calls. An appointment discussed in one call was still known in a later call (transcript-02, -04, -08).
- **Why it's a problem:** Identity verification is decorative rather than enforced. The agent announces it is bypassing it ("for demo purposes I'll accept it"), and no DOB input (correct, wrong, or corrected) actually gates anything. The "no record" greeting also contradicts the agent's own persisted state and its claim of an existing appointment. The agent has no coherent model of who the patient is or what records exist for them. In a real clinic this is a patient-identity and privacy failure, and it wrongly blocked a legitimate booking.

### 2. Long silent dead-air during record lookups

- **Severity:** High
- **Scenario:** refill, hours_location_insurance
- **Where:** transcript-05 at 03:04 (about 10 to 15 seconds); transcript-03 at 01:35 (about 5 seconds)
- **What happened:** When the agent performs a lookup (checking open refill requests, confirming hours), it goes silent for an extended period with no audio, no backchannel, and no hold message before responding. On transcript-05 this was roughly 10 to 15 seconds; on transcript-03 it was about 5 seconds.
- **Why it's a problem:** A 10 to 15 second unexplained silence is indistinguishable from a dropped call. A real patient would either start talking over the agent or hang up. The gaps occur specifically during backend lookups, with no "let me check that, one moment" cue to signal the line is still active. The behavior recurs across scenarios, so it is systemic latency rather than a one-off.

---

## Medium

### 3. Agent repeatedly re-states information it has already given

- **Severity:** Medium
- **Scenario:** Recurring across hours_location_insurance, reschedule, ambiguous_date
- **Where:**
  - transcript-03 at 01:28, re-stated full hours and "closed Saturday" after the patient had already read them back and the agent had confirmed
  - transcript-04 at 00:46, repeated the full street address, doctor name, and appointment details 3 to 4 times while confirming a reschedule
  - transcript-08 at 02:55 and 03:55, said "no openings for July 3rd" twice in a row, then repeated it again
  - The "should I transfer you to a live team member" prompt also recurred verbatim across calls
- **What happened:** Across multiple calls and scenarios, the agent repeats information it has already provided, including confirmations, addresses, hours, availability, and canned prompts, often several times in a row.
- **Why it's a problem:** Excessive repetition makes confirmations long and confusing, and suggests the agent re-reads the full record or re-runs its script on each turn instead of tracking what it has already said. The pattern is consistent across 3 or more calls, so it is a quality issue rather than an isolated slip.

---

## Low

### 4. Agent interrupts the caller before they finish speaking

- **Severity:** Low
- **Scenario:** closed_day_booking, topic_switch, out_of_scope
- **Where:** transcript-07 at 02:17; transcript-11 at 02:22; transcript-13 at 01:48 and 01:50
- **What happened:** On several calls the agent began speaking while the patient was still clearly mid-sentence, cutting them off. In transcript-07 it cut in with "we don't have any available morn," stopped mid-word, went silent, then restarted and delivered the full answer.
- **Why it's a problem:** Premature endpointing and aggressive barge-in talks over the caller and can cut off information the patient is still providing. The transcript-07 false-start also produces a garbled overlap. Recurs across 3 or more calls.

### 5. Agent clips its own greeting audio

- **Severity:** Low
- **Scenario:** hours_location_insurance (also seen on earlier calls)
- **Where:** transcript-03 at 00:10
- **What happened:** The agent's greeting cuts off right after "pretty good AI" and jumps straight into "am I speaking with Benjamin," dropping audio in the transition between the greeting and the verification prompt.
- **Why it's a problem:** The greeting-to-verification handoff loses audio and sounds broken to the caller. Repeatable across calls.

### 6. No special handling for a controlled-substance refill

- **Severity:** Low
- **Scenario:** controlled_substance_refill
- **Where:** transcript-10 at 03:16
- **What happened:** The patient requested a refill of oxycodone, a Schedule II controlled substance. The agent routed it through the same "I've submitted a request to the clinic support team" flow it used for routine medications, with no acknowledgment that a controlled substance requires different handling.
- **Why it's a problem:** Ideally the agent would flag that controlled substances must go through the prescribing physician directly. This is minor because the agent did not actually approve the refill, it forwarded the request like any other, but applying no distinction at all to a Schedule II drug is worth noting.

---

## Handled correctly

Not every probe surfaced a bug. The agent behaved correctly in several cases worth noting:

- **Denied a nonexistent appointment (transcript-09):** When asked to act on an appointment the patient never made, the agent correctly stated it had no such appointment rather than inventing one.
- **Held its ground on a real persisted appointment (transcript-04):** When the patient misremembered an existing appointment as Tuesday, the agent correctly maintained that its records showed Wednesday.
- **Knew its office hours (transcript-03):** The agent correctly stated it is closed on Saturdays and held that answer when the patient read the hours back.
- **Resolved ambiguous dates (transcript-08):** The agent handled vague date phrasing and resolved it to concrete dates without requiring the patient to over-clarify.
- **Kept context across a topic switch (transcript-11):** When the patient changed tasks mid-call, the agent followed the switch without losing track.
- **Stayed in scope (transcript-13):** When asked an out-of-scope question, the agent declined to answer outside its remit rather than improvising medical information.
