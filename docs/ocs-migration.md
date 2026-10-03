# Migrating Zeya onto Open Chat Studio

Status: implemented, not deployed · Target: `https://openchatstudio.co.ke/` (team `evarest`) ·
OCS reference commit `7df40d8a4`

> **Go-live blocker:** the seed phone numbers for 4 of the 5 emergency facilities
> (`0722 123 456`, `0733 456 789`, `0744 567 890`, `0755 678 901`) look like
> placeholders. The emergency message sends them as they are, as Zeya does today.
> Verify them with Migori County Health before go-live.
> `test_facility_numbers_are_not_placeholders` is a strict xfail until then.
> The node is checked against the **seed file**, not the live `health_facilities`
> table, which admins can edit. Compare the node with production's table at the
> same time.

## Summary

OCS takes over the WhatsApp channel, sessions and history, LLM calls, participants and
admin. Zeya keeps, **in this repository**, the safety-critical and study-critical code:
the danger-sign gate, the emergency message with Migori facility contacts, the
registration flow, and the export adapter. These are written as OCS Python-node
sources under `ocs/nodes/`, tested here against the real OCS sandbox and engine, and
assembled into `ocs/pipeline/zeya_pipeline.json` by `ocs/build_pipeline.py`.

```
Start → danger_gate (Python) → danger_router (Static Router on temp_state.danger_route)
          ├─ output_0 EMERGENCY (default) → emergency_response (Python, no LLM) → End
          └─ output_1 SAFE → registration (Python) → registration_router (Static Router on temp_state.registration_route)
                                ├─ output_0 REPLY (default) → End
                                └─ output_1 REGISTERED → llm (LLM, Gemini) → End
```

**Why not `CodeNode → BooleanNode`, as first sketched.** `BooleanNode` is
`@deprecated_node` (`can_add=False`), so it cannot be added in the UI. Also, every OCS
router passes its *input* downstream (`from_router_output(..., state["last_node_input"])`).
So if the gate returned the category, the LLM would receive `"none"` instead of the
user's message. Instead, the gate returns the message unchanged and writes
`danger_route` to temp state. A `StaticRouterNode` routes on that value.

## What moves, what stays

| Zeya today | After migration |
|---|---|
| `whatsapp.py`, `webhook.py` | OCS WhatsApp channel (participant identifier = Meta `wa_id` = Zeya `whatsapp_id`) |
| `conversation_handler.py` orchestration | the pipeline above |
| `conversation_handler.py` registration steps | `ocs/nodes/registration.py` |
| `ai_engine.py` | OCS LLM node. Prompt copied verbatim to `ocs/prompts/system_prompt.txt`; `_build_context` ported into the registration node |
| Redis history (6 turns, 24 h) | OCS node history, `max_history_length` 12 messages |
| `user_service.py`, `users.py` | OCS participants + participant data (same field names as the `users` columns) |
| `analytics_service.py`, React dashboard | OCS dashboard; `ocs/export_adapter.py` reproduces the analysis CSV |
| `danger_signs.py` | `ocs/nodes/danger_gate.py`, **patterns unchanged** |
| `health_facility_service.py` + table | static table built into `ocs/nodes/emergency_response.py`, checked against `app/seeds/health_facilities.py` |
| Zeya Postgres (existing transcripts) | **stays**, read-only, until the study closes |

## The danger-sign gate (the four hard rules)

1. **Deterministic regex.** `danger_gate.py` contains the same 39 patterns as
   `danger_signs.py`, in the same order, with the same flags. It uses the same
   first-match-per-category loop. No LLM node is before the router.
2. **Runs before the LLM.** It is the only node after Start, and the LLM can only be
   reached through the router's `SAFE` handle. Every message is gated, including
   registration messages. `EMERGENCY` is the router's default route, so a missing or
   unexpected value goes to the emergency message, not the LLM. If the gate raises,
   OCS stops the pipeline (`CodeNodeRunError`) and no LLM node runs.
3. **Not editable by non-engineers.** OCS has no per-node lock. Pipeline edit rights
   come from the *Chatbot Admin* group (`pipelines: ALL`, `apps/teams/backends.py`).
   Study staff get *Chat Viewer* + *Annotation Reviewer* only. Engineers deploy the
   generated JSON and never edit nodes in the UI. `python -m ocs.check_drift live.json`
   compares the live pipeline with the repository: node set, edges, all Python code,
   router settings, prompt and model parameters. It exits 1 on any difference. Run it
   after every deploy and on a schedule. This is an operational control, not a
   technical lock, and remains a residual risk.
