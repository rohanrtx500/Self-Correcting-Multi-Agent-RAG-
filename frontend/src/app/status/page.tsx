"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle,
  Database,
  RefreshCw,
  Server,
  Settings,
  ShieldAlert,
  Clock,
  Gauge,
  Cpu,
} from "lucide-react";
import { checkHealth, getMetrics, HealthStatus, MetricsPayload } from "@/lib/api";

export default function StatusPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [metrics, setMetrics] = useState<MetricsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatusData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [healthData, metricsData] = await Promise.all([checkHealth(), getMetrics()]);
      setHealth(healthData);
      setMetrics(metricsData);
    } catch (e: unknown) {
      console.error(e);
      const errMsg = e instanceof Error ? e.message : String(e);
      setError(errMsg || "Failed to fetch service status. Is the FastAPI server running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchStatusData();
    });
  }, []);

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
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
              System Health & Status
            </h1>
          </div>
          <button
            onClick={fetchStatusData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-card-border hover:bg-card text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {/* Main Body */}
      <main className="max-w-4xl mx-auto px-6 py-12 flex-1 w-full">
        {error && (
          <div className="p-4 rounded-xl border border-error/20 bg-error/10 text-error text-sm flex items-start gap-3 mb-8">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-slate-100">API Connection Offline</h3>
              <p className="text-xs text-error/85 mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Node 1: API & DB Health */}
          <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-6">
            <div className="flex items-center gap-2 border-b border-card-border pb-3">
              <Server className="w-5 h-5 text-accent" />
              <h3 className="font-bold text-slate-200">Core Services Connectivity</h3>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">API Service Status</span>
                {loading ? (
                  <span className="text-xs text-muted">Checking...</span>
                ) : health ? (
                  <span className="inline-flex items-center gap-1 text-xs text-success font-semibold">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Operational
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-error font-semibold">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Offline
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Vector Database Connection</span>
                {loading ? (
                  <span className="text-xs text-muted">Checking...</span>
                ) : health?.database_connected ? (
                  <span className="inline-flex items-center gap-1 text-xs text-success font-semibold">
                    <Database className="w-3.5 h-3.5" />
                    Connected
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-error font-semibold">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Disconnected
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Active LLM Provider</span>
                <span className="text-xs font-semibold bg-accent/15 text-accent px-2 py-0.5 rounded font-mono uppercase">
                  {loading ? "..." : health?.llm_provider || "N/A"}
                </span>
              </div>
            </div>
          </div>

          {/* Node 2: Telemetry Metrics */}
          <div className="p-6 rounded-2xl border border-card-border bg-card/25 flex flex-col gap-6">
            <div className="flex items-center gap-2 border-b border-card-border pb-3">
              <Gauge className="w-5 h-5 text-accent" />
              <h3 className="font-bold text-slate-200">Performance Metrics</h3>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-muted" />
                  <span className="text-xs text-muted">Server Uptime</span>
                </div>
                <span className="text-xs font-semibold text-slate-200 font-mono">
                  {loading || !metrics ? "..." : formatUptime(metrics.uptime_seconds)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Queries Processed</span>
                <span className="text-xs font-semibold text-slate-200 font-mono">
                  {loading || !metrics ? "..." : metrics.queries_processed}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Average Response Latency</span>
                <span className="text-xs font-semibold text-slate-200 font-mono">
                  {loading || !metrics ? "..." : `${metrics.average_query_latency.toFixed(3)}s`}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Configurations */}
        <div className="mt-8 p-6 rounded-2xl border border-card-border bg-card/10 flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-card-border pb-3">
            <Settings className="w-4.5 h-4.5 text-slate-300" />
            <h3 className="font-bold text-slate-300">Active Pipeline Configuration</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="flex items-center justify-between bg-card/20 p-3 rounded-lg border border-card-border">
              <span className="text-muted">Fact Match Sensitivity</span>
              <span className="font-mono text-slate-200">0.70</span>
            </div>
            <div className="flex items-center justify-between bg-card/20 p-3 rounded-lg border border-card-border">
              <span className="text-muted">Max Verification Attempts</span>
              <span className="font-mono text-slate-200">3 retries</span>
            </div>
            <div className="flex items-center justify-between bg-card/20 p-3 rounded-lg border border-card-border">
              <span className="text-muted">Embedding Engine Model</span>
              <span className="font-mono text-slate-200 flex items-center gap-1">
                <Cpu className="w-3 h-3 text-accent" />
                all-MiniLM-L6-v2
              </span>
            </div>
            <div className="flex items-center justify-between bg-card/20 p-3 rounded-lg border border-card-border">
              <span className="text-muted">Ingestion Document Loaders</span>
              <span className="font-mono text-slate-200">PDF, TXT, MD, JSON</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
