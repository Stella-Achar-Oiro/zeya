# Migrating Zeya onto Open Chat Studio

Status: proposed · Target: `https://openchatstudio.co.ke/` (team `evarest`) · OCS reference commit `7df40d8a4`

## Summary

OCS takes over the WhatsApp channel, sessions/history, LLM calls, participants and
admin. Zeya keeps, **in this repository**, the safety-critical and study-critical code:
the danger-sign gate, the emergency message with Migori facility contacts, the
registration flow, and the CSV export adapter. These are written as OCS Python-node
sources under `ocs/`, tested here against the real OCS sandbox, and assembled into a
pipeline file by a build script. People do not hand-edit the pipeline in the UI.

```
Start → danger_gate (Python) → danger_router (Static Router, temp_state.danger_route)
          ├─ EMERGENCY (default) → emergency_response (Python, no LLM) → End
          └─ SAFE → registration (Python) → registration_router (Static Router, temp_state.registration_route)
                       ├─ REPLY (default) → End
                       └─ REGISTERED → llm (LLM, Gemini) → End
```

## What moves, what stays

| Zeya today | After migration |
|---|---|
| `whatsapp.py`, `webhook.py` | OCS WhatsApp channel |
| `conversation_handler.py` orchestration | the pipeline above |
| `conversation_handler.py` registration steps | `ocs/nodes/registration.py` (Python node) |
| `ai_engine.py` | OCS LLM node; prompt copied verbatim into `ocs/prompts/system_prompt.txt` |
| Redis history (6 turns, 24 h) | OCS node history, capped at 12 messages (6 turns); see changes below |
| `user_service.py`, `users.py` | OCS participants + participant data |
| `analytics_service.py`, React dashboard | OCS dashboard; `ocs/export_adapter.py` reproduces the analysis CSV |
| `danger_signs.py` | `ocs/nodes/danger_gate.py`, **patterns unchanged** |
| `health_facility_service.py` + DB table | static table built into `ocs/nodes/emergency_response.py` from `app/seeds/health_facilities.py` |
| Zeya Postgres (existing transcripts) | **stays**, read-only, until the study closes |

## The danger-sign gate (the four hard rules)

1. **Deterministic regex.** `danger_gate.py` holds the same 39 patterns as
   `danger_signs.py`, in the same order, with the same flags. It uses the same
   first-match-per-category loop. No LLM node appears before the router.
2. **Runs before the LLM.** It is the only node after Start, and the LLM is reachable
   only through the router's `SAFE` handle. Every message is gated, including
   registration messages. `EMERGENCY` is the router's *default* route, so a missing or
   unexpected value fails toward the emergency message, not the LLM. If the gate itself
   raises, the pipeline stops with an error and no LLM node runs.
3. **Not editable by non-engineers.** OCS cannot lock a single node. Pipeline edit
   rights come from the *Chatbot Admin* group (`pipelines: ALL`,
   `apps/teams/backends.py`). Study staff get *Chat Viewer* + *Annotation Reviewer*
   only. Engineers deploy the generated `ocs/build/pipeline.json` and never edit nodes
   in the UI. `ocs/check_drift.py` compares the live pipeline's node code with the
   repository and fails on any difference. Run it after every deploy and on a schedule.
   This is an operational control, not a technical lock, and is recorded as a residual
   risk.
4. **Version-controlled with tests.** The node source is a normal `.py` file here.
   `ocs/tests/test_danger_gate_parity.py` imports both the original module and the node.
   It asserts they return identical categories and keywords for every existing test
   message, a positive example for every individual pattern (39), and the negative
   corpus. All 8 categories are covered in English **and** Swahili.

### Changes needed to fit the Python-node constraint (structure only)

OCS runs node code with `exec(code, globals, locals)`. Module-level names land in
`locals`, so `main` cannot see them (verified against `python_execution.py`). So:

- `import re` and the pattern table moved **inside** `main`.
- The table is a list of `(category, [patterns])` pairs instead of a `dict`. Iteration
  order is the same (dicts preserve insertion order). `bleeding` is still checked first.
- `DangerSignResult` became plain values written to temp state
  (`danger_categories`, `danger_keywords`).

**No pattern string, flag or match rule changed.** The parity test compares each
compiled pattern's `.pattern` and `.flags` with the original. It fails if either
side drifts.

### No LLM on the emergency path

`emergency_response` is a Python node with no LLM call. The route test parses the
generated pipeline. It asserts that no node reachable from `EMERGENCY` is an LLM-type
node, and that every LLM node is reachable only through `SAFE`.

