# Feature Specification: Project Documentation

**Feature Branch**: `001-add-project-docs`
**Created**: 2026-03-11
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quick Start Guide (Priority: P1)

A new developer or user arrives at the project with no prior context and needs to understand it quickly enough to run it locally and make their first API requests. By reading the README they can get the full system running and tested.

**Why this priority**: This is the most critical entry point — without a solid introduction, no one can use or contribute to the project.

**Independent Test**: Can be fully tested by following only the README from a clean environment and verifying the system starts correctly and accepts requests.

**Acceptance Scenarios**:

1. **Given** a developer with no prior knowledge of the project, **When** they read the README and follow the setup instructions, **Then** they can bring up all services and successfully perform a document ingest and a query without errors.
2. **Given** the system is running, **When** the user navigates to the interactive API documentation URL, **Then** they can see all endpoints listed with input and output examples.
3. **Given** incomplete or missing setup instructions, **When** the user attempts to bring up the project, **Then** they encounter errors with no guidance — this scenario represents a documentation failure.

---

### User Story 2 - API Endpoint Documentation (Priority: P2)

An API consumer (developer, system integrator, or data scientist) needs to know exactly how to call each endpoint, what parameters to send, and what to expect in return, including error cases.

**Why this priority**: The API is the main product of the project — its documentation defines how external systems integrate with it.

**Independent Test**: Can be fully tested by verifying that each documented endpoint has a complete contract (request, response, errors) and that the provided examples work correctly.

**Acceptance Scenarios**:

1. **Given** the API documentation, **When** the user looks up the `/ingest` endpoint, **Then** they find: accepted file types (PDF/TXT), request format, success response, and possible error responses.
2. **Given** the API documentation, **When** the user looks up the `/query` endpoint, **Then** they find: request parameters, response structure (answer + source chunks), and an explanation of the returned quality metrics.
3. **Given** the API documentation, **When** the user looks up the `/health` endpoint, **Then** they find the response structure and what each field indicates (Ollama status, ChromaDB status).

---

### User Story 3 - Architecture Documentation (Priority: P3)

A developer contributing to or maintaining the project needs to understand how the components relate to each other: the web framework, the vector store, the local LLM engine, the experiment tracker, and the evaluation system.

**Why this priority**: Essential for maintenance and contributions, but the project can be used without this level of detail.

**Independent Test**: Can be tested by verifying that a developer can identify where to make a specific change (e.g., swapping the LLM model, adjusting chunk size) by reading only the architecture documentation, without opening source code.

**Acceptance Scenarios**:

1. **Given** the architecture documentation, **When** the developer needs to understand the ingestion flow, **Then** they find a clear description of the pipeline: upload → extraction → chunking → embedding → storage.
2. **Given** the architecture documentation, **When** the developer needs to understand the query flow, **Then** they find the full sequence: question → embedding → vector search → answer generation → evaluation → metric logging.
3. **Given** the environment variable documentation, **When** the developer wants to change the LLM model, **Then** they know which variable to change and what values are supported.

---

### User Story 4 - Configuration and Models Documentation (Priority: P3)

A system operator needs to understand all available environment variables, the supported models, and the available Docker profiles to adapt the system to their environment without modifying code.

**Why this priority**: Enables the system to be adapted to different environments and use cases (CPU, GPU) without requiring code changes.

**Independent Test**: Can be tested by verifying that every variable in `.env.example` is documented and that the Docker profile instructions (CPU/GPU) work when followed alone.

**Acceptance Scenarios**:

1. **Given** the configuration documentation, **When** the operator reads about environment variables, **Then** each variable has: name, description, default value, and a usage example.
2. **Given** the model documentation, **When** the operator wants to change the generation model, **Then** they find the list of tested models and instructions for switching.
3. **Given** the Docker profile documentation, **When** the operator wants to use GPU acceleration, **Then** they find clear instructions for the CPU, NVIDIA, and AMD profiles.

---

### Edge Cases

