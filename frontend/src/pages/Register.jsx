import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import {
  Sparkles,
  Lock,
  Mail,
  AlertCircle,
  ArrowRight,
  Loader2,
  CheckCircle2,
  XCircle,
  ShieldCheck
} from "lucide-react";

function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  // Strong password checks
  const hasMinLen = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>_~`\-+=/\\\][]/.test(password);
  const hasMatch = password.length > 0 && password === confirmPassword;

  const isFormValid =
    email.includes("@") &&
    hasMinLen &&
    hasUpper &&
    hasLower &&
    hasNumber &&
    hasSpecial &&
    hasMatch;

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) {
      setError("Please fill in all required fields.");
      return;
    }

    if (!isFormValid) {
      setError("Please satisfy all strong password requirements before continuing.");
      return;
    }

    try {
      setError("");
      setLoading(true);
      await register(email, password);
      navigate("/dashboard");
    } catch (err) {
      console.error("Registration error:", err);
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Registration failed. Please check your information and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const criteria = [
    { label: "At least 8 characters", valid: hasMinLen },
    { label: "One uppercase letter (A-Z)", valid: hasUpper },
    { label: "One lowercase letter (a-z)", valid: hasLower },
    { label: "One number (0-9)", valid: hasNumber },
    { label: "One special character (!@#$%...)", valid: hasSpecial },
    { label: "Passwords match", valid: hasMatch },
  ];

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
      <div style={{ width: "100%", maxWidth: "480px" }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
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
            Create Enterprise Account
          </h1>
          <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Get started with isolated enterprise vector search and RAG
          </p>
        </div>

        {/* Register Form Card */}
        <div className="glass-card" style={{ padding: "32px", borderRadius: "var(--radius-xl)" }}>
          {error && (
            <div className="alert alert-danger">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>{error}</div>
            </div>
          )}

          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label" htmlFor="register-email">
                Work Email
              </label>
              <div style={{ position: "relative" }}>
                <Mail
                  size={18}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)" }}
                />
                <input
                  id="register-email"
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

            <div className="form-group">
              <label className="form-label" htmlFor="register-password">
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={18}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)" }}
                />
                <input
                  id="register-password"
                  type="password"
                  className="form-input"
                  style={{ paddingLeft: "42px" }}
                  placeholder="Enter strong password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "16px" }}>
              <label className="form-label" htmlFor="confirm-password">
                Confirm Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={18}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)" }}
                />
                <input
                  id="confirm-password"
                  type="password"
                  className="form-input"
                  style={{ paddingLeft: "42px" }}
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            {/* Live Password Requirements Checklist */}
            <div style={{
              padding: "14px 16px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "rgba(17, 24, 39, 0.6)",
              border: "1px solid var(--border-subtle)",
              marginBottom: "24px",
              textAlign: "left",
            }}>
              <div style={{
                fontSize: "0.78rem",
                fontWeight: "700",
                color: "var(--text-secondary)",
                marginBottom: "8px",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}>
                Password Requirements
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 12px" }}>
                {criteria.map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "0.78rem",
                      color: item.valid ? "#10B981" : "var(--text-muted)",
                      transition: "color 0.15s ease",
                    }}
                  >
                    {item.valid ? (
                      <CheckCircle2 size={13} color="#10B981" style={{ flexShrink: 0 }} />
                    ) : (
                      <XCircle size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                    )}
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%", padding: "12px", fontSize: "0.95rem" }}
              disabled={loading || !isFormValid}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account & Launch</span>
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
            Already have an account?{" "}
            <Link
              to="/login"
              style={{ color: "var(--primary)", fontWeight: "600", textDecoration: "none" }}
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features Checklist */}
        <div style={{
          display: "flex",
          justifyContent: "center",
          gap: "16px",
          marginTop: "24px",
          color: "var(--text-muted)",
          fontSize: "0.78rem"
        }}>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <ShieldCheck size={14} color="#10B981" /> Strict Isolation
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <ShieldCheck size={14} color="#10B981" /> Fast Vector Rerank
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <ShieldCheck size={14} color="#10B981" /> Zero Hallucination
          </span>
        </div>
      </div>
    </div>
  );
}

export default Register;