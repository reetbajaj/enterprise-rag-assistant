import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { Loader2 } from "lucide-react";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        backgroundColor: "var(--bg-main)",
        gap: "16px"
      }}>
        <Loader2 size={36} color="var(--primary)" className="spinner" />
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
          Authenticating session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export default ProtectedRoute;