"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Copy, Check, GitFork, Layers, ListFilter } from "lucide-react";

export default function ArchitecturePage() {
  const [copied, setCopied] = useState(false);

  const mermaidMarkup = `---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([__start__]):::first
	router(router)
	retrieve(retrieve)
	grade_documents(grade_documents)
	web_search(web_search)
	generate(generate)
	hallucination_grader(hallucination_grader)
	__end__([__end__]):::last

	__start__ --> router;
	generate --> hallucination_grader;
	grade_documents -.->|Relevant| generate;
	grade_documents -.->|Not Relevant| web_search;
	hallucination_grader -.->|Grounded| __end__;
	hallucination_grader -.->|Hallucinated & Retry < 3| generate;
	retrieve --> grade_documents;
	router -.->|vectorstore| retrieve;
	router -.->|websearch| web_search;
	web_search --> generate;
  
	classDef default fill:#f2f0ff,line-height:1.2;
	classDef first fill-opacity:0;
	classDef last fill:#bfb6fc;`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(mermaidMarkup);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="border-b border-card-border bg-card/10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 rounded-lg border border-card-border hover:bg-card transition-colors">
              <ArrowLeft className="w-4.5 h-4.5" />
            </Link>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              System Workflow Architecture
            </h1>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="max-w-6xl mx-auto px-6 py-12 flex-1 w-full flex flex-col gap-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Node details */}
          <div className="lg:col-span-1 flex flex-col gap-6">
            <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="flex items-center gap-2 border-b border-card-border pb-3">
                <Layers className="w-4.5 h-4.5 text-accent" />
                <h3 className="font-bold text-slate-200">Execution Node Roles</h3>
              </div>
              <div className="flex flex-col gap-4 text-xs leading-relaxed">
                <div>
                  <h4 className="font-semibold text-slate-300">Question Router</h4>
                  <p className="text-muted mt-0.5">Structured LLM call classifying query into local vector DB or web search engine.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300">Similarity Retriever</h4>
                  <p className="text-muted mt-0.5">Fetches top-k document chunks from Chroma vector store using Cosine / MMR metrics.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300">Relevance Critic</h4>
                  <p className="text-muted mt-0.5">LLM grader checking similarity relevance and filtering out non-matching context.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300">Tavily Web Search</h4>
                  <p className="text-muted mt-0.5">Fallback search client capturing current events / external facts.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300">Grounded Generator</h4>
                  <p className="text-muted mt-0.5">Synthesizes contextual answers with strict bracketed citations (e.g. [1], [2]).</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300">Hallucination Critic</h4>
                  <p className="text-muted mt-0.5">Self-RAG evaluator auditing generation claims and managing retry loops.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Code panel & Mermaid visualizer */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* Visualizer flowchart (pure css flow diagram) */}
            <div className="p-8 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="flex items-center gap-2 border-b border-card-border pb-3">
                <GitFork className="w-4.5 h-4.5 text-accent" />
                <h3 className="font-bold text-slate-200">Interactive Pipeline States</h3>
              </div>

              {/* Grid representation */}
              <div className="flex flex-col gap-6 text-xs mt-4">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-[10px] text-accent">
                    1
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-300">Query classification</h4>
                    <p className="text-muted mt-0.5">User question triggers LLM router to direct flow.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-[10px] text-accent">
                    2
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-300">Retriever & Grade relevance</h4>
                    <p className="text-muted mt-0.5">Extracts database context and removes noise concurrently.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-[10px] text-accent">
                    3
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-300">Synthesize & Verify (Self-RAG loop)</h4>
                    <p className="text-muted mt-0.5">Synthesizes answer with citations. Checks if assertions match source context, looping back for regeneration if hallucinations are detected.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Copyable code block */}
            <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-card-border pb-3">
                <div className="flex items-center gap-2">
                  <ListFilter className="w-4.5 h-4.5 text-accent" />
                  <h3 className="font-bold text-slate-200">Mermaid Diagram Code</h3>
                </div>
                <button
                  onClick={copyToClipboard}
                  className="p-2 rounded-lg border border-card-border hover:bg-card transition-colors flex items-center gap-1.5 text-xs font-semibold text-slate-300"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied!" : "Copy Code"}
                </button>
              </div>
              <pre className="p-4 rounded-xl bg-background font-mono text-[10px] sm:text-xs overflow-x-auto text-slate-300 leading-relaxed max-h-[300px]">
                {mermaidMarkup}
              </pre>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
