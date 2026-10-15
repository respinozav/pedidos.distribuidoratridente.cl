import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bot,
  Plus,
  Send,
  Trash2,
  Sparkles,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  ShoppingCart,
  MessageSquare,
  Clock,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Database,
  Cpu,
  Mic,
  MicOff,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import IAChartRenderer from "../../components/admin/ia/IAChartRenderer";
import IAPredictionRenderer from "../../components/admin/ia/IAPredictionRenderer";
import "./agenteTridenteIA.css";

const QUICK_PROMPTS = [
  {
    icon: BarChart3,
    title: "Top 5 Más Vendidos",
    prompt: "Genera un gráfico de barras con los 5 productos más vendidos en los últimos 30 días y sus totales.",
  },
  {
    icon: AlertTriangle,
    title: "Stock Crítico",
    prompt: "¿Cuáles son los productos que tienen stock crítico o menos de 10 unidades? Muestra una lista detallada.",
  },
  {
    icon: TrendingUp,
    title: "Predicción de Reposición",
    prompt: "Analiza el historial de ventas y genera una predicción de compras para reponer stock esta semana.",
  },
  {
    icon: ShoppingCart,
    title: "Resumen de Facturación",
    prompt: "¿Cuál es el resumen de pedidos y facturación global de los últimos 30 días?",
  },
];

