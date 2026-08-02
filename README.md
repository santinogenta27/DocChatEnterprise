**Enterprise AI Agent for Sales, Internal Knowledge Management, and Customer Support**
[![Live Demo Website](https://img.shields.io/badge/🚀_LIVE_DEMO_WEBSITE-enterprisedataai.com-blue?style=for-the-badge)](https://www.enterprisedataai.com/)
[![Watch Demo Video](https://img.shields.io/badge/▶️_WATCH_DEMO_VIDEO-YouTube-red?style=for-the-badge)](https://www.youtube.com/watch?v=wBtSqWNyFdI)

> 🎥 **Click the image or [this link](https://www.youtube.com/watch?v=wBtSqWNyFdI) to watch the video demo on YouTube.**

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

It transforms contracts, policies, manuals, technical documentation, and other enterprise knowledge into an intelligent AI assistant capable of answering questions, generating summaries, and performing semantic search.

The platform can be used as:

An internal AI assistant for employees to access company knowledge instantly.
An AI customer support assistant embedded into any website to answer customer questions using the company’s own documentation.
Built for security, scalability, and enterprise-grade performance, DocChat Enterprise helps organizations unlock the full value of their private knowledge and data while keeping sensitive information secure.


## Key Features

- **Private RAG** over uploaded PDFs and multi-document knowledge bases
- **Multi-agent architecture** powered by LangGraph
- **Embeddable AI Widget** for any website
- Advanced document understanding with Docling + OCR
- Support for OpenAI and Anthropic models
- Enterprise storage options (PostgreSQL, Redis, MongoDB, S3, GCS, Azure Blob)
- Background task processing with Celery

---

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

## Features

* Private RAG (Retrieval-Augmented Generation) over uploaded PDFs
* Advanced RAG Pipeline: Intelligent, high-accuracy context retrieval and querying across complex enterprise documents
* AI Widget embeddable into any website
* Enterprise AI Assistant for employees
* Secure private knowledge base built from company documents
* Multi-document ingestion (upload dozens or hundreds of PDFs)
* Chat with private enterprise knowledge
* AI-powered document search and question answering
* Enterprise-grade document summarization
* Large context window for understanding extensive documentation

## How it works

* Upload one or more PDF documents to create a private enterprise knowledge base.
* Index and retrieve information using an advanced RAG pipeline.
* Employees can ask natural-language questions and receive answers grounded in the uploaded documents.
* Generate summaries across large collections of enterprise PDFs.
* Search internal company knowledge instantly without manually reading documentation.
* Embed the AI assistant as a widget inside any website, portal, or internal enterprise application.
* Keep enterprise knowledge private while enabling fast, intelligent access to information.

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
