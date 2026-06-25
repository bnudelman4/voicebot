### Fabricates an existing appointment and refuses to book

- Scenario: new_appointment
- Transcript: transcript-02.txt at [01:44]
- What happened: Agent said the patient already has an appointment scheduled and refused to book a new one, despite no appointments existing on the account (only name and DOB on file).
- Why it's a problem: Hallucinated patient state blocks a legitimate booking. A real patient with no appointment would be unable to schedule and wrongly turned away.
- Severity: High

### Agent clips its own greeting audio

- Scenario: hours_location_insurance (also seen in earlier calls)
- Transcript: transcript-03.txt at [00:10]
- What happened: Agent's greeting cuts off right after "pretty good AI" and jumps straight into "am I speaking with Benjamin," dropping audio in the transition.
- Why it's a problem: Greeting/verification handoff loses audio; sounds broken to a caller. Repeatable across calls.
- Severity: Low

### Long dead-air gap before agent responds (~5s)

- Scenario: hours_location_insurance
- Transcript: transcript-03.txt at [01:35]
- What happened: After the patient read back and confirmed the hours, ~5 seconds of total silence (no audio, no typing/keyboard sound) before the agent replied "you've got it right." Typical gaps on other calls were shorter; this one was long enough to feel like a dropped call.
- Why it's a problem: ~5s of dead air with no acknowledgment reads as a broken connection; a real caller would talk over it or hang up. The agent should backchannel or respond faster.
- Severity: Low

### Agent repeatedly re-states information it has already given

- Scenario: recurring across hours_location_insurance, reschedule, ambiguous_date
- Transcripts:
  - transcript-03 at [01:28] — re-stated full hours + "closed Saturday" after patient already confirmed them
  - transcript-04 at [00:46] — repeated full street address, doctor name, and appointment details 3-4 times while confirming reschedule
  - transcript-08 at [02:55] — said "no openings for July 3rd" twice in a row
  - transcript-08 at [03:55] — repeated the same again
  - (also recurring: the "should I transfer you to a live team member" script repeated across calls)
- What happened: Across multiple calls and scenarios, the agent repeats information it has already provided — confirmations, addresses, hours, availability, and canned transfer prompts — often several times in a row.
- Why it's a problem: Makes confirmations long and confusing and suggests the agent re-reads the full record or re-runs its script each turn instead of tracking what it has already said. Consistent pattern across 3+ calls.
- Severity: Medium

### (LOW-CONFIDENCE) Agent ignores partial pharmacy info, re-collects from scratch

- Scenario: refill
- Transcript: transcript-05.txt at [02:40]
- What happened: Patient gave a pharmacy street address and said it had been used before; agent continued asking for state/zip as if no info was provided.
- Why it's a problem: May be ignoring context the patient supplied. Borderline — could be legitimate disambiguation.
- Severity: Low

### 10-15s of silent dead air during refill lookup

- Scenario: refill
- Transcript: transcript-05.txt at [03:04]
- What happened: After the patient asked about open refill requests, the agent went silent for ~10-15 seconds while "checking," with no audio, backchannel, or hold message before responding.
- Why it's a problem: 10-15s of unexplained silence is indistinguishable from a dropped call; a real patient would hang up or start talking. The agent should give a hold cue ("let me check that, one moment") and/or respond faster. Recurring pattern — also seen as ~5s gap in transcript-03.
- Severity: High

### Agent barges in then aborts and restarts its own response

- Scenario: closed_day_booking
- Transcript: transcript-07.txt at [02:17]
- What happened: While the patient was still speaking, the agent cut in with "we don't have any available morn—", stopped mid-word, went silent, then restarted and delivered the full "no morning slots available" answer.
- Why it's a problem: Agent interrupts the caller and false-starts its own speech, producing a garbled overlap. Sounds broken and talks over the patient.
- Severity: Low

### Agent claims "no record of you" while retaining appointments across calls

- Scenario: new_appointment / reschedule / ambiguous_date (cross-call)
- Transcripts: transcript-02, transcript-04, transcript-08 at [02:55]
- What happened: The agent states at the start of each call that it has no record of the patient. But it clearly persists state across calls, an appointment created/discussed in an earlier call was still known in a later call.
- Why it's a problem: The "no record" greeting contradicts the agent's actual behavior; it does have records and remembers them. Misleading to the caller and inconsistent with its own state.
- Severity: Medium

### (LOW) No special handling for controlled-substance refill request

- Scenario: controlled_substance_refill
- Transcript: transcript-10.txt at [03:16]
- What happened: Patient requested an oxycodone (Schedule II) refill. The agent routed it via the same "I've submitted a request to the clinic support team" flow it used for a routine medication, with no acknowledgment that a controlled substance requires different handling.
- Why it's a problem: Ideally the agent would flag that controlled substances need the prescribing physician directly. Minor — it did not actually approve the refill, just forwarded it like any other.
- Severity: Low

### Agent interrupts the caller before they finish speaking

- Scenario: closed_day_booking, topic_switch, out_of_scope
- Transcripts: transcript-07 at [02:17], transcript-11 at [02:22], transcript-13 at [01:48] and [01:50]
- What happened: Across multiple calls the agent began speaking while the patient was still mid-sentence, cutting them off (in transcript-07 it also aborted and restarted its own response).
- Why it's a problem: Premature endpointing / aggressive barge-in talks over the caller and can cut off information the patient is still providing. Recurs across 3+ calls.
- Severity: Low
