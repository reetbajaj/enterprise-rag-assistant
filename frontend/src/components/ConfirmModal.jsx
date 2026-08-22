import { useEffect } from "react";
import { AlertTriangle, Loader2, X } from "lucide-react";

function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText = "Delete",
  cancelText = "Cancel",
  isDanger = true,
  isLoading = false,
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isLoading, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) {
          onCancel();
        }
      }}
    >
      <div
        className="glass-card"
        style={{
          width: "100%",
          maxWidth: "460px",
          padding: "28px",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border-medium)",
          textAlign: "left",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                padding: "10px",
                borderRadius: "12px",
                backgroundColor: isDanger ? "var(--danger-light)" : "var(--primary-light)",
                color: isDanger ? "var(--danger)" : "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle size={24} />
            </div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#FFFFFF", margin: 0 }}>
              {title}
            </h3>
          </div>

          <button
            onClick={onCancel}
            disabled={isLoading}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "24px", lineHeight: 1.5 }}>
          {message}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </button>

          <button
            type="button"
            className={`btn ${isDanger ? "btn-danger" : "btn-primary"} btn-sm`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 size={15} className="spinner" />
                <span>Processing...</span>
              </>
            ) : (
              <span>{confirmText}</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;
