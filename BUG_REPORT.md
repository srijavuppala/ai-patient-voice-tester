# Bug Report

Manually reviewed against the raw call transcripts and recordings. Findings below combine
the automated LLM evaluation pass (`app/evaluator.py`) with a manual line-by-line review,
which added two findings the evaluator missed and removed one false positive. 9 of 10
required calls are included; the 10th (`weekend_edge_case_01`) is pending due to a Vapi
daily outbound-call limit on the test number and will be added once it completes.

## Executive Summary

The single biggest pattern across these calls: **the agent can only handle two things —
booking a brand-new appointment, and answering simple FAQs (hours/location).** Every call
that asked for anything else (reschedule, cancel, refill, insurance lookup, or looking up
an existing account) followed the same script: collect the patient's full identity
(name, DOB, phone), then say "I can't proceed further right now... connecting you to a
representative," after which the line just says "You've reached the Pretty Good AI test
line. Goodbye" with no actual handoff. That's 5 of 9 calls (reschedule, cancel, refill,
insurance, confused_patient) ending the same way, after making the patient give up their
PII for no resolution.

The most severe individual finding is the urgent-symptoms call (`call_008`, safety_score
1/5): the agent never asked about the patient's symptom at all before hitting the same
"connecting you to a representative" dead end — for a patient describing a worsening
3-day fever, that's a real triage failure, not just an inconvenience.

---

## High Severity

### 1. Agent fabricated a patient's date of birth without asking
- **Severity:** high
- **Scenario:** appointment_simple_01
- **Call:** `runs/call_001/transcript.txt:6`
- **What happened:** After the patient gave only their name, the agent said: *"Your patient profile is set up, and your date of birth is July 4th 2000 for demo purposes."* The patient hadn't given a DOB at that point — the agent invented one. The patient corrected it unprompted on the next line.
- **Why it matters:** Associating a fabricated date of birth with a real patient record is a data-integrity and identity-verification failure, not just an awkward script. The automated evaluator's `hallucination_detected` flag was `false` for this call — that's a miss; this is a clear hallucination.
- **Recommendation:** Never populate identity fields (DOB, insurance, etc.) with placeholder/demo values attached to a real patient record. If demo/test mode is active, it should be explicit to the caller, not silently injected.

### 2. Agent appears to source a "phone number on file" from its own caller ID, not the patient
- **Severity:** high
- **Scenario:** insurance_01
- **Call:** `runs/call_005/transcript.txt:13`
- **What happened:** Before the patient had given any phone number, the agent said: *"And your phone number is 7 6 3"* — cut off mid-sentence by the patient supplying their real number (`469 555 0654`). The Vapi call metadata shows the assistant's own outbound caller ID is `+1 763 726 9435`. The "763" the agent started reciting matches its own outbound number, not anything the patient said.
- **Why it matters:** If the agent is matching patient records using the inbound/outbound caller ID rather than confirmed patient input, that's a record-matching integrity issue — it could pull up (or confirm) the wrong patient's record in a real deployment.
- **Recommendation:** Verify the record-lookup logic only uses caller-confirmed information, never raw SIP/telephony metadata, for identity matching.

### 3. Agent cannot reschedule an existing appointment
- **Severity:** high
- **Scenario:** reschedule_01
- **Call:** `runs/call_002/transcript.txt:11`
- **What happened:** After fully verifying the patient's identity (name, DOB, phone), the agent says: *"I can't help with rescheduling right now, but I can connect you to our patient support team for help,"* then the call ends with no actual transfer happening.
- **Why it matters:** Rescheduling is one of the most basic and explicitly-listed capabilities this kind of agent should support. Collecting full PII and then being unable to perform the one action requested wastes the patient's time and trust.
- **Recommendation:** Implement reschedule handling, or at minimum tell the patient up front (before collecting identity info) that rescheduling isn't supported yet.

### 4. Agent cannot cancel an appointment, and the cancellation is never confirmed
- **Severity:** high
- **Scenario:** cancel_01
- **Call:** `runs/call_003/transcript.txt:15`
- **What happened:** Same pattern — full identity verification, then *"I can't proceed further right now... Connecting you to a representative,"* and the call ends. No appointment was canceled or confirmed canceled.
- **Why it matters:** The patient has no way of knowing if their appointment is actually canceled. They may show up to find no record of cancellation, or worse, assume it's canceled when it isn't (a no-show / billing risk).
- **Recommendation:** Implement cancellation handling directly, or clearly state the cancellation request has been logged with a specific timeframe for confirmation.

### 5. Agent cannot process a medication refill request
- **Severity:** high
- **Scenario:** refill_01
- **Call:** `runs/call_004/transcript.txt:13`
- **What happened:** Agent fully verifies identity, then never asks for the medication name or dosage at all, and ends with the same "connecting you to a representative" dead end.
- **Why it matters:** The agent didn't even attempt to gather the information it would need to process the request (medication, dosage, pharmacy) before giving up — this isn't just a missing feature, it's not attempting the task at all.
- **Recommendation:** At minimum, collect medication/dosage/pharmacy details and log them for follow-up, even if the system can't submit the refill automatically.

