ADEA – Autonomous Data Engineer Agent

This repository implements an AI-driven platform that builds, monitors, repairs, and optimizes data pipelines using agent-based orchestration.

Coding agents (Codex, Copilot, etc.) must follow the architectural rules defined here.

---

1. Architecture Overview

ADEA uses a layered architecture:

API Layer
↓
Orchestration Layer (LangGraph)
↓
Agent Layer
↓
Pipeline Execution Layer
↓
Data Layer (Database + Memory)

Dependencies must always flow downward.

Modules must never import from higher layers.

---

2. Project Structure

The repository is organized as follows:

adea/

app/
API entrypoints and application configuration

api/
FastAPI route handlers

orchestration/
LangGraph workflow and state system

agents/
Autonomous agents performing system tasks

pipelines/
Pipeline execution and transformation logic

monitoring/
Anomaly detection and validation logic

memory/
Vector knowledge base for failure patterns

database/
SQLAlchemy models and repositories

utils/
Logging and shared utilities

---

3. Global State Object

All agents communicate using a shared state object.

Defined in:

orchestration/state.py

Class:

PipelineState

Fields:

pipeline_id: str
user_prompt: str
pipeline_plan: dict
execution_logs: list
pipeline_status: str
error_type: str
diagnosis: dict
repair_action: dict
optimization: dict

All agent functions must follow:

input: PipelineState
output: PipelineState

Agents must not modify state structure.

---

4. Agent Design Rules

All agents must inherit from:

agents/base_agent.py

BaseAgent class.

Example interface:

class BaseAgent:

def run(self, state: PipelineState) -> PipelineState:
    raise NotImplementedError

Agents must only perform one responsibility.

Examples:

PipelineGeneratorAgent → generate pipeline plan
MonitoringAgent → detect anomalies
DiagnosisAgent → identify root cause
RepairAgent → modify pipeline plan
OptimizationAgent → suggest improvements

Agents must never call other agents directly.

All transitions between agents are controlled by LangGraph.

---

5. LangGraph Workflow

The system workflow is controlled by LangGraph.

Workflow nodes:

pipeline_generator
pipeline_executor
monitoring
diagnosis
repair
optimization

Example flow:

START
↓
pipeline_generator
↓
pipeline_executor
↓
monitoring

monitoring → diagnosis (if error)
monitoring → optimization (if success)

diagnosis → repair
repair → pipeline_executor

optimization → END

Agents must never bypass this workflow.

---

6. API Rules

FastAPI routes must only trigger workflows.

Routes must NOT execute business logic.

Correct pattern:

API → LangGraph workflow → agents

Incorrect pattern:

API → executor.run()

---

7. Database Rules

Database access must only occur through:

database/repository.py

Agents must not access database models directly.

---

8. Memory System

The memory layer stores historical knowledge.

Stored data:

pipeline failures
diagnosis records
repair strategies
optimization suggestions

Memory system uses FAISS vector store.

Agents may query memory but must not modify schema.

---

9. Logging

All modules must use the centralized logger defined in:

utils/logging.py

No module should create custom loggers.

---

10. Coding Standards

Follow these rules:

• Python 3.11
• Type hints required
• Use Pydantic for request/response models
• Avoid global variables
• Prefer pure functions when possible
• Write modular code

---

11. What Coding Agents Must NOT Do

Coding agents must never:

• change architecture layers
• introduce circular imports
• allow agents to call other agents
• modify PipelineState structure
• place business logic inside API routes

---

12. Goal of the System

ADEA aims to simulate an autonomous data engineer.

Capabilities include:

• generating pipelines
• detecting pipeline failures
• diagnosing root causes
• repairing pipelines automatically
• optimizing performance

All code generation must support these goals.

---