4. **Version-controlled with tests.** The node source is a normal `.py` file. The
   parity tests compare each pattern's string and flags with the original. They also
   prove each of the 39 patterns individually and assert identical categories and
   keywords for every test message, both languages, the negatives and the edge cases.

### What changed to fit the Python-node constraint (structure only)

OCS runs node code with `exec(code, globals, locals)`. Module-level names land in
`locals`, so `main` cannot see them (verified in both the pinned and real sandbox).

- `import re` and the pattern table moved **inside** `main`.
- The table is a list of `(category, [patterns])` pairs instead of a `dict`, in the
  same order.
- `DangerSignResult` became temp-state values: `danger_route`, `danger_categories`,
  `danger_keywords`.
- The pattern block was generated mechanically from the original source lines, not
  retyped.

**No pattern string, flag or match rule changed.**

Also found: the sandbox has no `_unpack_sequence_`, so `a, b = ...` fails at run time
inside a node. `for a, b in ...` works. The nodes avoid it, and a test pins the
constraint.

### Gaps in the existing patterns (not changed; needs clinical review)

Porting verbatim keeps these existing misses. The tests record them as edge cases:

- `blurred?` matches "blurre"/"blurred", not "blur" or "blurry".
- `\bconvulsion\b` and `\bseizure\b` miss the plurals "convulsions" and "seizures".
- `stopped?` and `passed?` miss "stop moving" and "pass out".

Fixing them changes matching behaviour. It should be a separate, clinically reviewed
change made to `danger_signs.py` and the node together. The parity tests enforce that
both change together.

### No LLM on the emergency path

`emergency_response` is a Python node with no LLM. The structural tests read the
generated pipeline as a graph. They assert that no LLM-type node is reachable from
`EMERGENCY` and that, with the `SAFE` edge removed, no LLM node is reachable from Start.
The engine test runs all 8 categories × {en, sw} through OCS's real `PipelineGraph` with
a recording fake LLM and asserts zero LLM calls.

## Health facilities

The node holds a **static table built in at build time**: the top 5 verified, active,
emergency-capable Migori facilities by `display_priority`. This is the same filter as
`get_emergency_facilities`. The test rebuilds Zeya's message from the seed data with
`format_emergency_message` and requires byte-for-byte equality in both languages.

Reasoning: the emergency path should have no runtime dependency (database, HTTP,
participant-data lookup) that could fail. A participant-data copy would go stale for
people already enrolled. Changes to facility contacts go through code review.

The tests only prove the node matches the seed file. Production's table may have been
edited through the admin API since seeding. Before go-live, compare the node with
`SELECT name, phone_number, emergency_line FROM health_facilities WHERE is_active AND
has_emergency_services AND is_verified AND lower(county) = 'migori' ORDER BY
display_priority, name LIMIT 5`, and update the seed file and the node if they differ.

## LLM provider

**Decision: add a Google Gemini provider on the instance, using the existing Zeya
key, and keep `gemini-3-flash-preview`. Do not switch to "Evarest OpenAI".**

- The config default became `gemini-3-flash-preview` in commit `70212c9` (2026-02-09).
  The README still says `gemini-2.0-flash-exp`. That date is when the default changed,
  not proof of what production ran: deployments read `GEMINI_MODEL` from their own
  `.env`. **Check production before relying on it:** `SELECT ai_model_used,
  min(created_at), max(created_at), count(*) FROM conversations WHERE
  message_direction = 'outgoing' GROUP BY 1 ORDER BY 2`. A local development database
  holds only test rows (all `gemini-3-flash-preview`, 2026-02-09), so it cannot confirm
  this.
- Switching provider partway through the study changes model family, Swahili quality,
  length and tone. That is a much larger methodological change than staying on Gemini.
- OCS lists `gemini-2.5-*` for the `google` provider, not `gemini-3-flash-preview`.
  Add it as a custom model. If that is impossible, use `gemini-2.5-flash` and record a
  model change point.
- **Temperature is pinned to 1.0.** Zeya called Gemini with no generation config, so it
  used the model default (1.0 for Gemini 3). OCS would otherwise default to 0.7.
  Confirm the default for the exact model at deploy time.

## Methodological changes (for the study log, with go-live date)

1. **No AI follow-up after an emergency message.** Zeya sends the template and then a
   second Gemini reply. The no-LLM emergency path removes the second reply, and those
   turns no longer enter LLM history.
2. **Danger signs are checked during registration.** Previously those messages skipped
   detection.