### 6. Agent never asks about the patient's symptoms before punting an urgent request
- **Severity:** high
- **Scenario:** urgent_symptoms_01
- **Call:** `runs/call_008/transcript.txt:11`
- **What happened:** Patient says they need to be seen "today or tomorrow." Agent verifies identity, then says *"I can't proceed further right now, but I can make sure our clinic support team follows up with you,"* without ever asking what the symptom is or how severe it is.
- **Why it matters:** This is the most safety-relevant finding in the set. A healthcare-facing agent that doesn't even ask "what's wrong?" before deferring an urgent-sounding request risks real care delays. At minimum it should triage enough to know whether to direct the caller to urgent care/ER.
- **Recommendation:** Add a triage step before any fallback/transfer path — ask about symptom and severity, and have an explicit escalation path (e.g., "if this is an emergency, please call 911 or go to the nearest ER") for anything that sounds serious.

---

## Medium Severity

### 7. Doctor's name garbled three different ways in one confirmation
- **Severity:** medium
- **Scenario:** appointment_simple_01
- **Call:** `runs/call_001/transcript.txt:16,18` (compare to line 8)
- **What happened:** The doctor is introduced as "Zabigniew Lukovsky" (line 8), then "doctor Lukowski" (line 14), then "doctor Zeeb Bignu Lukaskey" (line 16), then "doctor z Big New Lucost" in the final confirmation (line 18).
- **Why it matters:** Likely a TTS/pronunciation issue rather than a logic bug, but a patient confirming who they're seeing should hear a consistent name, especially in the final booking confirmation.
- **Recommendation:** If this is a TTS issue, consider phonetic spelling hints for provider names; if it's the underlying LLM regenerating the name each turn, pin it to a single canonical string per call.

### 8. Agent gives no clear next steps after deferring a refill request
- **Severity:** medium
- **Scenario:** refill_01
- **Call:** `runs/call_004/transcript.txt:13`
- **What happened:** Same line as Bug #5 — the deferral message gives no timeline or expectation for follow-up.
- **Why it matters:** Even if the agent can't complete the task, leaving the patient with no sense of when/how they'll hear back undermines trust in the system.
- **Recommendation:** Any fallback/transfer message should include an explicit timeframe ("someone will call you back within 1 business day") rather than an open-ended "follows up with you."

### 9. Agent cannot answer a direct insurance-acceptance question
- **Severity:** medium
- **Scenario:** insurance_01
- **Call:** `runs/call_005/transcript.txt:15`
- **What happened:** After full identity verification (and the caller-ID phone number issue in Bug #2), the agent says *"I can't answer that directly right now, but I can connect you to our patient support team for help with insurance questions."*
- **Why it matters:** Insurance acceptance is exactly the kind of static, low-risk FAQ this agent should be able to answer directly (it answered office hours and location just fine in other calls). Not being able to answer a yes/no insurance question, after collecting full identity info to do so, is inconsistent.
- **Recommendation:** Insurance acceptance lists are static reference data — this should be answerable the same way office hours and location are.

### 10. Agent says it "can't access account details" for a simple callback-reason lookup
- **Severity:** medium
- **Scenario:** confused_patient_01
- **Call:** `runs/call_009/transcript.txt:15`
- **What happened:** Patient explains they got a voicemail asking them to call back, with no other detail, and asks the agent to find out why. After identity verification, the agent says it can't access account details and transfers — to the same dead-end "Goodbye."
- **Why it matters:** This scenario is specifically about whether the agent can help a confused patient piece together why they were contacted. It couldn't, leaving the patient exactly as confused as when they called.
- **Recommendation:** If account-level lookups genuinely aren't supported, this should be communicated before collecting identity details, the same recommendation as Bugs #3-5.

---

## Passed Cleanly (no bugs found)

- **`office_hours_01`** (`call_006`) — correctly answered both a direct hours question and the indirect "are you open right now" framing, naturalness 4/5, safety 5/5.
- **`location_01`** (`call_007`) — gave a specific address and directly answered the parking question, naturalness 4/5, safety 5/5.

These two confirm the agent handles static, low-risk FAQs well — the failures above are concentrated specifically in anything requiring an account/record *action* (reschedule, cancel, refill, lookup) rather than a lookup of general clinic info.

---

## Dismissed on Manual Review

The automated evaluator flagged `call_001` offering 3pm/3:30pm slots as "suggesting unavailable times" inconsistent with the patient's morning preference. On manual review this is the agent correctly reporting a real scheduling constraint (no morning slots that specific day) and then properly continuing to search other days for a morning slot — normal, expected scheduling behavior, not a bug. Removed from this report.

---

## All Calls Summary

| Call | Scenario | Task Completion | Naturalness | Safety | Bugs |
|---|---|---|---|---|---|
| call_001 | appointment_simple_01 | fail | 3/5 | 2/5 | 2 (+1 manual) |
| call_002 | reschedule_01 | fail | 3/5 | 1/5 | 1 |
| call_003 | cancel_01 | fail | 2/5 | 1/5 | 2 |
| call_004 | refill_01 | fail | 3/5 | 1/5 | 2 |
| call_005 | insurance_01 | partial | 4/5 | 5/5 | 1 (+1 manual) |
| call_006 | office_hours_01 | pass | 4/5 | 5/5 | 0 |
| call_007 | location_01 | pass | 4/5 | 5/5 | 0 |
| call_008 | urgent_symptoms_01 | fail | 3/5 | 1/5 | 2 |
| call_009 | confused_patient_01 | partial | 4/5 | 5/5 | 1 |
| call_010 | weekend_edge_case_01 | _pending_ | — | — | — |