export default function AgenteTridenteIA() {
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loadingChats, setLoadingChats] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isListening, setIsListening] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);
  const baseTextBeforeListeningRef = useRef("");

  // Limpiar reconocimiento de voz al desmontar componente
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
    };
  }, []);

  // Alternar dictado por voz (Speech-to-Text)
  const toggleSpeechRecognition = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      Swal.fire({
        icon: "info",
        title: "Navegador no compatible",
        text: "Tu navegador no cuenta con soporte nativo para reconocimiento de voz Web Speech API. Te recomendamos usar Google Chrome, Microsoft Edge o Safari.",
        confirmButtonColor: "#0284c7",
      });
      return;
    }

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "es-CL";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognitionRef.current = recognition;

      baseTextBeforeListeningRef.current = inputMessage;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = 0; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        const speechText = (finalTranscript + " " + interimTranscript).trim();
        const base = baseTextBeforeListeningRef.current.trim();
        const combined = base ? `${base} ${speechText}` : speechText;

        setInputMessage(combined);

        if (textareaRef.current) {
          textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
        }
      };

      recognition.onerror = (event) => {
        console.warn("Reconocimiento de voz:", event.error);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          Swal.fire({
            icon: "warning",
            title: "Permiso de micrófono requerido",
            text: "Por favor permite el acceso al micrófono en la barra de tu navegador para dictar mensajes al Agente Tridente IA.",
            confirmButtonColor: "#0284c7",
          });
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (err) {
      console.error("Error al iniciar reconocimiento de voz:", err);
      setIsListening(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sendingMessage]);

  // Cargar lista de conversaciones
  const loadChats = async (selectFirst = true) => {
    try {
      setLoadingChats(true);
      const res = await api.get("/admin/ia/chats");
      const list = res.data || [];
      setChats(list);

      if (selectFirst && list.length > 0) {
        selectChat(list[0].id);
      } else if (list.length === 0) {
        // Si no tiene chats, crear uno automáticamente
        handleNewChat();
      }
    } catch (err) {
      console.error("Error al cargar chats:", err);
    } finally {
      setLoadingChats(false);
    }
  };

  useEffect(() => {
    loadChats(true);
  }, []);

  // Seleccionar conversación
  const selectChat = async (chatId) => {
    if (!chatId) return;
    setActiveChatId(chatId);
    setLoadingMessages(true);
    try {
      const res = await api.get(`/admin/ia/chats/${chatId}`);
      setMessages(res.data?.mensajes || []);
    } catch (err) {
      console.error("Error al cargar detalle del chat:", err);
      Swal.fire("Error", "No fue posible cargar el historial de la conversación.", "error");
    } finally {
      setLoadingMessages(false);
    }
  };

  // Crear nueva conversación
  const handleNewChat = async () => {
    try {
      const res = await api.post("/admin/ia/chats", { titulo: "Nueva conversación" });
      const newChat = res.data;
      setChats((prev) => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      setMessages([]);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    } catch (err) {
      console.error("Error al crear nueva conversación:", err);
      Swal.fire("Error", "No fue posible iniciar un nuevo chat.", "error");
    }
  };

  // Eliminar conversación
  const handleDeleteChat = async (e, chatId) => {
    e.stopPropagation();
    const result = await Swal.fire({
      title: "¿Eliminar conversación?",
      text: "Se borrará todo el historial de este chat.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#ef4444",
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar",
    });

    if (!result.isConfirmed) return;

    try {
      await api.delete(`/admin/ia/chats/${chatId}`);
      const updated = chats.filter((c) => c.id !== chatId);
      setChats(updated);

      if (activeChatId === chatId) {
        if (updated.length > 0) {
          selectChat(updated[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error("Error al eliminar conversación:", err);
      Swal.fire("Error", "No fue posible eliminar la conversación.", "error");
    }
  };

  // Enviar mensaje
  const handleSendMessage = async (textToSend = null) => {
    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      setIsListening(false);
    }

    const text = (textToSend !== null ? textToSend : inputMessage).trim();
    if (!text || sendingMessage) return;

    let currentChatId = activeChatId;

    // Si no hay chat activo, crear uno primero
    if (!currentChatId) {
      try {
        const resNew = await api.post("/admin/ia/chats", { titulo: "Nueva conversación" });
        currentChatId = resNew.data.id;
        setActiveChatId(currentChatId);
        setChats((prev) => [resNew.data, ...prev]);
      } catch (err) {
        Swal.fire("Error", "No fue posible iniciar el chat.", "error");
        return;
      }
    }

    // Agregar mensaje local del usuario temporalmente
    const tempUserMsg = {
      id: "temp-" + Date.now(),
      chat_id: currentChatId,
      rol: "user",
      contenido: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInputMessage("");
    setSendingMessage(true);

    try {
      const res = await api.post(`/admin/ia/chats/${currentChatId}/mensajes`, {
        mensaje: text,
      });

      const assistantMsg = res.data;
      setMessages((prev) => [...prev, assistantMsg]);

      // Actualizar título de chat en la lista si fue modificado
      setChats((prev) =>
        prev.map((c) =>
          c.id === currentChatId
            ? {
                ...c,
                titulo:
                  c.titulo === "Nueva conversación"
                    ? text.slice(0, 35) + (text.length > 35 ? "..." : "")
                    : c.titulo,
                updated_at: new Date().toISOString(),
              }
            : c
        )
      );
    } catch (err) {
      console.error("Error al enviar mensaje:", err);
      const errorMsg =
        err.response?.data?.detail || "No fue posible obtener respuesta del Agente IA.";
      Swal.fire("Error de Conexión", errorMsg, "error");
      // Agregar mensaje de error visual
      setMessages((prev) => [
        ...prev,
        {
          id: "err-" + Date.now(),
          chat_id: currentChatId,
          rol: "assistant",
          contenido: `⚠️ **Error:** ${errorMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSendingMessage(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeChat = chats.find((c) => c.id === activeChatId);

  return (
    <div className="agente-ia-layout">
      {/* SIDEBAR DE HISTORIAL DE CHATS */}
      <aside className={`agente-ia-sidebar ${sidebarOpen ? "is-open" : "is-collapsed"}`}>
        <div className="sidebar-header">
          <div className="d-flex align-items-center gap-2">
            <div className="ia-logo-pill">
              <Bot size={18} className="text-white" />
            </div>
            <span className="sidebar-title">Historial</span>
          </div>
          <button
            className="btn-new-chat"
            onClick={handleNewChat}
            title="Iniciar nueva conversación"
          >
            <Plus size={16} />
            <span>Nuevo</span>
          </button>
        </div>

        <div className="sidebar-chat-list">
          {loadingChats ? (
            <div className="p-3 text-center text-muted">
              <RefreshCw size={20} className="spinning mb-2" />
              <p className="small mb-0">Cargando chats...</p>
            </div>
          ) : chats.length === 0 ? (
            <div className="p-3 text-center text-muted small">
              No tienes conversaciones previas.
            </div>
          ) : (
            chats.map((chat) => (
              <div
                key={chat.id}
                className={`chat-list-item ${chat.id === activeChatId ? "is-active" : ""}`}
                onClick={() => selectChat(chat.id)}
              >
                <MessageSquare size={16} className="chat-item-icon" />
                <div className="chat-item-info">
                  <span className="chat-item-title">{chat.titulo || "Nueva conversación"}</span>
                  <span className="chat-item-time">
                    {new Date(chat.updated_at || chat.created_at).toLocaleDateString("es-CL", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <button
                  className="chat-item-delete"
                  onClick={(e) => handleDeleteChat(e, chat.id)}
                  title="Eliminar chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div className="badge-agent-info">
            <Database size={13} className="text-info" />
            <span>PostgREST v12</span>
            <span className="dot-divider">•</span>
            <Cpu size={13} className="text-success" />
            <span>Gemini Pro</span>
          </div>
        </div>
      </aside>

      {/* ÁREA PRINCIPAL DEL CHAT */}
      <main className="agente-ia-main">
        {/* HEADER SUPERIOR */}
        <header className="chat-navbar">
          <div className="d-flex align-items-center gap-2">
            <button
              className="btn-toggle-sidebar"
              onClick={() => setSidebarOpen((prev) => !prev)}
              title={sidebarOpen ? "Ocultar panel lateral" : "Mostrar historial"}
            >
              {sidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
            </button>
            <div className="agent-badge-avatar">
              <Bot size={22} className="text-white" />
            </div>
            <div>
              <h2 className="chat-agent-name">
                Agente Tridente IA
                <span className="live-status-pill">
                  <span className="live-status-dot"></span> Online
                </span>
              </h2>
              <p className="chat-agent-subtitle">
                Asistente inteligente de compras, rotación de stock y analítica de ventas
              </p>
            </div>
          </div>

          <div className="chat-navbar-actions">
            <button
              className="btn-clear-chat"
              onClick={handleNewChat}
              title="Nueva conversación"
            >
              <Plus size={15} />
              <span>Nuevo Chat</span>
            </button>
          </div>
        </header>

        {/* CONTENEDOR DE MENSAJES */}
        <div className="chat-messages-container">
          {loadingMessages ? (
            <div className="chat-loading-state">
              <RefreshCw size={28} className="spinning text-primary mb-3" />
              <h5>Cargando conversación...</h5>
              <p className="text-muted small">Recuperando mensajes e informes del agente.</p>
            </div>
          ) : messages.length === 0 ? (
            /* BIENVENIDA Y PROMPTS RÁPIDOS */
            <div className="chat-welcome-screen">
              <div className="welcome-avatar-wrap">
                <Bot size={44} className="text-primary" />
              </div>
              <h3 className="welcome-title">¡Hola! Soy tu Agente Tridente IA</h3>
              <p className="welcome-desc">
                Estoy conectado en tiempo real a las tablas de <strong>productos</strong> y{" "}
                <strong>pedidos</strong> vía <strong>PostgREST</strong>. Puedo responder tus
                preguntas, proyectar necesidades de reposición y graficar métricas clave de la
                distribuidora.
              </p>

              <div className="quick-prompts-grid">
                {QUICK_PROMPTS.map((qp, idx) => {
                  const Icon = qp.icon;
                  return (
                    <button
                      key={idx}
                      className="quick-prompt-card"
                      onClick={() => handleSendMessage(qp.prompt)}
                    >
                      <div className="quick-prompt-icon">
                        <Icon size={18} />
                      </div>
                      <div className="quick-prompt-content">
                        <div className="quick-prompt-title">{qp.title}</div>
                        <div className="quick-prompt-text">{qp.prompt}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* LISTA DE MENSAJES */
            <div className="chat-messages-flow">
              {messages.map((msg, index) => {
                const isUser = msg.rol === "user";
                return (
                  <div
                    key={msg.id || index}
                    className={`chat-message-row ${isUser ? "is-user" : "is-assistant"}`}
                  >
                    {!isUser && (
                      <div className="message-avatar">
                        <Bot size={18} className="text-white" />
                      </div>
                    )}

                    <div className="message-bubble">
                      {/* Badge de herramientas PostgREST utilizadas */}
                      {!isUser && msg.herramientas_usadas && msg.herramientas_usadas.length > 0 && (
                        <div className="tools-used-badge">
                          <Database size={12} className="text-info" />
                          <span>Consultó PostgREST:</span>
                          <strong>{msg.herramientas_usadas.join(", ")}</strong>
                        </div>
                      )}

                      {/* Contenido en Markdown con soporte para Tablas GFM */}
                      <div className="message-text-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.contenido}
                        </ReactMarkdown>
                      </div>

                      {/* Gráficos dinámicos estructurados */}
                      {!isUser &&
                        msg.datos_estructurados &&
                        msg.datos_estructurados.type === "chart" && (
                          <div className="message-dynamic-content">
                            <IAChartRenderer chartData={msg.datos_estructurados} />
                          </div>
                        )}

                      {/* Predicciones dinámicas de reposición */}
                      {!isUser &&
                        msg.datos_estructurados &&
                        msg.datos_estructurados.type === "prediction" && (
                          <div className="message-dynamic-content">
                            <IAPredictionRenderer predictionData={msg.datos_estructurados} />
                          </div>
                        )}

                      <span className="message-timestamp">
                        {new Date(msg.created_at).toLocaleTimeString("es-CL", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* Indicador de escritura y consulta a PostgREST */}
              {sendingMessage && (
                <div className="chat-message-row is-assistant">
                  <div className="message-avatar">
                    <Bot size={18} className="text-white" />
                  </div>
                  <div className="message-bubble is-loading">
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <Sparkles size={14} className="text-warning spinning" />
                      <span className="fw-semibold text-muted small">
                        Consultando datos vía PostgREST y analizando...
                      </span>
                    </div>
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* FORMULARIO DE ENTRADA INFERIOR */}
        <footer className="chat-input-bar">
          {isListening && (
            <div className="speech-listening-banner">
              <span className="speech-pulse-indicator"></span>
              <span className="speech-listening-text">
                Escuchando voz... habla con claridad y se irá escribiendo en tiempo real
              </span>
              <button
                type="button"
                className="btn-stop-speech"
                onClick={toggleSpeechRecognition}
              >
                Pausar dictado
              </button>
            </div>
          )}

          <form
            className={`chat-input-form ${isListening ? "is-voice-listening" : ""}`}
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
          >
            <textarea
              ref={textareaRef}
              rows={1}
              className="chat-textarea"
              placeholder={
                isListening
                  ? "🎙️ Escuchando tu voz... (habla con naturalidad)"
                  : "Pregúntale al Agente Tridente IA sobre stock, ventas o predicciones..."
              }
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sendingMessage}
            />

            {/* BOTÓN MICRÓFONO (SPEECH TO TEXT) */}
            <button
              type="button"
              className={`btn-mic-message ${isListening ? "listening" : ""}`}
              onClick={toggleSpeechRecognition}
              disabled={sendingMessage}
              title={isListening ? "Detener dictado por voz" : "Dictar mensaje por voz"}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>

            {/* BOTÓN ENVIAR */}
            <button
              type="submit"
              className="btn-send-message"
              disabled={!inputMessage.trim() || sendingMessage}
              title="Enviar mensaje"
            >
              <Send size={18} />
            </button>
          </form>

          <div className="chat-disclaimer">
            <span>
              El Agente Tridente IA utiliza Gemini Pro y herramientas de solo lectura sobre
              PostgreSQL / PostgREST para analizar datos y proyecciones.
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}
