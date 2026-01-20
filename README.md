# Be Holmes | Prediction Market Intelligence Terminal

![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat-square)
![Build](https://img.shields.io/badge/Build-Stable-success?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)

## Executive Summary

**Be Holmes** is an AI-native decision support system engineered to bridge the latency and semantic gap between unstructured global intelligence and decentralized prediction markets (e.g., Polymarket).

In the domain of event derivatives, information asymmetry exists between off-chain breaking news and on-chain probability pricing. Be Holmes functions as an end-to-end **Retrieval-Augmented Generation (RAG)** agent. It ingests raw intelligence, semantically maps it to live prediction contracts via neural search, and utilizes Large Language Models (LLMs) to compute an "Alpha Verdict" based on Bayesian inference logic.

---

## Core Architecture

The system operates on a strict, linear pipeline designed to minimize hallucination and maximize actionable insight.

### 1. Intelligence Injection (Input Layer)
The user inputs unstructured text data—ranging from breaking news headlines and social sentiment to geopolitical rumors. The system bypasses rigid keyword matching, focusing instead on the **semantic intent** and **implied outcome** of the input.

### 2. Neural Semantic Mapping (Retrieval Layer)
![Exa.ai](https://img.shields.io/badge/Neural_Search-Exa.ai-000000?style=flat-square)
* **Process:** The engine converts input text into high-dimensional vector embeddings.
* **Execution:** It performs a neural search across the web, specifically targeting prediction market domains to identify correlated betting contracts.
* **Capabilities:** Maps abstract concepts (e.g., "Fed hawkish stance") to specific derivative contracts (e.g., "Fed Interest Rate Decision: March"), effectively resolving the vocabulary mismatch problem.

### 3. Bayesian Alpha Decoding (Analysis Layer)
![Google Gemini](https://img.shields.io/badge/Inference_Engine-Google_Gemini-8E75B2?style=flat-square)
* **Data Stream:** Integrated with **Polymarket Gamma API** for real-time odds and volume, and **CryptoPanic API (v2)** for market-wide sentiment calibration.
* **Logic:** The LLM acts as a macro-analyst, synthesizing two distinct datasets:
    1.  **The Signal:** The material impact of the injected intelligence.
    2.  **The Price:** The current implied probability of the relevant contracts.
* **Output:** Calculates the "Expectation Gap"—determining if the news is already **"priced-in"** or if a divergence exists between the event's real-world probability and its market price.

---

## Technical Stack

The architecture is built on a modular, high-performance stack designed for rapid inference and data throughput.

![Python](https://img.shields.io/badge/Core-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![API](https://img.shields.io/badge/Data_Stream-Polymarket_Gamma-000000?style=for-the-badge)
![API](https://img.shields.io/badge/News_Feed-CryptoPanic_v2-F7931A?style=for-the-badge)
![LLM](https://img.shields.io/badge/Model-Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)

---

## Installation & Configuration

### Prerequisites
* Python 3.8+ environment
* API Credentials for Exa.ai, Google Gemini, and CryptoPanic (Developer Level).

### Quick Start

**1. Clone the repository**
```bash
git clone [https://github.com/your-username/be-holmes.git](https://github.com/your-username/be-holmes.git)
cd be-holmes
