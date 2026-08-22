import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { Sparkles, Lock, Mail, AlertCircle, ArrowRight, Loader2, ShieldCheck } from "lucide-react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    try {
      setError("");
      setLoading(true);
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      console.error("Login error:", err);
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Invalid email or password. Please verify your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
      backgroundColor: "var(--bg-main)",
      backgroundImage: "radial-gradient(ellipse at 50% 10%, rgba(99, 102, 241, 0.15), transparent 70%)"
    }}>
      <div style={{ width: "100%", maxWidth: "440px" }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "52px",
            height: "52px",
            borderRadius: "14px",
            background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
            boxShadow: "0 0 25px rgba(99, 102, 241, 0.45)",
            marginBottom: "16px"
          }}>
            <Sparkles size={28} color="#FFFFFF" />
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#FFFFFF", marginBottom: "6px" }}>
            Welcome Back
          </h1>
          <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Sign in to access your Enterprise RAG Knowledge Base
          </p>
        </div>

        {/* Login Form Card */}
        <div className="glass-card" style={{ padding: "32px", borderRadius: "var(--radius-xl)" }}>
          {error && (
            <div className="alert alert-danger">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>{error}</div>
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                Work Email
              </label>
              <div style={{ position: "relative" }}>
                <Mail
                  size={18}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)" }}
                />
                <input
                  id="email"
                  type="email"
                  className="form-input"
                  style={{ paddingLeft: "42px" }}
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "24px" }}>
              <label className="form-label" htmlFor="password">
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={18}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)" }}
                />
                <input
                  id="password"
                  type="password"
                  className="form-input"
                  style={{ paddingLeft: "42px" }}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%", padding: "12px", fontSize: "0.95rem" }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Signing In...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Workspace</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div style={{
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid var(--border-subtle)",
            textAlign: "center",
            fontSize: "0.875rem",
            color: "var(--text-secondary)"
          }}>
            Don't have an enterprise account?{" "}
            <Link
              to="/register"
              style={{ color: "var(--primary)", fontWeight: "600", textDecoration: "none" }}
            >
              Create Account
            </Link>
          </div>
        </div>

        {/* Security Footer */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          marginTop: "24px",
          color: "var(--text-muted)",
          fontSize: "0.78rem"
        }}>
          <ShieldCheck size={16} color="#10B981" />
          <span>Tenant Isolated &bull; 256-bit Vector Encryption</span>
        </div>
      </div>
    </div>
  );
}

export default Login;