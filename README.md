# Agentic Healthcare Assistant for Medical Task Automation

## Overview

This capstone project demonstrates an agentic healthcare assistant that coordinates structured patient data, deterministic workflow tools, retrieval-augmented generation (RAG), evaluation, memory, and a Streamlit user interface.

The primary demonstration scenario is:

> Book a nephrologist for a 70-year-old father with Chronic Kidney Disease (CKD) and summarize his current treatment.

The system is designed as a proof of concept for medical task automation. It uses synthetic/mock data and educational knowledge and is not intended for clinical use.

---

## Core Design Principle

The application separates **interpretation, execution, knowledge retrieval, generation, and evaluation** rather than assigning all responsibilities to a language model.

The language model is used to interpret natural-language requests and generate bounded summaries. Deterministic application components execute operational tasks such as patient lookup, medical-record retrieval, doctor selection, and appointment booking.

The system follows this authority hierarchy:

1. **Structured workflow data is authoritative.**
2. **Retrieved educational knowledge is supplemental and non-authoritative.**
3. **Generated model output must remain grounded in the supplied evidence.**

Retrieved information cannot override patient-specific diagnoses, medications, treatments, selected doctors, appointment details, or other authoritative workflow state.

---

## Architecture

The application is organized into several cooperating layers.

### 1. Request Interpretation

Natural-language requests are converted into structured intent using an OpenAI model and Pydantic schemas.

Example request:

```text
Book a nephrologist for my 70-year-old father with CKD and summarize his current treatment.
```

The interpretation layer identifies information needed by the downstream workflow, including the patient, requested specialty, and appointment purpose.

This creates a structured interface between probabilistic language interpretation and deterministic application execution.

---

### 2. Deterministic Workflow Tools

Operational actions are executed using deterministic Python tools rather than allowing the language model to directly modify application state.

Key capabilities include:

- patient lookup
- medical-record retrieval
- doctor search
- appointment booking
- appointment-state tracking

This design constrains the language model's operational authority and keeps important workflow actions inspectable.

---

### 3. LangGraph Orchestration

LangGraph coordinates the execution sequence and maintains structured workflow state.

The primary workflow is:

```text
START
  |
  v
Retrieve Patient
  |
  v
Retrieve Medical Record
  |
  v
Retrieve Educational Knowledge
  |
  v
Find Matching Doctors
  |
  v
Book Appointment
  |
  v
END
```

Structured Pydantic models represent entities such as:

- Patient
- MedicalRecord
- Doctor
- Appointment
- RequestIntent
- RetrievedDocument
- WorkflowState

The graph therefore provides explicit orchestration while deterministic tools remain responsible for operational actions.

---

### 4. Retrieval-Augmented Generation

The application uses OpenAI embeddings and FAISS vector search to retrieve supplemental educational information relevant to the workflow.

The demonstration knowledge base contains synthetic educational material related to:

- Chronic Kidney Disease
- CKD monitoring
- nephrology

Retrieved documents include provenance information such as title, source name, source type, source URL when available, and content.

Retrieved knowledge is explicitly treated as **non-authoritative educational context**.

It cannot modify, infer, or override patient-specific medical facts stored in structured workflow state.

---

## Safety and Authority Boundaries

The response-generation layer operates under explicit authority and safety constraints.

The assistant must not use retrieved educational material to:

- create new patient diagnoses
- modify existing diagnoses
- start or stop medications
- change medications
- adjust medication doses
- create new patient-specific treatments
- override structured medical information
- change doctor selection
- change appointment information
- convert general educational information into personalized treatment guidance

When supplemental retrieved knowledge is provided, the response-generation contract requires a clearly identified:

```text
Supplemental Educational Context
```

section.

This separates authoritative patient and workflow information from general educational material.

---

## Evaluation Architecture

The application uses two complementary evaluation layers before a generated response is accepted for memory.

### Deterministic Evaluation

The deterministic evaluator checks explicit application requirements and structured facts.

Evaluation includes checks for:

- user request presence
- generated response presence
- workflow errors
- successful appointment creation
- retrieval completion
- provenance completeness
- required patient facts
- required medical-record facts
- selected doctor information
- appointment information
- structured identifier contradictions
- appointment-time consistency
- safety-boundary violations
- presence of supplemental educational context when retrieval occurs
- grounding-context availability

