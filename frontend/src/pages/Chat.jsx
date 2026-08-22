import { useState, useEffect, useRef, useCallback } from "react";
import { askQuestion } from "../services/queryService";
import {
  getConversations,
  getConversation,
  createConversation,
  renameConversation,
  deleteConversation,
  clearAllConversations,
} from "../services/conversationService";
import { getDocuments } from "../services/documentService";
import ConfirmModal from "../components/ConfirmModal";
import {
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  User,
  Trash2,
  Edit2,
  Check,
  X,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2,
  ShieldCheck,
  CornerDownLeft,
  Copy,
  Layers,
  History
} from "lucide-react";

let msgCounter = 0;
const getUniqueId = (prefix) => {
  msgCounter += 1;
  return `${prefix}-${msgCounter}-${Math.random().toString(36).substring(2, 7)}`;
};

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [mobileHistoryDrawer, setMobileHistoryDrawer] = useState(false);
  const [editingConvId, setEditingConvId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [expandedSources, setExpandedSources] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [docsCount, setDocsCount] = useState(0);
  const [errorBanner, setErrorBanner] = useState("");

  // Modal State
  const [modalState, setModalState] = useState({
    isOpen: false,
    title: "",
    message: "",
    confirmText: "Delete",
    isDanger: true,
    isLoading: false,
    onConfirm: () => {},
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadConversations = useCallback(async () => {
    try {
      setConversationsLoading(true);
      const data = await getConversations();
      setConversations(data);
      return data;
    } catch (err) {
      console.error("Failed to load conversations:", err);
      return [];
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  const loadDocsCount = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocsCount(docs.filter((d) => d.status === "completed").length);
    } catch (err) {
      console.error("Failed to fetch documents count:", err);
    }
  }, []);

  const selectConversation = useCallback(async (convId) => {
    setActiveConversationId(convId);
    setMessagesLoading(true);
    setMobileHistoryDrawer(false);
    try {
      const data = await getConversation(convId);
      setMessages(data.messages || []);
    } catch (err) {
      console.error("Failed to load conversation messages:", err);
      setMessages([]);
    } finally {
      setMessagesLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      const convs = await loadConversations();
      if (isMounted && convs.length > 0 && activeConversationId === null) {
        selectConversation(convs[0].id);
      }
      loadDocsCount();
    };
    init();
    return () => {
      isMounted = false;
    };
  }, [loadConversations, loadDocsCount, selectConversation, activeConversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // FIXED + NEW CHAT HANDLER: Creates a persistent conversation entity in DB & selects it immediately
  const handleNewChat = async () => {
    if (isCreatingChat) return;
    try {
      setIsCreatingChat(true);
      setErrorBanner("");
      const newConv = await createConversation("New Chat");
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      setActiveConversationId(newConv.id);
      setMessages([]);
      setEditingConvId(null);
      setMobileHistoryDrawer(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err) {
      console.error("Failed to create new conversation:", err);
      setErrorBanner("Unable to create a new chat right now. Please try again.");
    } finally {
      setIsCreatingChat(false);
    }
  };

  const handleStartRename = (conv, e) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = async (convId, e) => {
    e?.stopPropagation();
    if (!editTitle.trim()) return;
    try {
      await renameConversation(convId, editTitle.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: editTitle.trim() } : c))
      );
      setEditingConvId(null);
    } catch (err) {
      console.error("Failed to rename conversation:", err);
    }
  };

  const handleCancelRename = (e) => {
    e?.stopPropagation();
    setEditingConvId(null);
  };

  const promptDeleteConversation = (conv, e) => {
    e.stopPropagation();
    setModalState({
      isOpen: true,
      title: "Delete Conversation?",
      message: `Are you sure you want to delete "${conv.title}"? All messages in this conversation will be permanently removed.`,
      confirmText: "Delete Chat",
      isDanger: true,
      isLoading: false,
      onConfirm: async () => {
        try {
          setModalState((prev) => ({ ...prev, isLoading: true }));
          await deleteConversation(conv.id);
          const updatedConvs = conversations.filter((c) => c.id !== conv.id);
          setConversations(updatedConvs);
          if (activeConversationId === conv.id) {
            if (updatedConvs.length > 0) {
              selectConversation(updatedConvs[0].id);
            } else {
              handleNewChat();
            }
          }
          setModalState((prev) => ({ ...prev, isOpen: false, isLoading: false }));
        } catch (err) {
          console.error("Failed to delete conversation:", err);
          setModalState((prev) => ({ ...prev, isLoading: false }));
        }
      },
    });
  };

  const promptClearAllChats = () => {
    setModalState({
      isOpen: true,
      title: "Clear All Conversations?",
      message: "Are you sure you want to delete all conversation history? This action cannot be undone.",
      confirmText: "Clear Everything",
      isDanger: true,
      isLoading: false,
      onConfirm: async () => {
        try {
          setModalState((prev) => ({ ...prev, isLoading: true }));
          await clearAllConversations();
          setConversations([]);
          setMessages([]);
          setActiveConversationId(null);
          setModalState((prev) => ({ ...prev, isOpen: false, isLoading: false }));
        } catch (err) {
          console.error("Failed to clear conversations:", err);
          setModalState((prev) => ({ ...prev, isLoading: false }));
        }
      },
    });
  };

  const handleSend = async (questionToSend) => {
    const queryText = (questionToSend || inputQuestion).trim();
    if (!queryText || loading) return;

    const userMessage = {
      id: getUniqueId("user"),
      role: "user",
      content: queryText,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuestion("");
    setLoading(true);

    try {
      const result = await askQuestion(queryText, activeConversationId);

      const assistantMessage = {
        id: result.message_id || getUniqueId("assistant"),
        role: "assistant",
        content: result.answer,
        sources: result.sources || [],
        latency_seconds: result.latency_seconds,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If this was a newly created chat or first message, refresh conversation list to update title
      if (!activeConversationId && result.conversation_id) {
        setActiveConversationId(result.conversation_id);
      }
      await loadConversations();
    } catch (error) {
      console.error("Chat error:", error);
      const detail = error.response?.data?.detail;
      const errorMessage = {
        id: getUniqueId("error"),
        role: "assistant",
        content:
          typeof detail === "string"
            ? `Error: ${detail}`
            : "An unexpected error occurred while communicating with the assistant. Please verify your backend server.",
        isError: true,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleSourceExpand = (msgId, sourceIdx) => {
    const key = `${msgId}-${sourceIdx}`;
    setExpandedSources((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleCopyAnswer = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Group conversations by date
  const groupConversations = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups = {
      Today: [],
      "Previous 7 Days": [],
      Older: [],
    };

    conversations.forEach((conv) => {
      const convDate = new Date(conv.updated_at || conv.created_at);
      if (convDate >= today) {
        groups.Today.push(conv);
      } else if (convDate >= sevenDaysAgo) {
        groups["Previous 7 Days"].push(conv);
      } else {
        groups.Older.push(conv);
      }
    });

    return groups;
  };

  const grouped = groupConversations();
  const activeConvObj = conversations.find((c) => c.id === activeConversationId);

  const suggestedQuestions = [
    "Summarize the key information in my uploaded documents.",
    "Do you have any documents uploaded?",
    "What are the main topics or guidelines?",
  ];

  // Conversation Sidebar Component (shared between desktop sidebar and mobile drawer)
  const renderConversationList = () => (
    <>
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)" }}>
        <button
          onClick={handleNewChat}
          className="btn btn-primary"
          style={{ width: "100%", justifyContent: "center", gap: "8px" }}
          disabled={isCreatingChat}
          aria-label="Start new chat conversation"
        >
          {isCreatingChat ? (
            <Loader2 size={16} className="spinner" />
          ) : (
            <Plus size={16} />
          )}
          <span>{isCreatingChat ? "Creating Chat..." : "New Chat"}</span>
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 8px", display: "flex", flexDirection: "column", gap: "14px" }}>
        {conversationsLoading ? (
          <div style={{ padding: "24px 0", textAlign: "center" }}>
            <Loader2 size={24} color="var(--primary)" className="spinner" style={{ margin: "0 auto 8px" }} />
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Loading chats...</p>
          </div>
        ) : conversations.length === 0 ? (
          <div style={{ padding: "32px 12px", textAlign: "center" }}>
            <MessageSquare size={28} color="var(--text-muted)" style={{ margin: "0 auto 8px" }} />
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: "4px" }}>No conversations yet.</p>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Click New Chat to begin.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([groupTitle, convList]) => {
            if (convList.length === 0) return null;
            return (
              <div key={groupTitle}>
                <div style={{
                  fontSize: "0.72rem",
                  fontWeight: "700",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-muted)",
                  padding: "0 8px 6px",
                }}>
                  {groupTitle}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                  {convList.map((conv) => {
                    const isActive = conv.id === activeConversationId;
                    const isEditing = editingConvId === conv.id;

                    return (
                      <div
                        key={conv.id}
                        onClick={() => !isEditing && selectConversation(conv.id)}
                        style={{
                          padding: "8px 10px",
                          borderRadius: "var(--radius-md)",
                          backgroundColor: isActive ? "var(--primary-light)" : "transparent",
                          border: isActive ? "1px solid var(--border-highlight)" : "1px solid transparent",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "8px",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", flex: 1 }}>
                          <MessageSquare size={14} color={isActive ? "var(--primary)" : "var(--text-muted)"} style={{ flexShrink: 0 }} />

                          {isEditing ? (
                            <input
                              type="text"
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleSaveRename(conv.id, e);
                                if (e.key === "Escape") handleCancelRename(e);
                              }}
                              onClick={(e) => e.stopPropagation()}
                              autoFocus
                              style={{
                                width: "100%",
                                background: "var(--bg-main)",
                                border: "1px solid var(--primary)",
                                color: "#FFFFFF",
                                padding: "2px 6px",
                                fontSize: "0.82rem",
                                borderRadius: "4px",
                                outline: "none",
                              }}
                            />
                          ) : (
                            <span style={{
                              fontSize: "0.83rem",
                              color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                              fontWeight: isActive ? "600" : "500",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}>
                              {conv.title}
                            </span>
                          )}
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
                          {isEditing ? (
                            <>
                              <button
                                onClick={(e) => handleSaveRename(conv.id, e)}
                                style={{ background: "transparent", border: "none", color: "#10B981", cursor: "pointer", padding: "2px" }}
                                aria-label="Save chat title"
                              >
                                <Check size={13} />
                              </button>
                              <button
                                onClick={handleCancelRename}
                                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px" }}
                                aria-label="Cancel renaming"
                              >
                                <X size={13} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={(e) => handleStartRename(conv, e)}
                                style={{
                                  background: "transparent",
                                  border: "none",
                                  color: "var(--text-muted)",
                                  cursor: "pointer",
                                  padding: "2px",
                                  opacity: isActive ? 0.9 : 0.4,
                                }}
                                title="Rename Chat"
                                aria-label="Rename conversation"
                              >
                                <Edit2 size={12} />
                              </button>
                              <button
                                onClick={(e) => promptDeleteConversation(conv, e)}
                                style={{
                                  background: "transparent",
                                  border: "none",
                                  color: "var(--danger)",
                                  cursor: "pointer",
                                  padding: "2px",
                                  opacity: isActive ? 0.9 : 0.4,
                                }}
                                title="Delete Chat"
                                aria-label="Delete conversation"
                              >
                                <Trash2 size={12} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>

      {conversations.length > 0 && (
        <div style={{ padding: "12px", borderTop: "1px solid var(--border-subtle)", backgroundColor: "rgba(11, 15, 25, 0.4)" }}>
          <button
            onClick={promptClearAllChats}
            className="btn btn-outline btn-sm"
            style={{ width: "100%", justifyContent: "center", color: "var(--danger)", fontSize: "0.78rem" }}
          >
            <Trash2 size={13} />
            <span>Clear All Chats</span>
          </button>
        </div>
      )}
    </>
  );

  return (
    <div className="chat-layout">
      {/* 1. Left Desktop Conversations Sidebar */}
      <div className="glass-card chat-history-sidebar">
        {renderConversationList()}
      </div>

      {/* 2. Mobile Chat History Drawer Overlay */}
      {mobileHistoryDrawer && (
        <div
          className="mobile-nav-backdrop"
          onClick={() => setMobileHistoryDrawer(false)}
        >
          <div
            className="chat-history-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{
              padding: "16px 20px",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <History size={18} color="var(--primary)" />
                <span style={{ fontSize: "0.95rem", fontWeight: "700", color: "#FFFFFF" }}>
                  Chat History
                </span>
              </div>
              <button
                onClick={() => setMobileHistoryDrawer(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px" }}
                aria-label="Close chat history"
              >
                <X size={18} />
              </button>
            </div>
            {renderConversationList()}
          </div>
        </div>
      )}

      {/* 3. Main Chat Conversation Area */}
      <div className="chat-main-area">
        {/* Error Banner */}
        {errorBanner && (
          <div className="alert alert-danger" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", marginBottom: "0" }}>
            <span>{errorBanner}</span>
            <button onClick={() => setErrorBanner("")} style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* Desktop Chat Header */}
        <div className="chat-desktop-header" style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingBottom: "10px",
          borderBottom: "1px solid var(--border-subtle)",
          flexWrap: "wrap",
          gap: "12px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0, flex: 1 }}>
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              backgroundColor: "var(--primary-light)",
              color: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}>
              <Sparkles size={18} />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <h1 style={{
                fontSize: "1.2rem",
                fontWeight: "800",
                color: "#FFFFFF",
                margin: 0,
                lineHeight: 1.2,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}>
                {activeConvObj ? activeConvObj.title : "New Chat"}
              </h1>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "2px" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  AI-powered document assistant &bull; Grounded in your files
                </span>
                <span className="badge badge-primary" style={{ padding: "1px 6px", fontSize: "0.68rem" }}>
                  <Layers size={10} />
                  {docsCount} {docsCount === 1 ? "Doc" : "Docs"} Ready
                </span>
              </div>
            </div>
          </div>

          {activeConvObj && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
              <button
                onClick={(e) => promptDeleteConversation(activeConvObj, e)}
                className="btn btn-outline btn-sm"
                style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}
                aria-label="Delete this conversation"
              >
                <Trash2 size={13} />
                <span>Delete Chat</span>
              </button>
            </div>
          )}
        </div>

        {/* Mobile Chat Header */}
        <div className="chat-mobile-header">
          <button
            onClick={() => setMobileHistoryDrawer(true)}
            className="btn btn-secondary btn-sm"
            style={{ padding: "6px 10px", fontSize: "0.78rem" }}
            aria-label="Open chat history drawer"
          >
            <History size={14} />
            <span>History</span>
          </button>

          <span style={{
            fontSize: "0.88rem",
            fontWeight: "700",
            color: "#FFFFFF",
            maxWidth: "140px",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            textAlign: "center",
          }}>
            {activeConvObj ? activeConvObj.title : "New Chat"}
          </span>

          <button
            onClick={handleNewChat}
            className="btn btn-primary btn-sm"
            disabled={isCreatingChat}
            style={{ padding: "6px 10px", fontSize: "0.78rem" }}
            aria-label="Start new conversation"
          >
            {isCreatingChat ? <Loader2 size={13} className="spinner" /> : <Plus size={13} />}
            <span>New</span>
          </button>
        </div>

        {/* Message Stream */}
        <div className="glass-card" style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
          borderRadius: "var(--radius-lg)",
          minWidth: 0,
        }}>
          {messagesLoading ? (
            <div style={{ margin: "auto", textAlign: "center", padding: "32px" }}>
              <Loader2 size={30} color="var(--primary)" className="spinner" style={{ margin: "0 auto 10px" }} />
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                Loading conversation messages...
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div style={{
              margin: "auto",
              maxWidth: "540px",
              textAlign: "center",
              padding: "20px 12px",
            }}>
              <div style={{
                width: "52px",
                height: "52px",
                borderRadius: "16px",
                background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: "16px",
                boxShadow: "0 0 20px rgba(99, 102, 241, 0.4)",
              }}>
                <Sparkles size={26} color="#FFFFFF" />
              </div>
              <h2 style={{ fontSize: "1.3rem", fontWeight: "800", color: "#FFFFFF", marginBottom: "8px" }}>
                How can I assist with your documents?
              </h2>
              <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginBottom: "22px", lineHeight: 1.5 }}>
                {docsCount > 0
                  ? `You have ${docsCount} document(s) indexed. Ask questions or request summaries with verified source citations.`
                  : "You haven't uploaded any documents yet. Upload a PDF in the Documents section to start asking questions."}
              </p>

              {docsCount > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <p style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.05em" }}>
                    Suggested Prompts
                  </p>
                  {suggestedQuestions.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(prompt)}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: "rgba(31, 41, 55, 0.6)",
                        border: "1px solid var(--border-subtle)",
                        color: "var(--text-primary)",
                        fontSize: "0.84rem",
                        textAlign: "left",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "8px",
                      }}
                      className="glass-card-interactive"
                    >
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>"{prompt}"</span>
                      <CornerDownLeft size={13} color="var(--primary)" style={{ flexShrink: 0 }} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id || index}
                  style={{
                    display: "flex",
                    gap: "10px",
                    alignSelf: isUser ? "flex-end" : "flex-start",
                    maxWidth: isUser ? "85%" : "95%",
                  }}
                >
                  {!isUser && (
                    <div style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "10px",
                      background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}>
                      <Sparkles size={16} color="#FFFFFF" />
                    </div>
                  )}

                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", minWidth: 0 }}>
                    <div
                      style={{
                        padding: "14px 18px",
                        borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                        backgroundColor: isUser ? "var(--primary)" : "var(--bg-surface-elevated)",
                        color: "#FFFFFF",
                        fontSize: "0.9rem",
                        lineHeight: 1.6,
                        border: isUser ? "none" : "1px solid var(--border-subtle)",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {msg.content}
                    </div>

                    {!isUser && !msg.isError && (
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        paddingLeft: "4px",
                        fontSize: "0.74rem",
                        color: "var(--text-muted)",
                      }}>
                        {msg.latency_seconds && (
                          <span>Generated in {msg.latency_seconds}s</span>
                        )}
                        <button
                          onClick={() => handleCopyAnswer(msg.content, index)}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "0.74rem",
                          }}
                          aria-label="Copy answer text"
                        >
                          {copiedIndex === index ? (
                            <>
                              <Check size={12} color="#10B981" />
                              <span style={{ color: "#10B981" }}>Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={12} />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Citations Section */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div style={{
                        marginTop: "6px",
                        padding: "10px 12px",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: "rgba(17, 24, 39, 0.5)",
                        border: "1px solid var(--border-subtle)",
                      }}>
                        <div style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "0.75rem",
                          fontWeight: "700",
                          color: "var(--text-secondary)",
                          marginBottom: "6px",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}>
                          <ShieldCheck size={13} color="#10B981" />
                          <span>Verified Citations ({msg.sources.length})</span>
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                          {msg.sources.map((src, sIdx) => {
                            const isExpanded = expandedSources[`${msg.id}-${sIdx}`];
                            return (
                              <div
                                key={sIdx}
                                style={{
                                  padding: "7px 10px",
                                  borderRadius: "6px",
                                  backgroundColor: "rgba(31, 41, 55, 0.7)",
                                  border: "1px solid var(--border-subtle)",
                                  fontSize: "0.78rem",
                                }}
                              >
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    cursor: "pointer",
                                  }}
                                  onClick={() => toggleSourceExpand(msg.id, sIdx)}
                                >
                                  <div style={{ display: "flex", alignItems: "center", gap: "6px", overflow: "hidden", flex: 1 }}>
                                    <FileText size={13} color="var(--primary)" style={{ flexShrink: 0 }} />
                                    <span style={{ fontWeight: "600", color: "#FFFFFF", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                      {src.filename}
                                    </span>
                                    <span style={{
                                      padding: "1px 5px",
                                      borderRadius: "4px",
                                      backgroundColor: "rgba(255, 255, 255, 0.08)",
                                      fontSize: "0.68rem",
                                      color: "var(--text-secondary)",
                                      flexShrink: 0,
                                    }}>
                                      Page {src.page_number}
                                    </span>
                                    {src.content_type && src.content_type !== "text" && (
                                      <span style={{
                                        padding: "1px 6px",
                                        borderRadius: "4px",
                                        backgroundColor: src.content_type === "table" ? "rgba(6, 182, 212, 0.15)" : src.content_type === "diagram" ? "rgba(168, 85, 247, 0.15)" : "rgba(245, 158, 11, 0.15)",
                                        border: `1px solid ${src.content_type === "table" ? "rgba(6, 182, 212, 0.3)" : src.content_type === "diagram" ? "rgba(168, 85, 247, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                                        color: src.content_type === "table" ? "#22D3EE" : src.content_type === "diagram" ? "#C084FC" : "#FBBF24",
                                        fontSize: "0.65rem",
                                        fontWeight: "600",
                                        textTransform: "uppercase",
                                        letterSpacing: "0.03em",
                                        flexShrink: 0,
                                      }}>
                                        {src.content_type}
                                      </span>
                                    )}
                                  </div>
                                  {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                                </div>

                                {isExpanded && src.snippet && (
                                  <div style={{
                                    marginTop: "6px",
                                    paddingTop: "6px",
                                    borderTop: "1px solid var(--border-subtle)",
                                    fontSize: "0.75rem",
                                    color: "var(--text-secondary)",
                                    fontStyle: "italic",
                                    lineHeight: 1.4,
                                  }}>
                                    "{src.snippet}"
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "10px",
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-medium)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      color: "var(--primary)",
                    }}>
                      <User size={16} />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Thinking Indicator */}
          {loading && (
            <div style={{ display: "flex", gap: "10px", alignSelf: "flex-start" }}>
              <div style={{
                width: "32px",
                height: "32px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}>
                <Sparkles size={16} color="#FFFFFF" />
              </div>

              <div style={{
                padding: "12px 16px",
                borderRadius: "16px 16px 16px 4px",
                backgroundColor: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
              }}>
                <Loader2 size={15} className="spinner" color="var(--primary)" />
                <span>Searching documents & generating grounded response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Box */}
        <div className="glass-card" style={{ padding: "10px 14px", borderRadius: "var(--radius-lg)" }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{ display: "flex", alignItems: "flex-end", gap: "8px" }}
          >
            <textarea
              ref={inputRef}
              className="form-input"
              style={{
                flex: 1,
                minHeight: "42px",
                maxHeight: "120px",
                resize: "none",
                padding: "9px 12px",
                lineHeight: 1.4,
                fontSize: "0.88rem",
              }}
              placeholder="Ask a question about your documents..."
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              rows={1}
              aria-label="Ask a question about your documents"
            />

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !inputQuestion.trim()}
              style={{ padding: "10px 16px", borderRadius: "var(--radius-md)" }}
              aria-label="Send message"
            >
              {loading ? (
                <Loader2 size={16} className="spinner" />
              ) : (
                <>
                  <Send size={15} />
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Reusable Confirm Modal */}
      <ConfirmModal
        isOpen={modalState.isOpen}
        title={modalState.title}
        message={modalState.message}
        confirmText={modalState.confirmText}
        isDanger={modalState.isDanger}
        isLoading={modalState.isLoading}
        onConfirm={modalState.onConfirm}
        onCancel={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}

export default Chat;
