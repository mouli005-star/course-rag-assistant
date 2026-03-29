# Agentic RAG Course Planning Assistant – Writeup

## Overview

This project implements an Agentic Retrieval-Augmented Generation (RAG) system that helps students understand course prerequisites and generate semester plans using grounded academic catalog data.

Primary dataset:
Cisco College 2025–2026 General Catalog.

The catalog includes:

• course inventory
• degree program requirements
• prerequisite relationships
• academic regulations

Example sections:
Associate of Science programs (around page 70)
Computer Science courses (around page 152)
Academic policies including GPA requirements (around page 52) 

The system answers prerequisite questions, generates structured course plans, and provides citations from the catalog.

---

## System Architecture

The system follows an agent-style modular workflow.

### 1. Intake Agent

Extracts structured student intent from natural language queries.

Examples:
completed courses
degree program
maximum courses per semester
academic term

---

### 2. Retriever Agent

Finds relevant catalog sections using embeddings.

Vector database:
ChromaDB

Embedding model:
text-embedding-3-small

Retrieval:
top-k similarity search

---

### 3. Reasoning Agent

Determines:

• whether prerequisites are satisfied
• which courses are eligible next
• missing academic requirements

Uses retrieved catalog chunks as context.

---

### 4. Planning Agent

Generates semester course plan based on:

• prerequisite graph
• degree structure
• user constraints (max courses)

Produces structured output.

---

### 5. Verifier Agent

Ensures:

• answers are grounded in catalog text
• citations are provided
• hallucinations are avoided
• system abstains when info not present

---

## RAG Pipeline

### Document ingestion

Catalog PDF parsed and converted into text chunks.

### Chunking strategy

Chunk size: 800 tokens
Overlap: 120 tokens

Chosen to preserve prerequisite relationships inside course descriptions.

---

### Embeddings

Model:
text-embedding-3-small

Selected for good semantic accuracy with low cost.

---

### Vector database

ChromaDB used to store embeddings and enable fast retrieval.

---

### Retrieval configuration

Top-k retrieval used to provide relevant context for reasoning agent.

---

## Dataset

Primary source:

Cisco College 2025–2026 General Catalog 

Contains:

course descriptions
degree requirements
academic regulations
program pathways

Supports multi-hop reasoning questions such as:

prerequisite chains
degree eligibility
course planning constraints

---

## Evaluation Methodology

Evaluation dataset includes 25 queries covering:

prerequisite eligibility questions
multi-step prerequisite chains
degree requirement questions
course planning queries
missing-information scenarios

Evaluation verifies:

answers include citations
system abstains when answer not found
planner respects prerequisite dependencies

---

## Output Structure

All responses follow structured format:

Answer / Plan

Why

Citations

Clarifying questions

Assumptions

---

## Limitations

Course naming variations may require clarification.

Course availability may vary by academic term.

Catalog updates may change prerequisite structures.

---

## Future Improvements

support multiple catalogs

improve fuzzy matching of course names

include scheduling constraints such as time conflicts

add student profile memory

---

## How to run

pip install -r requirements.txt

streamlit run ui.py

---

## Repository

https://github.com/mouli005-star/course-rag-assistant

---

## Alignment with assignment requirements

Uses RAG pipeline
Implements agent-style workflow
Provides grounded citations
Handles missing information safely
Includes evaluation dataset
Includes UI interface
