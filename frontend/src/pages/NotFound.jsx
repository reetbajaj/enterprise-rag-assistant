import { Link } from "react-router-dom";
import { AlertCircle, LayoutDashboard } from "lucide-react";

function NotFound() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "var(--bg-main)",
      padding: "24px",
      textAlign: "center",
    }}>
      <div className="glass-card" style={{ padding: "48px 36px", maxWidth: "460px", width: "100%" }}>
        <div style={{
          width: "60px",
          height: "60px",
          borderRadius: "18px",
          backgroundColor: "var(--danger-light)",
          color: "var(--danger)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "20px",
        }}>
          <AlertCircle size={32} />
        </div>

        <h1 style={{ fontSize: "2rem", fontWeight: "800", color: "#FFFFFF", marginBottom: "8px" }}>
          404 - Page Not Found
        </h1>
        <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "28px", lineHeight: 1.5 }}>
          The requested route does not exist or you may not have permission to view it.
        </p>

        <Link to="/dashboard" className="btn btn-primary" style={{ width: "100%" }}>
          <LayoutDashboard size={18} />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    </div>
  );
}

export default NotFound;