- The API startup flow pulls required Ollama models (generation, embedding, and judge) before serving requests. The documentation must make this clear so users understand why the first startup takes longer than subsequent ones.
- The documentation targets Linux and macOS environments. Windows users are directed to use WSL2; native Windows setup is out of scope.
- The documentation must explain that ChromaDB data persists across restarts via a Docker volume, that new ingests add to existing data, and include instructions for resetting the vector store (e.g., removing the Docker volume).
- The documentation must list the default port for each service (API: 8000, MLflow: 5000, Ollama: 11434) and explain how to remap them via Docker Compose port overrides.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The documentation MUST include a quick start guide that enables a user to bring up the project from scratch and successfully run a query.
- **FR-002**: The documentation MUST describe all API endpoints (`/ingest`, `/query`, `/health`) with request and response examples.
- **FR-003**: The documentation MUST document every environment variable in `.env.example` with its name, description, default value, and valid options.
- **FR-004**: The documentation MUST describe the models used (generation, embedding, and evaluation), their roles, and how to replace them.
- **FR-005**: The documentation MUST explain the document ingestion pipeline, including accepted formats, chunk size, and chunk overlap.
- **FR-006**: The documentation MUST explain the query pipeline, including the evaluation step and the quality metrics produced (answer relevancy, hallucination, safety).
- **FR-007**: The documentation MUST describe the available Docker profiles (CPU, NVIDIA GPU, AMD GPU) and how to activate each one.
- **FR-008**: The documentation MUST include the project structure with a description of each key directory and file.
- **FR-009**: The documentation MUST describe how to access the evaluation dashboard and how to interpret the quality metric results.
- **FR-010**: All documentation MUST be written in American English (en-US).
- **FR-011**: All detailed documentation MUST be placed under `./docs/` as individual Markdown files (e.g., `docs/api.md`, `docs/architecture.md`, `docs/configuration.md`).
- **FR-012**: The `README.md` MUST be revised for clarity and accuracy only — no new sections or content may be added. It serves as a concise project entry point.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer with no prior knowledge of the project can bring up the system and run a successful query by following only the documentation, without consulting the source code.
- **SC-002**: 100% of API endpoints are documented with at least one working request and response example.
- **SC-003**: 100% of environment variables in `.env.example` are documented with a description and default value.
- **SC-004**: Both core pipelines (ingestion and query) are described end-to-end, covering all components involved.
- **SC-005**: A developer can identify where to change the LLM model or the chunking parameters by reading only the documentation.

## Clarifications

### Session 2026-03-11

- Q: What happens if the user tries to start the project without the required Ollama models already downloaded? → A: The API startup flow auto-pulls required models via Ollama before serving requests. No manual pull step needed.
- Q: How does the documentation address environment differences between Linux, macOS, and Windows? → A: Targets Linux and macOS; Windows users are directed to WSL2. Native Windows setup is out of scope.
- Q: Does the documentation cover behavior when ChromaDB already contains data from a previous session? → A: Yes — explain persistence via Docker volume, that new ingests accumulate, and provide reset instructions (remove the volume).
- Q: What should the user do if a default port is already in use? → A: List default ports (API: 8000, MLflow: 5000, Ollama: 11434) and explain how to remap them via Docker Compose overrides.
- Q: Where should detailed documentation live, and what is the role of README.md? → A: All detailed docs go under `./docs/` as separate Markdown files. README.md is revised only (no new content added) and remains a concise entry point.

## Assumptions

- All detailed documentation is placed under `./docs/` as individual Markdown files. The `README.md` is revised for accuracy only — no new content is added to it.
- All documentation is written in American English (en-US).
- No documentation site generators (e.g., MkDocs, Sphinx) will be used — Markdown files in the repository only.
- The documentation describes the current state of the project (v0.1.0) and does not include a roadmap or future features.
- Request examples will use `curl` as the primary tool, as it is universal and language-agnostic.
- The interactive API documentation auto-generated by the API framework (accessible via browser) is considered complementary, not a replacement for the Markdown documentation in the repository.
