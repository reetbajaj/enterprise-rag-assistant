import { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  LogOut,
  Sparkles,
  User,
  Menu,
  X,
  ShieldCheck
} from "lucide-react";

function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && mobileNavOpen) {
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileNavOpen]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/documents", label: "Documents", icon: FileText },
    { to: "/chat", label: "AI Chat", icon: MessageSquare },
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--bg-main)", width: "100%", overflowX: "hidden" }}>
      {/* 1. Mobile Top Header Bar */}
      <header className="mobile-header-bar">
        <button
          onClick={() => setMobileNavOpen(true)}
          style={{
            background: "transparent",
            border: "none",
            color: "#FFFFFF",
            cursor: "pointer",
            padding: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "8px",
          }}
          aria-label="Open navigation menu"
        >
          <Menu size={22} />
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{
            width: "28px",
            height: "28px",
            borderRadius: "8px",
            background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            <Sparkles size={16} color="#FFFFFF" />
          </div>
          <span style={{ fontSize: "1rem", fontWeight: "800", color: "#FFFFFF" }}>
            Enterprise RAG
          </span>
        </div>

        <div style={{ width: "32px", height: "32px", borderRadius: "50%", backgroundColor: "var(--primary-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--primary)", fontWeight: "700", fontSize: "0.8rem" }}>
          {user?.email ? user.email.charAt(0).toUpperCase() : "U"}
        </div>
      </header>

      {/* 2. Mobile Nav Drawer Overlay */}
      {mobileNavOpen && (
        <div
          className="mobile-nav-backdrop"
          onClick={() => setMobileNavOpen(false)}
        >
          <div
            className="mobile-nav-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div style={{
              padding: "20px",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{
                  width: "34px",
                  height: "34px",
                  borderRadius: "10px",
                  background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}>
                  <Sparkles size={18} color="#FFFFFF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "1rem", fontWeight: "800", color: "#FFFFFF", margin: 0 }}>
                    Enterprise RAG
                  </h2>
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    AI Knowledge System
                  </span>
                </div>
              </div>

              <button
                onClick={() => setMobileNavOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "6px",
                }}
                aria-label="Close navigation menu"
              >
                <X size={20} />
              </button>
            </div>

            {/* Navigation Links */}
            <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: "6px" }}>
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileNavOpen(false)}
                    style={({ isActive }) => ({
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "var(--radius-md)",
                      fontSize: "0.95rem",
                      fontWeight: isActive ? "600" : "500",
                      textDecoration: "none",
                      color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                      backgroundColor: isActive ? "var(--primary-light)" : "transparent",
                      border: isActive ? "1px solid var(--border-highlight)" : "1px solid transparent",
                    })}
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            {/* Drawer User Info & Logout */}
            <div style={{ padding: "16px", borderTop: "1px solid var(--border-subtle)", backgroundColor: "rgba(11, 15, 25, 0.6)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
                <div style={{
                  width: "34px",
                  height: "34px",
                  borderRadius: "50%",
                  backgroundColor: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#FFFFFF",
                  fontWeight: "700",
                  fontSize: "0.85rem",
                }}>
                  {user?.email ? user.email.charAt(0).toUpperCase() : <User size={16} />}
                </div>
                <div style={{ overflow: "hidden", flex: 1 }}>
                  <p style={{ fontSize: "0.82rem", fontWeight: "600", color: "#FFFFFF", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {user?.email || "User"}
                  </p>
                  <span style={{ fontSize: "0.7rem", color: "#10B981", fontWeight: "600" }}>Active Session</span>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="btn btn-outline btn-sm"
                style={{ width: "100%", justifyContent: "center", color: "#F87171" }}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Desktop Sticky Sidebar */}
      <aside className="desktop-sidebar">
        {/* Brand */}
        <div style={{
          padding: "24px 20px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}>
          <div style={{
            width: "38px",
            height: "38px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 15px rgba(99, 102, 241, 0.4)",
          }}>
            <Sparkles size={20} color="#FFFFFF" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.05rem", fontWeight: "800", color: "#FFFFFF", lineHeight: 1.2 }}>
              Enterprise RAG
            </h2>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: "500" }}>
              AI Knowledge System
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav style={{ flex: 1, padding: "20px 12px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "11px 14px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                  fontWeight: isActive ? "600" : "500",
                  textDecoration: "none",
                  transition: "all 0.15s ease",
                  color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                  backgroundColor: isActive ? "var(--primary-light)" : "transparent",
                  border: isActive ? "1px solid var(--border-highlight)" : "1px solid transparent",
                })}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User Card & Logout Footer */}
        <div style={{
          padding: "16px",
          borderTop: "1px solid var(--border-subtle)",
          backgroundColor: "rgba(11, 15, 25, 0.5)",
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "12px",
            padding: "8px 10px",
            borderRadius: "var(--radius-md)",
            background: "rgba(31, 41, 55, 0.5)",
          }}>
            <div style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              backgroundColor: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              fontWeight: "700",
              fontSize: "0.85rem",
            }}>
              {user?.email ? user.email.charAt(0).toUpperCase() : <User size={16} />}
            </div>
            <div style={{ overflow: "hidden", flex: 1, textAlign: "left" }}>
              <p style={{
                fontSize: "0.82rem",
                fontWeight: "600",
                color: "#FFFFFF",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                margin: 0
              }}>
                {user?.email || "Authenticated User"}
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span className="pulse-dot" style={{ color: "#10B981" }}></span>
                <span style={{ fontSize: "0.7rem", color: "#10B981", fontWeight: "600" }}>Active Session</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="btn btn-outline btn-sm"
            style={{ width: "100%", justifyContent: "center", color: "#F87171" }}
          >
            <LogOut size={15} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* 4. Main Content Area */}
      <main style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        minWidth: 0,
        overflowX: "hidden",
      }}>
        {/* Desktop Sticky Header */}
        <header
          className="page-header-desktop-banner"
          style={{
            height: "64px",
            borderBottom: "1px solid var(--border-subtle)",
            backgroundColor: "rgba(17, 24, 39, 0.6)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 32px",
            position: "sticky",
            top: 0,
            zIndex: 40,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <ShieldCheck size={18} color="#10B981" />
            <span style={{ fontSize: "0.82rem", color: "var(--text-secondary)", fontWeight: "500" }}>
              Isolated Tenant Environment &bull; RAG Protected
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span className="badge badge-primary">
              <Sparkles size={12} />
              AI Assistant Ready
            </span>
          </div>
        </header>

        {/* Page Content View */}
        <div className="page-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default Layout;
