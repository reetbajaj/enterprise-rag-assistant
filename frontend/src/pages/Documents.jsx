import { useState, useEffect, useRef, useCallback } from "react";
import { getDocuments, deleteDocument } from "../services/documentService";
import { uploadDocument } from "../services/uploadService";
import ConfirmModal from "../components/ConfirmModal";
import {
  Upload,
  FileText,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Search,
  Loader2,
  X,
  Layers,
  Calendar,
  HardDrive
} from "lucide-react";

function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [message, setMessage] = useState({ text: "", type: "" });
  const [deleteModal, setDeleteModal] = useState({ open: false, doc: null, loading: false });
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);

  const fetchDocuments = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch (error) {
      console.error("Failed to load documents:", error);
      setMessage({ text: "Failed to load documents from server.", type: "error" });
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadInitial = async () => {
      try {
        const data = await getDocuments();
        if (isMounted) {
          setDocuments(data);
        }
      } catch (err) {
        console.error("Failed to load documents:", err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadInitial();
    return () => {
      isMounted = false;
    };
  }, []);

  // Auto-polling when documents are processing
  useEffect(() => {
    const hasProcessing = documents.some((doc) => doc.status === "processing" || doc.status === "uploaded");
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      fetchDocuments(false);
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  const handleFileSelection = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setMessage({ text: "Only PDF (.pdf) files are supported.", type: "error" });
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setMessage({ text: "File exceeds maximum size limit (50MB).", type: "error" });
      return;
    }

    try {
      setUploading(true);
      setMessage({ text: "", type: "" });
      await uploadDocument(file);
      setMessage({
        text: `"${file.name}" uploaded successfully! Background extraction & indexing started.`,
        type: "success",
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await fetchDocuments(false);
    } catch (error) {
      console.error("Upload error:", error);
      const detail = error.response?.data?.detail;
      setMessage({
        text: typeof detail === "string" ? detail : "Unable to upload this document. Please try again.",
        type: "error",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const confirmDelete = async () => {
    if (!deleteModal.doc) return;
    try {
      setDeleteModal((prev) => ({ ...prev, loading: true }));
      await deleteDocument(deleteModal.doc.document_id);
      setMessage({
        text: `Document "${deleteModal.doc.filename}" and its vector embeddings were removed.`,
        type: "success",
      });
      setDeleteModal({ open: false, doc: null, loading: false });
      await fetchDocuments(false);
    } catch (error) {
      console.error("Delete error:", error);
      setMessage({ text: "Failed to delete document. Please try again.", type: "error" });
      setDeleteModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return "N/A";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%", textAlign: "left" }}>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Document Management</h1>
          <p className="page-subtitle">
            Upload PDFs for automatic text extraction, semantic chunking, and AI vector search.
          </p>
        </div>

        <button
          onClick={() => fetchDocuments(true)}
          className="btn btn-secondary btn-sm"
          disabled={loading}
          aria-label="Refresh document list"
        >
          <RefreshCw size={15} className={loading ? "spinner" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {message.text && (
        <div
          className={`alert ${message.type === "success" ? "alert-success" : "alert-danger"}`}
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: 0 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {message.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span>{message.text}</span>
          </div>
          <button
            onClick={() => setMessage({ text: "", type: "" })}
            style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
            aria-label="Close notification"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        className="glass-card"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          padding: "28px 20px",
          border: isDragging ? "2px dashed var(--primary)" : "2px dashed var(--border-medium)",
          backgroundColor: isDragging ? "var(--primary-light)" : "var(--bg-card)",
          borderRadius: "var(--radius-lg)",
          textAlign: "center",
          cursor: "pointer",
          transition: "all 0.2s ease",
          width: "100%",
        }}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={(e) => handleFileSelection(e.target.files[0])}
        />

        <div style={{
          width: "48px",
          height: "48px",
          borderRadius: "14px",
          background: "var(--primary-light)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "12px",
          color: "var(--primary)",
        }}>
          {uploading ? <Loader2 size={24} className="spinner" /> : <Upload size={24} />}
        </div>

        <h2 style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "4px" }}>
          {uploading ? "Extracting & Indexing PDF..." : "Upload Document"}
        </h2>
        <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", maxWidth: "380px", margin: "0 auto 14px", lineHeight: 1.4 }}>
          Drag & drop or select a PDF. Automatic vector indexing and text extraction. Max 50MB.
        </p>

        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={uploading}
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current && fileInputRef.current.click();
          }}
          aria-label="Select PDF file"
        >
          {uploading ? (
            <>
              <Loader2 size={15} className="spinner" />
              <span>Processing In Background...</span>
            </>
          ) : (
            <>
              <Upload size={15} />
              <span>Select PDF</span>
            </>
          )}
        </button>
      </div>

      {/* Documents View Card */}
      <div className="glass-card" style={{ padding: "20px" }}>
        {/* Search & Filter Header */}
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "18px",
          gap: "14px",
          flexWrap: "wrap",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "700" }}>
              Uploaded Files
            </h2>
            <span className="badge badge-primary" style={{ padding: "2px 8px", fontSize: "0.72rem" }}>
              {filteredDocs.length} {filteredDocs.length === 1 ? "Doc" : "Docs"}
            </span>
          </div>

          <div className="doc-search-container" style={{ position: "relative", width: "100%", maxWidth: "260px" }}>
            <Search
              size={15}
              color="var(--text-muted)"
              style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }}
            />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: "34px", paddingVertical: "7px", fontSize: "0.84rem" }}
              placeholder="Search by filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search by filename"
            />
          </div>
        </div>

        {/* Content View */}
        {loading ? (
          <div style={{ padding: "40px 0", textAlign: "center" }}>
            <Loader2 size={28} color="var(--primary)" className="spinner" style={{ margin: "0 auto 10px" }} />
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Loading document catalog...
            </p>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div style={{
            padding: "40px 16px",
            textAlign: "center",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}>
            <FileText size={36} color="var(--text-muted)" style={{ margin: "0 auto 10px" }} />
            <p style={{ fontSize: "0.9rem", fontWeight: "600", color: "#FFFFFF", marginBottom: "4px" }}>
              {searchQuery ? "No documents match your search." : "You haven't uploaded any documents yet."}
            </p>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Upload a PDF above to start asking grounded questions about your files.
            </p>
          </div>
        ) : (
          <>
            {/* 1. Desktop & Tablet Table View */}
            <div className="documents-table-view">
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                    <th style={{ padding: "10px 12px", fontWeight: "600" }}>Filename</th>
                    <th style={{ padding: "10px 12px", fontWeight: "600" }}>Size</th>
                    <th style={{ padding: "10px 12px", fontWeight: "600" }}>Status</th>
                    <th style={{ padding: "10px 12px", fontWeight: "600" }}>Chunks</th>
                    <th style={{ padding: "10px 12px", fontWeight: "600" }}>Date</th>
                    <th style={{ padding: "10px 12px", fontWeight: "600", textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.map((doc) => (
                    <tr
                      key={doc.document_id}
                      style={{ borderBottom: "1px solid var(--border-subtle)" }}
                    >
                      <td style={{ padding: "12px", color: "#FFFFFF", fontWeight: "500" }}>
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
                          <div>
                            <div style={{ fontWeight: "600", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {doc.filename}
                            </div>
                            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                              {doc.document_id}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: "12px", color: "var(--text-secondary)" }}>
                        {formatFileSize(doc.file_size)}
                      </td>

                      <td style={{ padding: "12px" }}>
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

                      <td style={{ padding: "12px", color: "var(--text-secondary)" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          <Layers size={13} color="var(--text-muted)" />
                          {doc.chunks || 0}
                        </span>
                      </td>

                      <td style={{ padding: "12px", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </td>

                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <button
                          onClick={() => setDeleteModal({ open: true, doc, loading: false })}
                          className="btn btn-danger btn-sm"
                          title="Delete Document"
                          aria-label={`Delete ${doc.filename}`}
                        >
                          <Trash2 size={14} />
                          <span>Delete</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 2. Mobile Responsive Cards View */}
            <div className="documents-cards-view">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.document_id}
                  style={{
                    padding: "14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(31, 41, 55, 0.5)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
                      <div style={{
                        padding: "6px",
                        borderRadius: "6px",
                        background: "var(--primary-light)",
                        color: "var(--primary)",
                        display: "flex",
                        flexShrink: 0,
                      }}>
                        <FileText size={16} />
                      </div>
                      <span style={{ fontWeight: "600", color: "#FFFFFF", fontSize: "0.88rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {doc.filename}
                      </span>
                    </div>

                    <div style={{ flexShrink: 0 }}>
                      {doc.status === "completed" ? (
                        <span className="badge badge-completed" style={{ padding: "2px 6px", fontSize: "0.68rem" }}>
                          Ready ✓
                        </span>
                      ) : doc.status === "processing" || doc.status === "uploaded" ? (
                        <span className="badge badge-processing" style={{ padding: "2px 6px", fontSize: "0.68rem" }}>
                          Indexing...
                        </span>
                      ) : (
                        <span className="badge badge-failed" style={{ padding: "2px 6px", fontSize: "0.68rem" }}>
                          Failed
                        </span>
                      )}
                    </div>
                  </div>

                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "14px",
                    fontSize: "0.76rem",
                    color: "var(--text-secondary)",
                    flexWrap: "wrap",
                  }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <HardDrive size={12} color="var(--text-muted)" />
                      {formatFileSize(doc.file_size)}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <Layers size={12} color="var(--text-muted)" />
                      {doc.chunks || 0} chunks
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <Calendar size={12} color="var(--text-muted)" />
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "6px", borderTop: "1px solid var(--border-subtle)" }}>
                    <button
                      onClick={() => setDeleteModal({ open: true, doc, loading: false })}
                      className="btn btn-danger btn-sm"
                      style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                      aria-label={`Delete ${doc.filename}`}
                    >
                      <Trash2 size={13} />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Reusable Confirm Modal for Deletion */}
      <ConfirmModal
        isOpen={deleteModal.open}
        title="Delete Document?"
        message={`Are you sure you want to delete "${deleteModal.doc?.filename}"? This will permanently remove the PDF and all associated vector embeddings from your ChromaDB index.`}
        confirmText="Confirm Delete"
        isDanger={true}
        isLoading={deleteModal.loading}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteModal({ open: false, doc: null, loading: false })}
      />
    </div>
  );
}

export default Documents;
