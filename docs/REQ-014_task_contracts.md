# REQ-014 Agent Task Contracts

## Contract standard

Every agentic task declares:

1. Task purpose
2. Structured input
3. Structured output
4. Validation rule
5. Failure behavior
6. Provenance requirement

## Contract matrix

| Task | Structured input | Structured output | Validation | Failure behavior | Provenance |
|---|---|---|---|---|---|
| Request interpretation | Raw healthcare request text | `RequestIntent` | Required intent fields and patient identifier are present | Return structured interpretation failure; do not execute workflow | Original user request |
| Patient retrieval | Patient identifier | `Patient` or not-found result | Returned patient ID matches requested ID | Return not-found result; do not continue with mismatched patient | Patient data store |
| Medical-record retrieval | Patient identifier | `MedicalRecord` or not-found result | Record patient ID matches requested patient | Return not-found result; preserve patient scope | Medical-record store |
| Doctor search | Specialty and availability criteria | Candidate doctor list | Specialty and availability match request | Return empty candidate result; do not invent provider | Doctor data store |
| Appointment booking | Patient, doctor, date/time, specialty | `Appointment` or booking failure | Required booking fields and outcome are present | Return explicit booking failure; do not claim success | Appointment tool result |
| Response synthesis | Workflow state, retrieved facts, appointment result | Structured response summary | Claims remain bounded by authoritative workflow state | Return synthesis failure or bounded response | Workflow state and retrieved records |
| Semantic evaluation | Response text and supplied evidence | `SemanticFaithfulnessResult` | Structured result schema validates evaluator output | Return evaluator failure/uncertain status | Supplied evidence only |
| Memory decision | Workflow result and evaluation results | Memory acceptance decision | Deterministic and semantic gates both pass | Skip memory write and record reason | Evaluation outputs and patient scope |
| Response precision | Persisted semantic-evaluation records | `ResponsePrecisionResult` | Supported claims divided by total verifiable claims | Return `N/A` when no verifiable claims exist | Persisted pipeline evaluation log |

## Closure evidence

- Contract artifact reviewed against the active agent, tool, evaluator, and memory modules.
- Each contract identifies input, output, validation, failure, and provenance boundaries.
- Existing workflow behavior is preserved.
- No patient-memory data is changed by this artifact.