## Health facilities

The node has a **static table built in at build time**, generated from
`app/seeds/health_facilities.py`: verified, active, emergency-capable facilities sorted
by `display_priority`, top 5. This is the same filter as `get_emergency_facilities`.

Reasoning: the emergency path should have no runtime dependency (no database, no HTTP,
no participant-data lookup) that could fail. A participant-data copy would go stale for
people already enrolled. Changes to facilities go through code review, which suits
contact numbers that people rely on in an emergency. Today's fallback text is kept only
as a test fixture.

## LLM provider

**Decision: add a Google Gemini provider on the instance, using the existing Zeya API
key, and keep `gemini-3-flash-preview`. Do not switch to "Evarest OpenAI".**

- Zeya has used `gemini-3-flash-preview` since commit `70212c9` (2026-02-09), not
  `gemini-2.0-flash-exp` as the README says. Earlier rows have the older model in
  `conversations.ai_model_used`. Analysis should already treat 2026-02-09 as a model
  change point.
- Switching providers would be a second, larger change partway through the study:
  different model family, different Swahili quality, different length and tone. That
  hurts comparability with the data already collected. Keeping the model means the
  remaining differences are only in how the prompt is assembled (below).
- OCS lists `gemini-2.5-*` for the `google` provider, not `gemini-3-flash-preview`.
  Add it as a custom model on the provider. If the instance refuses, use
  `gemini-2.5-flash` and record it as a model change point in the study log.

## Methodological changes (for the study log)

These follow from the four hard rules or from OCS, and must be recorded with their
go-live date:

1. **No AI follow-up after an emergency message.** Today Zeya sends the emergency
   template, then a second Gemini reply. Rule 2 and the no-LLM emergency path remove the
   second reply. Danger-sign turns now get only the template.
2. **Danger signs are checked during registration and for people who declined.**
   Today those messages bypass detection. Now someone who types "bleeding" while
   registering gets the emergency message.
3. **Prompt assembly.** The system prompt, gestational-age guidance and Swahili or
   danger-sign context lines are copied verbatim. OCS sends history as chat turns, not
   as an inline "Recent conversation history" block. History length is 6 turns
   (12 messages). There is no 24-hour expiry; OCS sessions persist.
4. **Declined consent.** Today later messages are ignored without logging. Now they get
   a one-line reply saying YES re-enrols. The welcome text already promises this, but
   the old code never allowed it. Their messages are excluded from the export (below).

## Study data continuity

- **Existing transcripts are not migrated.** The Zeya database and
  `/api/v1/analytics/export/*` stay running, read-only, until the study closes. Nothing
  existing becomes unexportable.
- **New transcripts:** `ocs/export_adapter.py` turns the OCS chatbot transcript export
  into Zeya's exact `conversations_export.csv` columns (`study_id, study_group,
  direction, message_text, gestational_age, danger_sign, danger_keywords,
  response_time_ms, timestamp`):
  - `danger_sign` and `danger_keywords` come from message tags (`danger_sign:<category>`)
    and a `danger_keywords` tag that the gate writes.
  - `gestational_age` comes from the participant-data snapshot (`gestational_age_weeks`).
  - `response_time_ms` = AI message time − human message time.
  - `study_id` uses the same `STUDY_####` scheme over a combined set, with OCS
    participants linked to Zeya users by phone number.
  - Rows for participants without `consent_given` are dropped.
- Migrated participants are seeded into OCS participant data (consent, name, enrolment
  gestational age and date, study group, language) by `ocs/seed_participants.py`, so
  they skip registration again.

## Testing

All tests live in `ocs/tests/` and run with `make test-ocs`. They use the real OCS
`RestrictedPythonExecutionMixin` when `OCS_SOURCE` is set, and a pinned copy of it
otherwise.

- Gate parity with `danger_signs.py`, as above.
- Gate behaviour inside the sandbox: the route value, temp state and tags for all 8
  categories × {en, sw}, plus negatives.
- Pipeline structure: emergency path has no LLM; LLM is only behind `SAFE`; `EMERGENCY`
  is the default route; generated node code matches the files in the repository.
- Registration state machine, emergency message content (facilities present, both
  languages), export adapter columns.

## Rollout

Deploy the pipeline to a new OCS chatbot. Test it on the web channel with the test
corpus, then attach the WhatsApp number. Run `check_drift.py`. Zeya's webhook is
switched off at the same time the number moves. The Zeya backend stays up for export
only.