The appointment-time evaluator tolerates legitimate presentation differences while still rejecting incorrect appointment times.

The design principle is:

> Evaluation should inspect the state of the system, not just the appearance of the output.

---

### Semantic Faithfulness Evaluation

A secondary model-assisted evaluator assesses whether the generated response remains faithful to the evidence supplied by the application.

The semantic evaluator examines:

- structured claim support
- retrieved-knowledge support
- authority-boundary compliance
- unsupported patient-specific claims
- clinical personalization
- retrieval relevance
- overall semantic faithfulness

The semantic evaluator is evidence-bounded. It is instructed to judge the supplied workflow state and retrieved documents rather than substitute external medical knowledge.

The semantic layer supplements rather than replaces deterministic evaluation.

---

## Evaluation-Gated Memory

The application uses patient-specific, versioned persistent memory for validated interactions.

A generated response is accepted into memory only when both evaluation gates pass:

```text
Deterministic Evaluation = PASS
AND
Semantic Evaluation = PASS
```

This prevents a response that fails either evaluation layer from automatically becoming trusted conversational context.

The application also supports cross-turn use of validated memory.

For supported narrow follow-ups, the application performs an explicit
patient-scoped lookup before constructing the LLM prompt. The prompt receives
only one relevant evaluation-approved turn and includes provenance fields for
the requested patient ID, stored patient ID, memory source, validation status,
last specialty, and last appointment ID. A mismatched patient ID, unrelated
memory turn, unsupported follow-up, or missing memory prevents memory context
from entering the prompt.

Patient-memory decisions are also projected into a metadata-only audit trace.
Each UTC-timestamped event records the patient ID, `READ`, `WRITE`, or `SKIP`
action, outcome, provenance, validation basis, reason code, and bounded turn
count. The event schema forbids request and response content. Valid events are
appended to `logs/memory_events.jsonl`, included with full pipeline results,
and displayed in the Streamlit Workflow Diagnostics section.

Example follow-up:

```text
What time is his appointment?
```

Validated memory is saved atomically to a bounded local JSON store and reloaded
when the application starts. The path defaults to `data/patient_memory.json`
and can be overridden with `PATIENT_MEMORY_STORE_PATH`. This is the capstone
PoC persistence boundary; production clinical-memory infrastructure remains
outside the project scope.

---

## Adversarial Testing

The project uses positive and negative controls to test whether the evaluation architecture can detect important failure conditions.

Tested conditions include:

- unsafe medication-management language
- contradictory structured identifiers
- missing required patient facts
- incorrect medication dosage
- irrelevant retrieved knowledge
- unsupported patient-specific treatment assertions
- incorrect appointment-time representations

These tests are intended to demonstrate that plausible-looking language is not automatically treated as correct output.

The application evaluates the relationship between generated output, authoritative state, retrieved evidence, and defined safety boundaries.

---

## Streamlit Interface

The Streamlit application provides an interactive demonstration and observability layer for the capstone.

The interface exposes information including:

- healthcare request input
- patient workflow summary
- medical-record information
- selected doctor
- appointment details
- retrieved sources
- deterministic evaluation status
- semantic evaluation status
- memory acceptance
- workflow diagnostics
- interpreted intent
- workflow state

The interface is designed to expose important system behavior and evidence rather than hiding the workflow behind a single chatbot response.

---

## Verified Capstone Scenario

The final production regression for the primary capstone scenario produced:

```text
Deterministic Evaluation: PASS
Semantic Evaluation: PASS
Accepted for Memory: YES
```

The verified appointment state included:

```text
Doctor: Sarah Chen
Specialty: Nephrology
Appointment Time: 2026-09-02 09:00
Status: scheduled
```

This validates the integrated path from request interpretation through deterministic execution, retrieval, bounded response generation, evaluation, and memory acceptance.

---

## Repository Structure

