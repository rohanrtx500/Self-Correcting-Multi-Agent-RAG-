"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  Activity,
  ArrowLeft,
  Bot,
  Brain,
  Copy,
  FileText,
  HelpCircle,
  Network,
  Send,
  Trash2,
  User,
  ShieldCheck,
  AlertCircle,
  UploadCloud,
  CheckCircle2,
  X,
  FileCode,
} from "lucide-react";
import { sendQuery, uploadDocument, QueryResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  responseDetails?: QueryResponse;
  timestamp: Date;
}

export default function DashboardPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Active tab in the telemetry sidebar: "flow", "chunks", "metrics", "sources"
  const [activeTab, setActiveTab] = useState<"flow" | "chunks" | "metrics" | "sources">("flow");
  
  // Holds details of the currently selected message's RAG execution
  const [selectedResponse, setSelectedResponse] = useState<QueryResponse | null>(null);

  // Controls whether the Developer Telemetry sidebar is shown or standard user view is active
  const [developerMode, setDeveloperMode] = useState(false);
  const [activeCitationDoc, setActiveCitationDoc] = useState<{ title: string; content: string; source: string } | null>(null);

  // File Upload Modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string; chunks_count?: number } | null>(null);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || uploading) return;

    setUploading(true);
    setUploadStatus(null);

    try {
      const res = await uploadDocument(selectedFile);
      setUploadStatus({
        success: true,
        message: res.message,
        chunks_count: res.chunks_count,
      });
      setSelectedFile(null);
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setUploadStatus({
        success: false,
        message: errMsg || "Failed to upload and ingest document.",
      });
    } finally {
      setUploading(false);
    }
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userMsg = question;
    setQuestion("");
    setError(null);
    setLoading(true);

    // Append user message
    const newMessages: Message[] = [
      ...messages,
      { role: "user", content: userMsg, timestamp: new Date() },
    ];
    setMessages(newMessages);

    try {
      const response = await sendQuery(userMsg);
      
      // Append assistant response
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: response.answer,
          responseDetails: response,
          timestamp: new Date(),
        },
      ]);
      
      // Auto-focus the latest execution flow
      setSelectedResponse(response);
      setActiveTab("flow");
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setError(errMsg || "Failed to communicate with RAG Pipeline server.");
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setSelectedResponse(null);
    setError(null);
  };

  const handleCitationClick = (docIndex: number) => {
    if (selectedResponse && selectedResponse.retrieved_chunks && selectedResponse.retrieved_chunks[docIndex - 1]) {
      const doc = selectedResponse.retrieved_chunks[docIndex - 1];
      const sourceName = doc.metadata?.source
        ? doc.metadata.source.replace(/\\/g, "/").split("/").pop() || doc.metadata.source
        : `Source Document [${docIndex}]`;
      setActiveCitationDoc({
        title: sourceName,
        content: doc.page_content,
        source: doc.metadata?.source || "Internal Document Store",
      });
    } else {
      setActiveTab("chunks");
      if (!developerMode) setDeveloperMode(true);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // Helper to parse code blocks in response content
  const parseResponseContent = (content: string) => {
    const parts = content.split("```");
    return parts.map((part, index) => {
      const isCode = index % 2 === 1;
      if (isCode) {
        const lines = part.split("\n");
        const language = lines[0] ? lines[0].trim() : "plaintext";
        const code = lines.slice(1).join("\n").trim();
        return (
          <div key={index} className="my-3 rounded-lg overflow-hidden border border-card-border bg-background">
            <div className="flex items-center justify-between px-4 py-1.5 bg-card/65 border-b border-card-border text-[10px] sm:text-xs text-muted font-mono uppercase">
              <span>{language}</span>
              <button
                onClick={() => copyToClipboard(code)}
                className="hover:text-foreground transition-colors flex items-center gap-1 font-sans font-semibold"
              >
                <Copy className="w-3 h-3" />
                Copy
              </button>
            </div>
            <pre className="p-4 overflow-x-auto text-[11px] sm:text-xs font-mono text-slate-300">
              <code>{code}</code>
            </pre>
          </div>
        );
      } else {
        // Pre-process single citations like [1] or coupled citations like [1, 2] / [1, 2, 3] into individual citation links
        const formattedPart = part.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (_, match) => {
          const nums = match.split(/\s*,\s*/);
          return nums.map((num: string) => `[${num}](citation:${num})`).join(", ");
        });

        // Render markdown with styled bullets, bold text, headers, and interactive citation badges
        return (
          <div key={index} className="text-sm leading-relaxed text-slate-300 space-y-2">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="pl-1">{children}</li>,
                h1: ({ children }) => <h1 className="text-base font-bold text-slate-100 my-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-sm font-bold text-slate-100 my-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-xs font-bold text-slate-200 my-1">{children}</h3>,
                strong: ({ children }) => <strong className="font-semibold text-slate-100">{children}</strong>,
                a: ({ href, children }) => {
                  if (href?.startsWith("citation:")) {
                    const docNum = href.replace("citation:", "");
                    return (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleCitationClick(Number(docNum));
                        }}
                        title={`View Source Document Chunk [${docNum}]`}
                        className="inline-flex items-center justify-center font-bold text-[11px] text-amber-400 bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/35 px-1.5 py-0.5 rounded-md cursor-pointer transition-all mx-0.5 shadow-sm active:scale-95 hover:scale-105"
                      >
                        [{children}]
                      </button>
                    );
                  }
                  return (
                    <a href={href} target="_blank" rel="noreferrer" className="text-accent underline hover:opacity-80">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {formattedPart}
            </ReactMarkdown>
          </div>
        );
      }
    });
  };

  // Maps backend node execution step names to user-friendly titles and descriptions
  const getNodeDisplayDetails = (step: string) => {
    switch (step) {
      case "router_node":
        return {
          title: "Question Router",
          desc: "Evaluates intent to classify local RAG vs public web search.",
        };
      case "retrieve_node":
        return {
          title: "ChromaDB Retriever",
          desc: "Scans semantic embeddings vector database for local match chunks.",
        };
      case "grade_documents_node":
        return {
          title: "Relevance Critic",
          desc: "Filters out irrelevant chunks concurrently in a thread pool.",
        };
      case "web_search_node":
        return {
          title: "Tavily Web Search",
          desc: "Retrieves top public web pages context to answer the question.",
        };
      case "generate_node":
        return {
          title: "Grounded Generator",
          desc: "Synthesizes final answer restricting context to matched facts.",
        };
      case "hallucination_grader_node":
        return {
          title: "Hallucination Evaluator",
          desc: "Factual check loops verify claims grounding to prevent hallucinations.",
        };
      default:
        return {
          title: step.replace(/_/g, " "),
          desc: "Orchestrated graph node transition execution.",
        };
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      {/* Header */}
      <header className="border-b border-card-border bg-card/10 shrink-0">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 rounded-lg border border-card-border hover:bg-card transition-colors">
              <ArrowLeft className="w-4.5 h-4.5" />
            </Link>
            <h1 className="text-sm font-bold tracking-tight text-slate-300">AI Knowledge Workspace</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setIsUploadModalOpen(true);
                setUploadStatus(null);
                setSelectedFile(null);
              }}
              className="text-xs px-3.5 py-1.5 rounded-lg border font-semibold flex items-center gap-1.5 transition-all bg-accent/15 border-accent/30 hover:bg-accent/25 text-accent shadow-sm cursor-pointer active:scale-95"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Document</span>
            </button>

            <button
              onClick={() => setDeveloperMode(!developerMode)}
              className={`text-xs px-3.5 py-1.5 rounded-lg border font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                developerMode
                  ? "bg-accent/20 border-accent text-accent shadow-sm shadow-accent/10"
                  : "bg-card/50 border-card-border text-slate-300 hover:text-white hover:border-card-border/80"
              }`}
            >
              <Brain className="w-3.5 h-3.5 text-accent" />
              <span>{developerMode ? "Developer Mode: ON" : "User Mode"}</span>
            </button>

            <Link
              href="/status"
              className="text-xs text-muted hover:text-foreground transition-colors flex items-center gap-1 bg-card/30 px-3 py-1.5 rounded-lg border border-card-border"
            >
              <Activity className="w-3.5 h-3.5 text-success animate-pulse" />
              Health
            </Link>
          </div>
        </div>
      </header>

      {/* Main split-pane panel */}
      <div className="flex flex-1 overflow-hidden max-w-7xl w-full mx-auto px-6 py-6 gap-6">
        
        {/* Left Pane: Chatbot interface */}
        <div className="flex-1 flex flex-col rounded-2xl border border-card-border bg-card/10 overflow-hidden relative">
          
          {/* Workspace clear logs header */}
          <div className="flex items-center justify-between px-6 py-4 bg-card/15 border-b border-card-border shrink-0">
            <div className="flex items-center gap-2">
              <Bot className="w-4.5 h-4.5 text-accent" />
              <span className="text-sm font-semibold text-slate-350">TrustFlow Assistant</span>
            </div>
            {messages.length > 0 && (
              <button
                onClick={handleClearChat}
                className="text-xs text-muted hover:text-error flex items-center gap-1.5 transition-colors font-semibold"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Chat
              </button>
            )}
          </div>

          {/* Chat bubbles list */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <Brain className="w-12 h-12 text-accent/25 mb-4" />
                <h3 className="text-base font-bold text-slate-200">How can I help you today?</h3>
                <p className="text-xs text-muted max-w-xs mt-1.5">
                  Ask any question about your internal documents. TrustFlow will search company files, verify the facts, and cite precise source paragraphs.
                </p>
                <div className="flex flex-col gap-2 w-full max-w-sm mt-6">
                  <button
                    onClick={() => setQuestion("What is the parental leave policy and home office stipend?")}
                    className="p-3 text-left rounded-xl border border-card-border bg-card/25 text-xs text-slate-300 hover:border-accent/40 transition-colors"
                  >
                    What is the parental leave policy and home office stipend?
                  </button>
                  <button
                    onClick={() => setQuestion("What is the database failover SLA and encryption standard?")}
                    className="p-3 text-left rounded-xl border border-card-border bg-card/25 text-xs text-slate-300 hover:border-accent/40 transition-colors"
                  >
                    What is the database failover SLA and encryption standard?
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shrink-0">
                      <Bot className="w-4.5 h-4.5" />
                    </div>
                  )}

                  <div className="flex flex-col gap-1.5 max-w-[85%]">
                    <div
                      onClick={() => msg.responseDetails && setSelectedResponse(msg.responseDetails)}
                      className={`p-4 rounded-2xl border text-sm transition-all cursor-pointer ${
                        msg.role === "user"
                          ? "bg-accent/10 border-accent/25 text-slate-200"
                          : selectedResponse === msg.responseDetails
                          ? "bg-card border-accent/40 shadow-md shadow-accent/5"
                          : "bg-card/45 border-card-border hover:border-card-border/80"
                      }`}
                    >
                      {msg.role === "assistant" ? parseResponseContent(msg.content) : msg.content}
                    </div>

                    <div className={`flex items-center gap-3 text-[10px] text-muted px-1.5 ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}>
                      <span>
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {msg.responseDetails && (
                        <button
                          onClick={() => {
                            if (msg.responseDetails) {
                              setSelectedResponse(msg.responseDetails);
                              setActiveTab("flow");
                            }
                          }}
                          className="hover:text-accent font-semibold flex items-center gap-1 transition-colors"
                        >
                          <Network className="w-3 h-3" />
                          Node Trace
                        </button>
                      )}
                    </div>
                  </div>

                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-lg bg-card-border flex items-center justify-center text-slate-300 shrink-0">
                      <User className="w-4.5 h-4.5" />
                    </div>
                  )}
                </div>
              ))
            )}

            {/* In-progress loader skeleton */}
            {loading && (
              <div className="flex gap-4 justify-start">
                <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shrink-0 animate-pulse">
                  <Bot className="w-4.5 h-4.5" />
                </div>
                <div className="p-4 rounded-2xl border border-card-border bg-card/25 max-w-[85%] w-full flex flex-col gap-2">
                  <div className="h-4 bg-card-border rounded w-3/4 animate-pulse" />
                  <div className="h-4 bg-card-border rounded w-1/2 animate-pulse" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mx-6 mb-2 p-3 rounded-lg border border-error/20 bg-error/10 text-xs text-error flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form input */}
          <form
            onSubmit={handleSubmit}
            className="p-4 bg-card/20 border-t border-card-border flex gap-3 shrink-0"
          >
            <button
              type="button"
              onClick={() => {
                setIsUploadModalOpen(true);
                setUploadStatus(null);
                setSelectedFile(null);
              }}
              title="Upload custom document (.pdf, .txt, .md, .json)"
              className="p-3 rounded-xl border border-card-border bg-card/30 hover:bg-card text-muted hover:text-accent transition-colors shrink-0 flex items-center justify-center cursor-pointer"
            >
              <UploadCloud className="w-4.5 h-4.5" />
            </button>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a technical question..."
              className="flex-1 px-4 py-3 rounded-xl border border-card-border bg-background focus:outline-none focus:border-accent/40 text-sm transition-colors text-slate-200"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="px-5 py-3 rounded-xl bg-accent hover:bg-accent/90 text-sm font-semibold transition-colors disabled:opacity-50 flex items-center justify-center shrink-0"
            >
              <Send className="w-4.5 h-4.5 text-slate-950" />
            </button>
          </form>
        </div>

        {/* Right Pane: Telemetry Sidebar (Visible in Developer Telemetry Mode) */}
        {developerMode && (
          <div className="w-96 rounded-2xl border border-card-border bg-card/10 flex flex-col overflow-hidden shrink-0 transition-all">
            
            {/* Tabs header */}
            <div className="flex border-b border-card-border bg-card/20 shrink-0 text-[10px] sm:text-xs font-semibold">
              <button
                onClick={() => setActiveTab("flow")}
                className={`flex-1 py-3 text-center border-b-2 transition-colors ${
                  activeTab === "flow" ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                Transitions Flow
              </button>
              <button
                onClick={() => setActiveTab("chunks")}
                className={`flex-1 py-3 text-center border-b-2 transition-colors ${
                  activeTab === "chunks" ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                Retrieved Context
              </button>
              <button
                onClick={() => setActiveTab("metrics")}
                className={`flex-1 py-3 text-center border-b-2 transition-colors ${
                  activeTab === "metrics" ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                Telemetry Metrics
              </button>
            </div>

          {/* Tab contents */}
          <div className="flex-1 overflow-y-auto p-5">
            {!selectedResponse ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted p-4">
                <HelpCircle className="w-8 h-8 opacity-20 mb-2" />
                <span className="text-xs">No active node trace logs. Send a query to inspect live transitions.</span>
              </div>
            ) : (
              <>
                {/* --- TAB 1: FLOW VISUALIZER --- */}
                {activeTab === "flow" && (
                  <div className="flex flex-col gap-4 font-sans">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">LangGraph Node Traces</h3>
                    {selectedResponse.steps.map((step, idx) => {
                      const details = getNodeDisplayDetails(step);
                      const isLast = idx === selectedResponse.steps.length - 1;
                      return (
                        <div key={idx} className="flex gap-4 relative">
                          {/* Left Line separator */}
                          {!isLast && (
                            <div className="absolute left-[11px] top-6 bottom-0 w-0.5 bg-card-border" />
                          )}
                          <div className="w-6 h-6 rounded-full bg-accent/15 border border-accent/40 flex items-center justify-center font-bold text-[10px] text-accent shrink-0">
                            {idx + 1}
                          </div>
                          <div className="flex-1 flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-slate-200">{details.title}</span>
                              <span className="text-[10px] text-success font-semibold flex items-center gap-1 font-mono">
                                <ShieldCheck className="w-3 h-3" />
                                Success
                              </span>
                            </div>
                            <span className="text-[11px] text-muted leading-relaxed">{details.desc}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* --- TAB 2: RETRIEVED CHUNKS --- */}
                {activeTab === "chunks" && (
                  <div className="flex flex-col gap-4">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Retrieved Database Documents</h3>
                    {selectedResponse.sources.length === 0 ? (
                      <span className="text-xs text-muted">No document sources referenced for this query response.</span>
                    ) : (
                      selectedResponse.sources.map((source, idx) => (
                        <div key={idx} className="p-4 rounded-xl border border-card-border bg-card/30 flex flex-col gap-2">
                          <div className="flex items-center justify-between border-b border-card-border pb-1.5">
                            <span className="text-xs font-bold text-slate-200 flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5 text-accent" />
                              {source}
                            </span>
                            <span className="text-[10px] font-mono bg-accent/15 text-accent px-1.5 py-0.5 rounded font-bold">
                              Doc [{idx + 1}]
                            </span>
                          </div>
                          <p className="text-xs text-muted leading-relaxed font-mono">
                            Referenced as source context citation [{idx + 1}] in answer.
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* --- TAB 3: METRICS DASHBOARD --- */}
                {activeTab === "metrics" && (
                  <div className="flex flex-col gap-4">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Operational Latency</h3>
                    
                    <div className="grid grid-cols-1 gap-3.5">
                      {/* total pipeline latency */}
                      <div className="p-4 rounded-xl border border-accent/20 bg-accent/5 flex flex-col gap-1.5 glow-active">
                        <span className="text-[10px] text-accent uppercase font-bold tracking-wider">Total Graph Duration</span>
                        <span className="text-xl font-bold text-slate-200 font-mono">
                          {selectedResponse.execution_time.total_pipeline ? `${selectedResponse.execution_time.total_pipeline.toFixed(3)}s` : "N/A"}
                        </span>
                      </div>

                      {/* retrieval latency */}
                      <div className="p-4 rounded-xl border border-card-border bg-card/30 flex flex-col gap-1">
                        <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Retrieve Node Latency</span>
                        <span className="text-sm font-semibold text-slate-200 font-mono">
                          {selectedResponse.execution_time.retrieve ? `${selectedResponse.execution_time.retrieve.toFixed(3)}s` : "0.000s"}
                        </span>
                      </div>

                      {/* generation latency */}
                      <div className="p-4 rounded-xl border border-card-border bg-card/30 flex flex-col gap-1">
                        <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Generate Node Latency</span>
                        <span className="text-sm font-semibold text-slate-200 font-mono">
                          {selectedResponse.execution_time.generate ? `${selectedResponse.execution_time.generate.toFixed(3)}s` : "0.000s"}
                        </span>
                      </div>

                      {/* retries */}
                      <div className="p-4 rounded-xl border border-card-border bg-card/30 flex flex-col gap-1">
                        <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Self-RAG Correction Loops</span>
                        <span className="text-sm font-semibold text-slate-200 font-mono">
                          {selectedResponse.retry_count} retries
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        )}
      </div>

      {/* Citation Source Inspector Modal */}
      {activeCitationDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-card border border-card-border rounded-2xl max-w-xl w-full max-h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-card-border bg-card/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-bold text-slate-200 truncate">{activeCitationDoc.title}</h3>
              </div>
              <button
                onClick={() => setActiveCitationDoc(null)}
                className="text-xs text-muted hover:text-slate-200 px-2 py-1 rounded-md border border-card-border transition-colors font-semibold"
              >
                Close
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-4">
              <div className="text-[11px] text-muted font-mono bg-background/50 p-2.5 rounded-lg border border-card-border">
                <span className="text-slate-400">File Path / Source:</span> {activeCitationDoc.source}
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Referenced Document Excerpt</h4>
                <div className="p-4 rounded-xl bg-background/80 border border-card-border text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">
                  {activeCitationDoc.content}
                </div>
              </div>
            </div>
            <div className="px-6 py-3 border-t border-card-border bg-card/20 flex justify-end">
              <button
                onClick={() => setActiveCitationDoc(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-accent text-slate-950 hover:bg-accent/90 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Document Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-sm animate-fadeIn">
          <div className="bg-card border border-card-border rounded-2xl max-w-lg w-full flex flex-col overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-card-border bg-card/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-4.5 h-4.5 text-accent" />
                <h3 className="text-sm font-bold text-slate-200">Upload & Ingest Document</h3>
              </div>
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setSelectedFile(null);
                  setUploadStatus(null);
                }}
                className="text-xs text-muted hover:text-slate-200 p-1 rounded-lg border border-card-border transition-colors font-semibold cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleFileUpload} className="p-6 space-y-4">
              <p className="text-xs text-muted leading-relaxed">
                Select a custom file to embed into TrustFlow’s vector database. Supported formats: <span className="text-accent font-semibold font-mono">.pdf, .txt, .md, .json</span>.
              </p>

              {/* Drag & drop upload area */}
              <div className="relative border-2 border-dashed border-card-border hover:border-accent/40 rounded-xl p-6 flex flex-col items-center justify-center text-center bg-background/50 transition-colors group cursor-pointer">
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.json"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                      setUploadStatus(null);
                    }
                  }}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                {selectedFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <FileCode className="w-8 h-8 text-accent animate-bounce" />
                    <span className="text-xs font-semibold text-slate-200">{selectedFile.name}</span>
                    <span className="text-[10px] text-muted">{(selectedFile.size / 1024).toFixed(1)} KB</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <UploadCloud className="w-8 h-8 text-muted group-hover:text-accent transition-colors" />
                    <span className="text-xs font-semibold text-slate-300">Click to browse or drop file here</span>
                    <span className="text-[10px] text-muted">Max file size: 15 MB</span>
                  </div>
                )}
              </div>

              {/* Status Message */}
              {uploadStatus && (
                <div className={`p-3 rounded-lg border text-xs flex items-center gap-2.5 ${
                  uploadStatus.success
                    ? "border-success/30 bg-success/10 text-success"
                    : "border-error/30 bg-error/10 text-error"
                }`}>
                  {uploadStatus.success ? <CheckCircle2 className="w-4 h-4 shrink-0 text-success" /> : <AlertCircle className="w-4 h-4 shrink-0 text-error" />}
                  <span>{uploadStatus.message}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsUploadModalOpen(false);
                    setSelectedFile(null);
                    setUploadStatus(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-lg border border-card-border text-muted hover:text-slate-200 transition-colors cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={!selectedFile || uploading}
                  className="px-5 py-2 text-xs font-semibold rounded-lg bg-accent text-slate-950 hover:bg-accent/90 disabled:opacity-50 transition-all shadow-md flex items-center gap-2 cursor-pointer"
                >
                  {uploading ? (
                    <>
                      <span className="w-3 h-3 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                      Ingesting...
                    </>
                  ) : (
                    "Upload & Ingest"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
