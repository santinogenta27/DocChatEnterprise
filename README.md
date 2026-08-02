# DocChat Enterprise
### Enterprise AI Agent for Sales, Internal Knowledge Management, and Customer Support

[![Live Demo Website](https://img.shields.io/badge/🚀_LIVE_DEMO_WEBSITE-enterprisedataai.com-blue?style=for-the-badge)](https://www.enterprisedataai.com/)
[![Watch Demo Video](https://img.shields.io/badge/▶️_WATCH_DEMO_VIDEO-YouTube-red?style=for-the-badge)](https://www.youtube.com/watch?v=wBtSqWNyFdI)

> 🎥 **Click the video thumbnail below or [this link](https://www.youtube.com/watch?v=wBtSqWNyFdI) to watch the Full Video Demo on YouTube.**

[![DocChat Enterprise Demo](https://img.youtube.com/vi/wBtSqWNyFdI/maxresdefault.jpg)](https://www.youtube.com/watch?v=wBtSqWNyFdI)

**Demo Workflow:** The current public demonstration showcases **Alien Mode**, the main end-to-end workflow of the platform, including document upload, knowledge extraction, conversational AI, and an embeddable AI widget.

Additional modules included in the repository explore advanced AI workflows, enterprise automation patterns, and prototype integrations under continuous development.

> 🌐 **Language Note:** The public demo UI is currently configured in Spanish. Non-Spanish speakers can easily review the full application flow by enabling their browser's built-in translation (e.g., Chrome Google Translate).

## 📌 Table of Contents
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [System Architecture](#architecture-high-level)
- [Real-World Use Cases](#real-world-use-cases--applications)
- [Getting Started & Local Setup](#getting-started)

DocChat Enterprise is an enterprise-grade AI platform that enables organizations to securely chat with private documents using advanced Retrieval-Augmented Generation (RAG).

It transforms contracts, policies, manuals, technical documentation, and complex knowledge bases into intelligent AI agents capable of answering questions, qualifying leads, generating summaries, and performing deep semantic search.

### Core Platform Capabilities:

* **Massive Multi-Document Ingestion (100–500+ PDFs):** Ingest and index hundreds of corporate PDFs into a unified knowledge base to generate instant high-level summaries or execute deep queries across multiple files.
* **Autonomous Sales Agent:** Engages prospects, qualifies leads 24/7, and guides users through product technical details.
* **Internal Knowledge Assistant:** Allows employees to instantly query company policies, SOPs, and technical documents.
* **AI Customer Support Agent:** Embeds into any website to handle complex user inquiries using private documentation.

Built for security, scalability, and enterprise-grade performance, DocChat Enterprise helps organizations unlock the full value of their private knowledge and data while keeping sensitive information secure.

## Tech Stack

| Category              | Technologies                                      |
|-----------------------|---------------------------------------------------|
| **Core AI**           | LangChain, LangGraph, OpenAI, Anthropic           |
| **Vector Store**      | ChromaDB                                          |
| **Document Processing**| Docling, PyPDF2, pdf2image, pytesseract, Pillow  |
| **Backend**           | FastAPI, Uvicorn, Pydantic                        |
| **UI / Demo**         | Gradio                                            |
| **Databases**         | PostgreSQL, Redis, MongoDB                        |
| **Task Queue**        | Celery                                            |
| **Cloud Storage**     | AWS S3, Google Cloud Storage, Azure Blob          |
| **Integrations**      | Slack, Google APIs                                |

---

## Architecture (High Level)
PDF Upload → Document Processing (Docling + OCR)
→ Chunking + Embedding
→ Vector Store (ChromaDB)
→ Multi-Agent Orchestration (LangGraph)
→ LLM (OpenAI / Anthropic)
→ Response + Citations
textThe system supports both internal employee chat and an embeddable customer-facing widget


## 🌍 Real-World Use Cases & Applications

DocChat Enterprise can be integrated across a wide variety of industries and operational workflows to solve complex document-handling challenges:

### 1. E-Commerce & Retail

* **24/7 Customer Support (via Embeddable Widget):** Instantly answer buyer inquiries regarding shipping policies, return guidelines, warranties, or size charts using uploaded product PDFs.
* **Complex Product Assistance:** Help customers navigate extensive catalogs, technical specifications, or assembly manuals directly from the storefront website.

### 2. Internal Knowledge Management & HR

* **Employee Onboarding & Training:** Allow new hires to ask natural-language questions about company policies, internal benefits, organizational culture, and employee handbooks.
* **Instant SOP Search (Standard Operating Procedures):** Help employees resolve operational doubts in seconds without manually reading hundreds of pages of internal documentation.
* **Unified Corporate Assistant:** Serve as a single, centralized entry point for day-to-day administrative and operational queries across the company intranet.

### 3. Legal, Compliance & Auditing

* **Mass Contract Analysis:** Ingest dozens or hundreds of legal PDFs to quickly extract key clauses, expiration dates, or specific compliance conditions.
* **Regulatory Compliance Checking:** Verify whether internal procedures or company documents align with local and international legal frameworks.
* **Executive Summaries:** Generate concise, high-level summaries of complex legal filings and extensive audit reports for faster decision-making.

### 4. Finance, Banking & Accounting

* **Financial Report Analysis:** Extract, analyze, and compare financial metrics, corporate balances, and annual reports hidden within large volumes of PDF documentation.
* **Credit & Risk Policy Consulting:** Help analysts instantly check current rules, thresholds, and requirements for credit approvals and financial investments.

### 5. IT, Software Engineering & Technical Support

* **Rapid Incident Resolution:** Query software architecture guides, server documentation, and technical manuals to troubleshoot errors faster.
* **Technical Spec Libraries:** Allow engineers to cross-reference technical requirements and legacy project specifications without manual documentation scanning.

### 6. Healthcare & Pharmaceuticals

* **Clinical Trials & Medical Reference:** Search quickly through medical literature, clinical trials, drug monographs, and treatment guidelines.
* **Secure Protocol Access:** Ensure medical staff have private, instant access to up-to-date hospital protocols and clinical care procedures.

### 7. Education & Academic Portals

* **Virtual Research Tutor:** Enable students and researchers to upload multiple textbooks, theses, or scientific papers to ask direct questions or generate chapter summaries.
* **University Web Assistant:** Embed the widget on educational portals to handle student inquiries regarding syllabi, academic calendars, and enrollment processes.

### 8. Sales, Marketing & B2B

* **RFP & Tender Response Preparation:** Sales teams can quickly extract technical answers and past project details to draft competitive proposals under tight deadlines.
* **Sales Enablement:** Provide sales reps with instant access to brand guidelines, product battlecards, and feature comparisons during client interactions.

---

## ⚡ Key Features

### 📄 Advanced Document Ingestion & RAG
- **Massive Multi-Document Ingestion:** Ingest and index 100 to 500+ PDFs into a single, structured enterprise knowledge base.
- **Advanced RAG Pipeline:** Context-aware retrieval and semantic search tailored for complex enterprise documentation.
- **Enterprise Document Summarization:** Generate instant summaries and cross-document analysis across extensive PDF collections.
- **OCR & Layout Processing:** Extract text and tables from scanned documents and complex layouts using Docling + OCR.

### 🤖 Multi-Agent & AI Capabilities
- **Multi-Agent Architecture:** Built with **LangChain** and **LangGraph** for intelligent routing, query decomposition, state management, and task execution.
- **Autonomous Sales Agent:** Qualifies leads 24/7, engages prospects, and answers complex product questions.
- **Internal Knowledge Assistant:** Gives employees immediate access to company SOPs, policies, and internal guides.
- **AI Support Agent:** Handles automated customer service inquiries grounded strictly in uploaded company documents.

### 🔌 Integration & Deployment
- **Embeddable AI Widget:** Seamless integration into any external website, internal portal, or intranet.
- **Multi-LLM Support:** Native integration with OpenAI and Anthropic models via LangChain abstractions.
- **Enterprise Storage Integration:** Compatible with PostgreSQL, Redis, MongoDB, AWS S3, Google Cloud Storage, and Azure Blob.
- **Async Heavy Processing:** Background task queue processing powered by Celery for large document uploads.
- **Data Privacy & Security:** Ensures sensitive company knowledge remains private and secure within the enterprise context.

## ⚙️ How It Works (End-to-End Architecture Flow)

1. **Document Ingestion & OCR:** PDFs (up to 500+ files) are ingested using Docling and Tesseract OCR to extract text, tables, and structural layout.
2. **Chunking & Vector Embedding:** Text is split into semantic chunks and embedded into ChromaDB for high-accuracy similarity search.
3. **Multi-Agent Orchestration:** LangGraph routes user requests to specialized agents (Sales, Support, Knowledge) based on intent.
4. **Contextual RAG & Synthesis:** Relevant context is retrieved and fed into LLMs (OpenAI/Anthropic) to generate accurate answers with source citations.
5. **Multi-Channel Delivery:** Responses are served via direct interface or embedded live on web clients via the AI Widget.

## Getting Started

## Installation

```bash
# Clone the repository
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
```

Add any additional API keys required for the features you want to use.

## Run

```bash
python app.py
```