```text
Agentic_Healthcare-Assistant/
├── app/
│   ├── agents/
│   │   ├── healthcare_graph.py
│   │   ├── request_interpreter.py
│   │   ├── response_synthesizer.py
│   │   └── assistant_pipeline.py
│   ├── evaluation/
│   │   ├── pipeline_evaluator.py
│   │   ├── pipeline_logger.py
│   │   └── semantic_faithfulness_evaluator.py
│   ├── memory/
│   │   └── patient_memory.py
│   ├── models/
│   ├── retrieval/
│   │   ├── embeddings.py
│   │   ├── faiss_index.py
│   │   └── knowledge_base.py
│   ├── tools/
│   └── ui/
│       └── streamlit_app.py
├── data/
│   └── mock_data.py
├── logs/
├── notebooks/
├── tests/
│   ├── test_cross_turn_memory.py
│   ├── test_patient_memory.py
│   ├── test_pipeline_integration.py
│   └── test_semantic_faithfulness.py
├── main.py
├── README.md
└── requirements.txt
```

---

## Installation

### 1. Create a virtual environment

From the project root:

```powershell
python -m venv .venv
```

### 2. Activate the virtual environment

In Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and define the required OpenAI API key.

The `.env` file and API credentials must not be committed to source control.

---

## Run the Application

From the project root with the virtual environment activated:

```powershell
python -m streamlit run app/ui/streamlit_app.py
```

Streamlit will provide a local URL for the application.

Using `python -m streamlit` also avoids reliance on direct execution of the Streamlit launcher in environments where application-control policies restrict executable launchers.

---

## Testing

The repository includes tests for major application capabilities.

Examples include:

```text
tests/test_patient_memory.py
tests/test_cross_turn_memory.py
tests/test_pipeline_integration.py
tests/test_semantic_faithfulness.py
```

Testing covers both successful operation and selected adversarial failure conditions.

The final integrated Streamlit regression is also used to verify the complete application path.

---

## Logging and Observability

Pipeline execution is logged for inspection.

The application exposes diagnostic information including:

- deterministic evaluation details
- semantic evaluation details
- workflow state
- interpreted intent
- workflow errors
- retrieved sources
- memory status

This supports failure isolation and provides evidence about why a response was accepted or rejected.

---

## Reproducibility

The project includes a frozen `requirements.txt` generated from the validated Python environment.

This captures the dependency versions used during final capstone validation and supports recreation of the development environment.

Secrets remain separate from the dependency and source-code layers.

---

## Known Limitations

This project is a high-fidelity proof of concept rather than a production clinical application.

Current limitations include:

- synthetic/mock patient and provider data
- synthetic educational retrieval content
- no production EHR integration
- no production scheduling API
- no persistent database-backed memory
- no production authentication or authorization layer
- no clinical deployment validation
- no production security certification
- evaluation logic remains tuned to the demonstrated capstone workflow
- semantic evaluation can exhibit diagnostic-field classification inconsistencies even when the overall evaluation correctly rejects an invalid response

The project does not demonstrate production healthcare interoperability, clinical validation, or real-world patient-data governance.

---

## Engineering Interpretation

The capstone demonstrates capabilities relevant to AI enablement and forward-deployed engineering, including:

- structured interface design
- deterministic and probabilistic system separation
- agentic workflow orchestration
- retrieval integration
- authority-boundary design
- prompt-contract design
- state management
- failure isolation
- evaluation architecture
- adversarial testing
- observability
- evaluation-gated memory
- dependency management
- reproducibility
- production-style debugging

Several engineering principles emerged during implementation:

> Retrieval capability becomes application capability only when retrieved context is integrated into generation with explicit authority boundaries.

> Component contract changes should be followed by component verification, downstream-consumer verification, and integration testing.

> Syntax PASS does not equal Runtime PASS, Functional PASS, or Requirement Closure.

> Representation tolerance should not become factual tolerance.

## Appointment-Booking Success Metric

The Streamlit Operational Performance panel calculates a reproducible
appointment-booking success rate from persisted tool-execution events:

`successful book_appointment executions / book_appointment attempts`

Only `TOOL_EXECUTION` events with a `SUCCESS` or `FAILURE` outcome count as
attempts. `TOOL_SKIPPED` planning outcomes are excluded from the denominator,
and a zero-attempt history displays `N/A` rather than a misleading percentage.

---

## Disclaimer

This application uses synthetic data and educational content for demonstration purposes only.

It is not a medical device, clinical system, treatment recommendation engine, or substitute for qualified medical care.

It should not be used to make real-world patient-care decisions. 