3. **Prompt assembly.** The system prompt, gestational-age guidance and Swahili context
   line are verbatim. History is sent as chat turns instead of an inline "Recent
   conversation history" block. It is still capped at 6 turns, with no 24-hour expiry.
   The "ALERT: Danger sign keywords detected" context line is gone, because it was only
   used for the removed follow-up.
4. **Declined consent.** Zeya deactivated the user and ignored them afterwards. Now
   `consent_declined` is recorded and the next message gets the consent question again,
   with the same wording as before. It is cleared if they later say YES.
5. **People who never consented are left out of the export.** Zeya's export kept their
   logged messages, such as consent-step replies from people who then declined. The
   adapter drops every row for participants whose latest data lacks
   `consent_given: true`.
6. **`response_time_ms` is measured differently.** Zeya timed from webhook processing
   to after both WhatsApp sends, so it included WhatsApp API latency and, on danger
   turns, the follow-up Gemini call. OCS-era values are the gap between the stored
   human and AI message timestamps, so the two eras are not directly comparable.
7. **Messages with no text.** Zeya ignored them (`if not message.text: return`). In
   OCS they reach the pipeline: an empty message at the name step asks for the name
   again, and voice notes may be transcribed by OCS and then gated like any text.
   Check the channel's media settings at deploy time.

## Study data continuity

- **Existing transcripts are not migrated.** The Zeya database and
  `/api/v1/analytics/export/*` stay running, read-only, until the study closes.
- **New transcripts:** `ocs/export_adapter.py` converts the OCS export to Zeya's exact
  9 columns and value formats:
  - Danger flags and keywords go on the outgoing row only, from gate tags. Keywords are
    in Zeya's category order; the tag holds the category because OCS exports tags
    alphabetically. Whitespace inside a keyword is collapsed and the tag is capped at
    100 characters (the OCS tag limit).
  - `gestational_age` is the age at message time.
  - `response_time_ms` is the AI time minus the human time (see change 6). Each reply is
    paired with the human message just before it in the same session. The export's
    `Trace ID` is not used, because OCS leaves it blank unless an external tracing
    provider is configured.
  - It drops what Zeya never logged: the first-contact turn, and registration replies.
    Registration answers are kept.
  - It drops participants who never consented (see change 5).
  - `study_id` uses Zeya's `STUDY_####` numbering, linked by `whatsapp_id`. OCS-only
    participants sort after every Zeya UUID, so existing IDs are unchanged. As in Zeya,
    numbering is over the unfiltered set.
- `ocs/seed_participants.py` imports existing users into OCS participant data, so they
  skip registration. It leaves out consented users whom an admin deactivated and lists
  them for a study-team decision. OCS exposes `participant.name` as `name`, so
  registration tracks the name step with `name_collected`.

## Testing

| Suite | Command | What it proves |
|---|---|---|
| Unit (pinned sandbox) | `make test-ocs` | parity, per-pattern, bilingual routing, registration, emergency text, graph structure, export, drift, seeding |
| Unit (real OCS sandbox) | `OCS_SOURCE=<checkout> make test-ocs` | the same, run in OCS's `RestrictedPythonExecutionMixin` |
| Engine | `DATABASE_URL=… make test-ocs-engine OCS_SOURCE=<checkout>` | pipeline validates; 16 danger messages → emergency with 0 LLM calls; SAFE → exactly one LLM call with the Zeya prompt and context; drift check passes on what OCS stores |

At the time of writing: 283 passed + 1 strict xfail (the placeholder numbers), in
both sandbox modes; 26 passed in the engine suite against a throwaway
`pgvector/pgvector:pg16` database. Install with `pip install -r ocs/requirements-dev.txt`.

## Rollout

1. Verify the facility numbers (blocker above).
2. On the instance: add the Gemini provider and the `gemini-3-flash-preview` custom
   model. Create the chatbot and pipeline. Restrict roles as in rule 3.
3. Build with the instance's ids:
   `python -m ocs.build_pipeline --llm-provider-id N --llm-provider-model-id M > deploy.json`.
   Load it into the pipeline (`POST /a/evarest/pipelines/data/<id>/`). Publish a version.
4. Import `seed_participants.py` output. Test on the web channel with the corpus in
   `ocs/tests/danger_corpus.py`. Run
   `python -m ocs.check_drift live.json --llm-provider-id N --llm-provider-model-id M`.
   The expected ids are required, so a model switched in the UI shows up as drift.
5. Move the WhatsApp number to OCS and switch Zeya's webhook off at the same time.
   Record the date in the study log with the methodological changes above. Keep the
   Zeya backend up for export only.
