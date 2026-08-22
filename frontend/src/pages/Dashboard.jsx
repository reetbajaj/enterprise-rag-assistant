import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getDocumentStats, getDocuments } from "../services/documentService";
import {
  FileText,
  CheckCircle2,
  Clock,
  Layers,
  MessageSquare,
  Upload,
  ArrowRight,
  Sparkles,
  RefreshCw,
  AlertCircle
} from "lucide-react";

function Dashboard() {
  const [stats, setStats] = useState({
    total_documents: 0,
    completed_documents: 0,
    processing_documents: 0,
    failed_documents: 0,
    total_chunks: 0,
  });
  const [recentDocs, setRecentDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  const loadDashboardData = useCallback(async () => {
    try {
      const [statsData, docsData] = await Promise.all([
        getDocumentStats(),
        getDocuments(),
      ]);
      setStats(statsData);
      setRecentDocs(docsData.slice(0, 6));
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const fetchInit = async () => {
      try {
        const [statsData, docsData] = await Promise.all([
          getDocumentStats(),
          getDocuments(),
        ]);
        if (isMounted) {
          setStats(statsData);
          setRecentDocs(docsData.slice(0, 6));
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchInit();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  const statCards = [
    {
      title: "Total Documents",
      value: stats.total_documents,
      subtitle: "Indexed in workspace",
      icon: FileText,
      color: "#6366F1",
      bgColor: "rgba(99, 102, 241, 0.12)",
    },
    {
      title: "Completed & Ready",
      value: stats.completed_documents,
      subtitle: "Available for search",
      icon: CheckCircle2,
      color: "#10B981",
      bgColor: "rgba(16, 185, 129, 0.12)",
    },
    {
      title: "Processing",
      value: stats.processing_documents,
      subtitle: "Extracting & indexing",
      icon: Clock,
      color: "#F59E0B",
      bgColor: "rgba(245, 158, 11, 0.12)",
    },
    {
      title: "Vector Chunks",
      value: stats.total_chunks,
      subtitle: "Semantic passages",
      icon: Layers,
      color: "#06B6D4",
      bgColor: "rgba(6, 182, 212, 0.12)",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", textAlign: "left" }}>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Workspace Dashboard</h1>
          <p className="page-subtitle">
            Overview of enterprise knowledge bases, indexed documents, and AI assistant actions.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={handleRefresh}
            className="btn btn-secondary btn-sm"
            disabled={refreshing}
            aria-label="Refresh dashboard data"
          >
            <RefreshCw size={15} className={refreshing ? "spinner" : ""} />
            <span>Refresh</span>
          </button>
          <Link to="/chat" className="btn btn-primary btn-sm">
            <MessageSquare size={15} />
            <span>Open AI Chat</span>
          </Link>
        </div>
      </div>

      {/* 1. Top Statistics: 4 cols desktop -> 2x2 tablet -> 1 col mobile */}
      <div className="stats-grid">
        {statCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <div
              key={index}
              className="glass-card"
              style={{
                padding: "20px",
                display: "flex",
                alignItems: "center",
                gap: "16px",
                minWidth: 0,
              }}
            >
              <div style={{
                width: "46px",
                height: "46px",
                borderRadius: "var(--radius-md)",
                backgroundColor: card.bgColor,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}>
                <Icon size={22} color={card.color} />
              </div>
              <div style={{ minWidth: 0, flex: 1 }}>
                <p style={{
                  fontSize: "0.82rem",
                  fontWeight: "600",
                  color: "var(--text-secondary)",
                  marginBottom: "2px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}>
                  {card.title}
                </p>
                <div style={{ fontSize: "1.65rem", fontWeight: "800", color: "#FFFFFF", lineHeight: 1.1 }}>
                  {loading ? "..." : card.value}
                </div>
                <p style={{
                  fontSize: "0.74rem",
                  color: "var(--text-muted)",
                  marginTop: "2px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}>
                  {card.subtitle}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* 2. Action Cards: 2 cols desktop/tablet -> 1 col mobile */}
      <div className="actions-grid">
        {/* Upload Action */}
        <div
          className="glass-card glass-card-interactive"
          style={{
            padding: "24px",
            background: "linear-gradient(135deg, rgba(31, 41, 55, 0.7) 0%, rgba(17, 24, 39, 0.9) 100%)",
            border: "1px solid var(--border-medium)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            cursor: "pointer",
            minWidth: 0,
          }}
          onClick={() => navigate("/documents")}
        >
          <div>
            <div style={{
              display: "inline-flex",
              padding: "10px",
              borderRadius: "12px",
              background: "var(--primary-light)",
              color: "var(--primary)",
              marginBottom: "14px",
            }}>
              <Upload size={22} />
            </div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "700", marginBottom: "8px" }}>
              Upload & Manage Documents
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "18px" }}>
              Upload enterprise PDFs with automatic page extraction and vector search indexing.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--primary)", fontWeight: "600", fontSize: "0.88rem" }}>
            <span>Go to Documents</span>
            <ArrowRight size={16} />
          </div>
        </div>

        {/* Chat Action */}
        <div
          className="glass-card glass-card-interactive"
          style={{
            padding: "24px",
            background: "linear-gradient(135deg, rgba(31, 41, 55, 0.7) 0%, rgba(17, 24, 39, 0.9) 100%)",
            border: "1px solid var(--border-medium)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            cursor: "pointer",
            minWidth: 0,
          }}
          onClick={() => navigate("/chat")}
        >
          <div>
            <div style={{
              display: "inline-flex",
              padding: "10px",
              borderRadius: "12px",
              background: "var(--accent-cyan-light)",
              color: "var(--accent-cyan)",
              marginBottom: "14px",
            }}>
              <Sparkles size={22} />
            </div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "700", marginBottom: "8px" }}>
              Interactive RAG Chat
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "18px" }}>
              Ask questions grounded strictly on your documents with verified citations and zero hallucination.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-cyan)", fontWeight: "600", fontSize: "0.88rem" }}>
            <span>Launch AI Chat</span>
            <ArrowRight size={16} />
          </div>
        </div>
      </div>

      {/* 3. Recent Documents — Spanning FULL Available Width */}
      <div className="glass-card recent-docs-full" style={{ padding: "24px" }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "18px",
          flexWrap: "wrap",
          gap: "10px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "700" }}>
              Recent Documents
            </h2>
            <span className="badge badge-primary" style={{ padding: "2px 8px", fontSize: "0.72rem" }}>
              {recentDocs.length} {recentDocs.length === 1 ? "File" : "Files"}
            </span>
          </div>

          <Link
            to="/documents"
            style={{ fontSize: "0.85rem", color: "var(--primary)", fontWeight: "600", textDecoration: "none" }}
          >
            View All Documents &rarr;
          </Link>
        </div>

        {recentDocs.length === 0 ? (
          <div style={{
            padding: "36px 16px",
            textAlign: "center",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}>
            <FileText size={32} color="var(--text-muted)" style={{ margin: "0 auto 10px" }} />
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "4px" }}>
              No documents uploaded yet in this workspace.
            </p>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Upload your first PDF to start asking grounded questions.
            </p>
            <Link to="/documents" className="btn btn-primary btn-sm" style={{ marginTop: "14px" }}>
              <Upload size={14} />
              <span>Upload PDF</span>
            </Link>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Filename</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Status</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Passages</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Uploaded Date</th>
                </tr>
              </thead>
              <tbody>
                {recentDocs.map((doc) => (
                  <tr
                    key={doc.document_id}
                    style={{ borderBottom: "1px solid var(--border-subtle)" }}
                  >
                    <td style={{ padding: "12px 14px", color: "#FFFFFF", fontWeight: "500" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{
                          padding: "6px",
                          borderRadius: "6px",
                          background: "var(--primary-light)",
                          color: "var(--primary)",
                          display: "flex",
                        }}>
                          <FileText size={16} />
                        </div>
                        <span style={{ maxWidth: "320px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {doc.filename}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      {doc.status === "completed" ? (
                        <span className="badge badge-completed">
                          <CheckCircle2 size={12} />
                          Ready ✓
                        </span>
                      ) : doc.status === "processing" || doc.status === "uploaded" ? (
                        <span className="badge badge-processing">
                          <span className="pulse-dot"></span>
                          Indexing...
                        </span>
                      ) : (
                        <span className="badge badge-failed">
                          <AlertCircle size={12} />
                          Failed
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-secondary)" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <Layers size={13} color="var(--text-muted)" />
                        {doc.chunks || 0}
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                      {new Date(doc.uploaded_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;