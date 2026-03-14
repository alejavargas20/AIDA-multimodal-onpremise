
# Multimodal AI System with Orchestrated Agents - On-Premise 

## AIDA – Artificial Intelligence for Data Assistance

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL_Server-CC292B?style=for-the-badge&logo=microsoft-sql-server&logoColor=white)

AIDA is a multimodal artificial intelligence platform designed to assist financial data analysis through natural interaction.

The system allows users to interact with financial information using natural language, voice recordings, images, or PDF documents, transforming those inputs into technical actions such as:

* automatic SQL query generation
* database analysis
* structured financial insights
* executive summaries of results

Unlike most AI assistants that rely on external APIs, AIDA runs entirely on-premise, using open-source models executed locally. This approach ensures data privacy, regulatory compliance, and full control over sensitive financial information.

This project was developed as the Master’s Thesis (TFM) for the MSc in Big Data, Data Science & Artificial Intelligence – Universidad Complutense de Madrid.

---

## Key Features

* **Local Privacy (On-Premise):** Execution of open-source Large Language Models (LLMs) in local infrastructure, ensuring compliance with financial data regulations.

* **Native Multimodality:** Seamless interaction through text, voice recordings, images, and documents within the same conversational session.

* **Decoupled Orchestration:** Implementation of the Model Context Protocol (MCP) to dynamically route requests between the orchestrator and specialized agents.

* **Asymmetric VRAM Allocation:** Strategic GPU memory optimization by limiting transactional contexts while expanding conversational contexts (up to 32k tokens) to prevent system crashes.

* **Hybrid Text-to-SQL Generation:** Combines deterministic semantic logic with dynamic LLM-based SQL generation for secure database queries (SQL Server via ODBC).

---

## System Architecture

AIDA is built using a multi-agent architecture orchestrated through a central orchestrator and the Model Context Protocol (MCP).

The system separates responsibilities between specialized agents:

| Agent | Responsibility |
| :--- | :--- |
| **Data Agent** | SQL generation and structured financial data retrieval |
| **NLP Agent** | reasoning, summarization, conversational memory |
| **Voice Agent** | speech-to-text transcription |
| **Image Agent** | OCR extraction from documents and images |

The orchestrator analyzes the user's intent and dynamically routes each request to the appropriate agent, ensuring efficient use of system resources.

---

## Models and Agents

### Data Agent – Analytical Core
This is the most complex component of the system, responsible for interacting with the SQL Server database via ODBC. To guarantee banking-grade reliability and maintain flexibility, the system implements a Hybrid Query Engine.

* **Level 1 – Deterministic Semantic Layer:** For recurrent or critical queries, the agent uses predefined deterministic routes. This guarantees zero hallucinations and minimal computational cost.
* **Level 2 – Dynamic Text-to-SQL Generation:** Powered by **Qwen 2.5 (14B)**. For complex ad-hoc queries, the model analyzes the database catalog (`tables_catalog.json`) and dynamically generates SQL queries.
* **VRAM Optimization:** The Data Agent is limited to 2048 context tokens, since its only task is generating transactional queries and returning raw data.

### NLP Agent – Conversational Intelligence
Powered by **Llama 3.1 (8B)**, this agent manages human interaction, reasoning and summarization.

* **Long-Context Memory:** The NLP agent operates with 32,768 tokens, allowing it to process full conversation history, uploaded documents, voice transcriptions, and database results. This enables high-quality executive summaries without memory overflow.
* **Role Adaptation:** The system dynamically adapts the response style depending on the authenticated user:
  * *Analyst* → technical and direct explanations
  * *Client* → pedagogical and empathetic explanations

### Preprocessing Agents – Multimodal Input
To protect GPU resources, binary data processing is handled entirely on the CPU.

* **Voice Agent:** Uses Whisper to transcribe voice notes in real time. For privacy protection, temporary `.webm` files are deleted immediately after transcription.
* **Image Agent (OCR):** Extracts raw text from PDF documents and captured images using a local OCR pipeline.

### Prompt Optimizer – Security Router
The Prompt Optimizer acts as a semantic gateway between user input and the agents. It analyzes the user request and generates a structured execution plan in JSON format. Its critical role is protecting the database:

*Example:* If the user asks: *"What are late payment days?"* The system routes the request directly to the NLP agent.
If the user asks: *"What is the average loan term issued last month?"* The request is routed to the Data Agent to generate SQL.

---

## Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python, FastAPI |
| **Orchestration** | LangGraph |
| **LLM Inference** | llama.cpp |
| **Voice Processing** | Whisper |
| **Vision Processing**| OpenCV + OCR |
| **Frontend** | React / Next.js |
| **Database** | SQL Server |
| **Deployment** | Docker |


**Hardware Configuration:**
The system was designed to run fully on-premise, optimizing hardware resource allocation. Example development environment:
* GPU: NVIDIA RTX 5090 – 32GB VRAM
* CPU: Intel Core i7
* RAM: 32GB

GPU resources are dedicated to LLM inference, while CPU handles multimodal preprocessing tasks such as voice transcription and OCR.

---

## Project Structure

```text
aida-multimodal-onpremise
│
├── agents/              # Specialized AI agents
├── backend/             # Backend logic and API endpoints
├── mcp/                 # Model Context Protocol server
├── orchestrator/        # LangGraph orchestration engine
├── web-ui/              # Frontend application
├── scripts/             # Utility scripts
├── tests/               # Testing modules
├── docs/                # Technical documentation
├── docker/              # Containerization setup
│
├── requirements.txt     # Python dependencies
└── README.md
```

## Example Use Cases

[![AIDA Demo Video](https://www.youtube.com/watch?v=apHoQVYMS3o)
> 🎥 *Click the image above to watch the full system demonstration on YouTube.*

...

# Research Context

This project demonstrates the feasibility of deploying **advanced multimodal AI systems entirely on-premise**, combining:

- multi-agent orchestration
- local LLM inference
- multimodal processing
- natural language access to structured databases

The architecture reduces dependence on cloud AI services while preserving **data sovereignty and financial data privacy**.

---
