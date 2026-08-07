"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  Bot,
  Brain,
  Database,
  GitFork,
  ArrowRight,
  Layers,
  Search,
  ShieldCheck,
  Terminal,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground selection:bg-accent selection:text-white">
      {/* --- Sticky Header --- */}
      <header className="sticky top-0 z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="p-2 rounded-lg bg-accent/10 border border-accent/20 group-hover:border-accent/40 transition-colors">
              <Bot className="w-5 h-5 text-accent" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              TrustFlow
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <a href="#architecture" className="text-sm text-muted hover:text-foreground transition-colors">
              Architecture
            </a>
            <a href="#features" className="text-sm text-muted hover:text-foreground transition-colors">
              Features
            </a>
            <Link
              href="/status"
              className="text-sm text-muted hover:text-foreground transition-colors flex items-center gap-1.5"
            >
              <Activity className="w-4 h-4 text-success" />
              Status
            </Link>
          </nav>
        </div>
      </header>

      {/* --- Hero Section --- */}
      <section className="relative pt-24 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,var(--accent-glow),transparent_50%)] pointer-events-none" />
        <div className="max-w-5xl mx-auto px-6 text-center relative z-10 flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-card-border bg-card/60 text-xs font-medium text-slate-300 mb-8"
          >
            <Brain className="w-3.5 h-3.5 text-accent" />
            Powered by Self-Correcting Knowledge AI
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-6xl font-extrabold tracking-tight bg-gradient-to-b from-white via-slate-100 to-slate-500 bg-clip-text text-transparent max-w-4xl leading-tight"
          >
            TrustFlow: Verified AI Assistant
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-base sm:text-lg text-muted max-w-2xl mt-6 leading-relaxed"
          >
            An enterprise-ready AI assistant that answers questions from private company documents with verified, zero-hallucination factual accuracy and precise source citations.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center gap-4 mt-10"
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3.5 rounded-xl bg-accent hover:bg-accent/90 text-sm font-semibold transition-all shadow-xl shadow-accent/25 hover:translate-y-[-1px]"
            >
              Launch Chat Workspace
              <ArrowRight className="w-4 h-4 text-slate-950" />
            </Link>
            <a
              href="#architecture"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3.5 rounded-xl border border-card-border bg-card hover:bg-card/75 text-sm font-semibold transition-colors"
            >
              View System Workflow
            </a>
          </motion.div>
        </div>
      </section>

      {/* --- Interactive Architecture Flowchart --- */}
      <section id="architecture" className="py-20 border-t border-card-border bg-card/10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Automated Verification Workflow
            </h2>
            <p className="text-sm text-muted mt-2">
              How TrustFlow dynamically routes questions, extracts matching facts, and verifies answer accuracy.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Visual Node Flow */}
            <div className="p-8 rounded-2xl border border-card-border bg-card/40 flex flex-col gap-6 relative shadow-inner">
              <div className="flex items-center justify-between border-b border-card-border pb-4">
                <div className="flex items-center gap-2">
                  <GitFork className="w-4.5 h-4.5 text-accent" />
                  <span className="text-sm font-semibold">Active Execution Path</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                  <span className="text-xs text-muted">Ready</span>
                </div>
              </div>

              {/* Simplified visual flowchart */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-center p-3.5 rounded-xl border border-card-border bg-background font-mono text-xs font-semibold text-accent">
                  User Question
                </div>
                <div className="flex justify-center text-muted">▼</div>
                <div className="p-3.5 rounded-xl border border-card-border bg-background flex justify-between items-center text-xs">
                  <span className="font-semibold font-mono text-slate-200">1. Intent Classifier</span>
                  <span className="text-xs text-muted bg-card-border px-2 py-0.5 rounded">Smart Router</span>
                </div>
                <div className="flex justify-between px-12 text-muted">
                  <span>↙ (Documents)</span>
                  <span>↘ (Web Search)</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg border border-card-border bg-background/50 flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-200">2a. Document Search</span>
                    <span className="text-[10px] text-muted">Semantic Context Scan</span>
                  </div>
                  <div className="p-3 rounded-lg border border-card-border bg-background/50 flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-200">2b. Web Search</span>
                    <span className="text-[10px] text-muted">Live Web Search Fallback</span>
                  </div>
                </div>
                <div className="flex justify-center text-muted">▼</div>
                <div className="p-3.5 rounded-xl border border-card-border bg-background flex justify-between items-center text-xs">
                  <span className="font-semibold font-mono text-slate-200">3. Relevance Filter</span>
                  <span className="text-xs text-success bg-success/10 px-2 py-0.5 rounded">Context Check</span>
                </div>
                <div className="flex justify-center text-muted">▼</div>
                <div className="p-3.5 rounded-xl border border-card-border bg-background flex justify-between items-center text-xs">
                  <span className="font-semibold font-mono text-slate-200">4. Answer Synthesis</span>
                  <span className="text-xs text-muted bg-card-border px-2 py-0.5 rounded">Source Citations</span>
                </div>
                <div className="flex justify-center text-muted">▼</div>
                <div className="p-3.5 rounded-xl border border-accent/30 bg-accent/5 flex justify-between items-center text-xs glow-active">
                  <span className="font-semibold font-mono text-accent">5. Fact Consistency Check</span>
                  <span className="text-xs text-accent bg-accent/20 px-2 py-0.5 rounded font-mono font-bold">Verification</span>
                </div>
                </div>
            </div>

            {/* Path description */}
            <div className="flex flex-col gap-6">
              <h3 className="text-2xl font-bold text-slate-200 font-mono">Self-Correcting Feedback Loop</h3>
              <p className="text-sm text-muted leading-relaxed">
                Rather than generating answers blindly, TrustFlow acts as an intelligent fact-checker. If the document retriever extracts incomplete details, the relevance filter detects it and triggers a web search fallback.
              </p>
              <p className="text-sm text-muted leading-relaxed">
                Once an answer is synthesized, it is audited by a factual critic. If claims cannot be traced back to verified sources, TrustFlow automatically corrects and regenerates the response to ensure absolute factual grounding.
              </p>
              <div className="flex flex-col gap-3 mt-4">
                <div className="flex items-start gap-3">
                  <div className="p-1 rounded-md bg-accent/15 text-accent mt-0.5">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">Zero-Hallucination Guardrails</h4>
                    <p className="text-xs text-muted">Verifies alignment with source context before delivering output.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="p-1 rounded-md bg-accent/15 text-accent mt-0.5">
                    <Search className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">Autonomous Web Verification</h4>
                    <p className="text-xs text-muted">Escalates query to public engines when internal sources are lacking.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --- Key Capabilities Section --- */}
      <section id="features" className="py-20 border-t border-card-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Enterprise Knowledge at Your Fingertips
            </h2>
            <p className="text-sm text-muted mt-2">
              Transform unstructured company documents into an instant, trustworthy AI knowledge assistant.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                <Search className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-200">Instant Knowledge Retrieval</h3>
              <p className="text-xs text-muted leading-relaxed">
                Ask questions across HR policies, technical RFCs, financial reports, and SOC2 guidelines in plain language.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-success/10 flex items-center justify-center text-success">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-200">Guaranteed Factual Accuracy</h3>
              <p className="text-xs text-muted leading-relaxed">
                Self-correcting AI guardrails evaluate retrieved facts and verify every single claim before returning answers.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
                <Bot className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-200">Verifiable Source Citations</h3>
              <p className="text-xs text-muted leading-relaxed">
                Clickable citation badges [1], [2] allow users to inspect the exact document paragraph backing every claim.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --- Enterprise Value Banner --- */}
      <section className="py-16 border-t border-card-border bg-card/10">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold tracking-tight text-slate-200 mb-4">Ready to Explore TrustFlow?</h2>
          <p className="text-sm text-muted mb-8 max-w-xl mx-auto">
            Experience verified, grounded AI assistance backed by multi-domain enterprise knowledge.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-accent hover:bg-accent/90 text-sm font-semibold transition-all shadow-xl shadow-accent/25"
          >
            Launch Chat Workspace
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* --- Footer --- */}
      <footer className="border-t border-card-border py-8 bg-card/15 mt-auto">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-muted">
            &copy; 2026 TrustFlow. Licensed under MIT.
          </p>
          <div className="flex gap-6">
            <Link href="/dashboard" className="text-xs text-muted hover:text-foreground transition-colors">
              App
            </Link>
            <Link href="/status" className="text-xs text-muted hover:text-foreground transition-colors">
              Health Status
            </Link>
            <Link href="/architecture" className="text-xs text-muted hover:text-foreground transition-colors">
              Flowchart
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
