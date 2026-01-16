# 🔥 PROMETHEUS PROTOCOL
### The Event-Driven Intelligence Engine for Prediction Markets

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://polywish.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Gemini API](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange?logo=google&logoColor=white)](https://ai.google.dev/)
[![Polymarket](https://img.shields.io/badge/Data-Polymarket%20Gamma%20API-blueviolet)](https://polymarket.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

> *"In a world of noise, Prometheus finds the signal."*

**Prometheus** is an autonomous AI agent designed to capture Alpha in global prediction markets. By integrating **Real-time RAG (Retrieval-Augmented Generation)** with **Second-order Causal Reasoning**, it bridges the gap between unstructured breaking news and structured financial probabilities.

---

## ⚡ Live Demo
**👉 [Launch Terminal (Streamlit Cloud)](https://polywish.streamlit.app/)**


---

## 🖼️ Interface Preview
<img width="3826" height="1788" alt="image" src="https://github.com/user-attachments/assets/d1ddc491-9d23-4ea1-8871-ba0bdb5fe781" />

---

## 🧠 Core Architecture

Prometheus is not just a chatbot; it is a specialized **Reasoning Agent** built with a distinct "Trader Persona."

```mermaid
graph TD
    A[📡 User Input: Breaking News] --> B(⚡ Orchestrator)
    C[📊 Polymarket Gamma API] -->|Real-time Liquidity & Volume| D[Data Cleaning & ETL]
    D --> B
    B -->|Context Injection| E{🤖 Gemini 2.5 Flash Engine}
    
    subgraph "Reasoning Core (CoT)"
    E --> F[Semantic Mapping]
    F --> G[Second-Order Thinking]
    G --> H[Causal Inference Filter]
    end
    
    H -->|Structured Output| I[🚀 Trading Signal]
    I --> J[Terminal Display]
