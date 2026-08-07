# Architecture Overview - Self-Correcting Multi-Agent RAG

This document illustrates the technical design, data flows, state machine nodes, and ingestion mechanics of the Self-Correcting RAG system built using LangGraph.

---

## 1. Overall System Architecture

```mermaid
graph TD
    Client[Client / FastAPI UI] <--> API[FastAPI Web Server]
    subgraph LangGraph Orchestrator
        API <--> Graph[Compiled State Graph]
        Graph <--> Router[Router LLM Agent]
        Graph <--> Grader[Document Grader LLM Agent]
        Graph <--> Generator[Generator LLM Agent]
        Graph <--> Hallucination[Hallucination Grader LLM Agent]
    end
    subgraph Knowledge Sources
        Graph <--> VectorDB[Chroma Vector DB]
        Graph <--> Tavily[Tavily Search API]
    end
```

---

## 2. LangGraph State Machine Workflow

The graph begins at `START` and executes agent states based on the routing parameters and grades.

```mermaid
stateDiagram-v2
    [*] --> RouterNode : Query Received
    
    RouterNode --> RetrieveNode : Route: "vectorstore"
    RouterNode --> WebSearchNode : Route: "websearch"
    
    RetrieveNode --> DocumentGraderNode
    
    DocumentGraderNode --> GenerateNode : Any relevant document found
    DocumentGraderNode --> WebSearchNode : No relevant documents found
    
    WebSearchNode --> GenerateNode
    
    GenerateNode --> HallucinationGraderNode
    
    state GradeDecision <<choice>>
    HallucinationGraderNode --> GradeDecision
    
    GradeDecision --> GenerateNode : Hallucination detected (retry count < 3)
    GradeDecision --> [*] : Grounded answer (Success) or Max retries reached
```

---

## 3. Data Flow and State Modifications

Each node receives the current `AgentState`, processes data, and returns a dictionary updating specific state attributes.

```mermaid
sequenceDiagram
    autonumber
    participant S as AgentState
    participant R as Router Node
    participant DB as VectorDB (Chroma)
    participant G as Generator Node
    participant H as Hallucination Grader
    
    Note over S, R: Start Flow
    S->>R: Read question
    R->>S: Write router_decision to metadata
    alt Vector store path
        S->>DB: Query question
        DB-->>S: Write documents & retrieved_chunks
        Note over S: Grade documents (discard irrelevant)
    else Web search path
        Note over S: Fetch web results via Tavily
        S->>S: Append search documents
    end
    S->>G: Read formatted context documents & question
    G-->>S: Write generation, sources, increment retry_count
    S->>H: Read generation & context documents
    H-->>S: Write hallucination_score (Grounded / Hallucinated)
    alt Hallucinated & retry_count < 3
        Note over S: Loop back to Generator Node
    else Grounded
        Note over S: Output generation & Finish
    end
```

---

## 4. RAG Ingestion Pipeline

The ingestion pipeline handles preprocessing and text partitioning to store information in the Chroma persistent store.

```mermaid
graph LR
    Source[File: PDF, MD, TXT, JSON] --> Loader[File Loaders]
    Loader --> Document[Raw Documents]
    Document --> Splitter[Recursive Character Text Splitter]
    Splitter --> Chunks[Overlapping Chunks]
    Chunks --> Embedding[OpenAI Embeddings Engine]
    Embedding --> Index[Chroma DB Indexer]
    Index --> Storage[(Chroma Persistent DB)]
```

---

## 5. Folder Structure Tree

```
self-correcting-multi-agent-rag/
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
├── Makefile
├── .github/
│   └── workflows/
│       └── python.yml
├── docs/
│   └── architecture.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── router.py
│   │   ├── edges.py
│   │   ├── prompts.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── retrieve.py
│   │       ├── grade_documents.py
│   │       ├── web_search.py
│   │       ├── generate.py
│   │       └── hallucination.py
│   ├── vectorstore/
│   │   ├── __init__.py
│   │   ├── chroma.py
│   │   ├── loader.py
│   │   ├── embeddings.py
│   │   └── ingestion.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   ├── openai.py
│   │   └── groq.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── helpers.py
│       └── timing.py
├── tests/
└── scripts/
```
