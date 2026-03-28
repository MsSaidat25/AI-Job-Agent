Generate a Software Design Document (SDD) for this project.

## Instructions

1. Read the entire codebase to understand the system architecture:
   - Entry points and request flow
   - Component/module boundaries and their responsibilities
   - Data models and relationships
   - External integrations and third-party services
   - Authentication and authorization flow

2. If `docs/PRD.md` exists, read it first to align the SDD with product requirements.

3. Generate an SDD with these sections:

### System Overview
- One-paragraph description of what the system does and how it does it
- Architecture style (monolith, microservices, serverless, etc.)
- Key design decisions and their rationale

### Architecture Diagram
- Mermaid C4 or flowchart showing major components and their interactions
- Data flow direction between components
- External system boundaries

### Component Catalog
For each major component/module:
- **Name and purpose** (one sentence)
- **Responsibilities** (bullet list)
- **Dependencies** (what it imports/calls)
- **Public interface** (key exports, endpoints, or methods)

### Data Model
- Mermaid ERD showing all entities and relationships
- Key fields for each entity (not every column, just the important ones)
- Relationship types (one-to-many, many-to-many)

### API Reference
For each API endpoint or public interface:
- Method and path (e.g., `POST /api/users`)
- Request/response shape (simplified)
- Authentication requirements
- Error responses

### Security Architecture
- Authentication mechanism
- Authorization model (roles, permissions)
- Data protection (encryption, hashing)
- Input validation strategy

### Infrastructure
- Deployment topology (Mermaid diagram)
- Environment configuration
- Database and caching strategy
- CI/CD pipeline overview

### Cross-Cutting Concerns
- Error handling strategy
- Logging and observability
- Rate limiting and throttling
- Background jobs and async processing

## Writing Style

Write for two audiences at once:
- **Non-technical readers** should understand the Overview, Architecture Diagram, and Component Catalog without knowing code
- **Technical readers** should find enough detail in the API Reference, Data Model, and Security sections to onboard quickly

Use plain language. Avoid jargon where a simpler word works. When a technical term is necessary, define it on first use.

## Output

Save to `docs/sdd/SDD.md`. Use Mermaid diagrams (```mermaid blocks) for all visual elements.
Do NOT modify any code. This is a documentation-only task.
