

https://github.com/user-attachments/assets/0f008c2b-756b-4783-88a4-7c6e989c3912

## DocChat Enterprise
Enterprise AI Knowledge Assistant for Internal Knowledge Management and Customer Support.

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
textThe system supports both internal employee chat and an embeddable customer-facing widget.

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Add your OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

# Run the application
uvicorn api.main:app --reload
# or
python -m gradio app.py






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
