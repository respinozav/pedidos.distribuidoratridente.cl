import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  MicOff,
  Upload,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Plus,
  Trash2,
  Volume2,
  RefreshCw,
  Search,
  ArrowLeft,
  Calendar,
  User,
  ShoppingBag,
  ExternalLink,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import "./pedidosVoz.css";

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

export default function PedidosVoz({ onNavigateToOrders }) {
  const [viewMode, setViewMode] = useState("list"); // 'list' | 'dictado' | 'revision'
  const [loading, setLoading] = useState(false);
  const [pedidosVoz, setPedidosVoz] = useState([]);
  const [metricas, setMetricas] = useState(null);
  const [totalCount, setTotalCount] = useState(0);

  // Filtros de lista
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = `${today.slice(0, 7)}-01`;
  const [filtros, setFiltros] = useState({
    desde: monthStart,
    hasta: today,
    estado: "",
    busqueda: "",
  });

  // Estado de dictado / transcripción
  const [isRecording, setIsRecording] = useState(false);
  const [transcripcion, setTranscripcion] = useState("");
  const [audioUrl, setAudioUrl] = useState(null);
  const [uploadingAudio, setUploadingAudio] = useState(false);
  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Estado de revisión de borrador
  const [borradorActivo, setBorradorActivo] = useState(null);
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null);
  const [direccionesCliente, setDireccionesCliente] = useState([]);
  const [direccionSeleccionadaId, setDireccionSeleccionadaId] = useState("");
  const [lineasPedido, setLineasPedido] = useState([]);
  const [alertaDuplicado, setAlertaDuplicado] = useState(null);
  const [notas, setNotas] = useState("");
  const [savingOrder, setSavingOrder] = useState(false);

  // Catálogo en memoria para agregar productos manualmente si es necesario
  const [catalogoProductos, setCatalogoProductos] = useState([]);
  const [clientesDisponibles, setClientesDisponibles] = useState([]);

  // Modal para ver audio/transcripción de un pedido histórico
  const [modalAudioTexto, setModalAudioTexto] = useState(null);

  useEffect(() => {
    cargarListado();
    cargarMetricas();
    cargarCatalogoBase();
  }, [filtros.desde, filtros.hasta, filtros.estado]);

  async function cargarListado() {
    try {
      setLoading(true);
      const params = {};
      if (filtros.desde) params.fecha_desde = `${filtros.desde}T00:00:00Z`;
      if (filtros.hasta) params.fecha_hasta = `${filtros.hasta}T23:59:59Z`;
      if (filtros.estado) params.estado = filtros.estado;

      const { data } = await api.get("/admin/pedidos-voz", { params });
      setPedidosVoz(data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error("Error al cargar pedidos por voz:", err);
    } finally {
      setLoading(false);
    }
  }

  async function cargarMetricas() {
    try {
      const params = {};
      if (filtros.desde) params.fecha_desde = `${filtros.desde}T00:00:00Z`;
      if (filtros.hasta) params.fecha_hasta = `${filtros.hasta}T23:59:59Z`;
      const { data } = await api.get("/admin/pedidos-voz/metricas", { params });
      setMetricas(data);
    } catch (err) {
      console.error("Error al cargar métricas de voz:", err);
    }
  }

  async function cargarCatalogoBase() {
    try {
      const [resProd, resCli] = await Promise.all([
        api.get("/productos").catch(() => ({ data: [] })),
        api.get("/clientes").catch(() => ({ data: [] })),
      ]);
      setCatalogoProductos(resProd.data || []);
      setClientesDisponibles(resCli.data || []);
    } catch (err) {
      console.error("Error cargando productos/clientes:", err);
    }
  }

  // --- Web Speech API & Grabación de Audio ---
  function iniciarDictado() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      Swal.fire({
        icon: "info",
        title: "Reconocimiento de voz no soportado",
        text: "Tu navegador no soporta Web Speech API de forma nativa. Puedes escribir el texto directamente o subir un archivo de audio de WhatsApp.",
      });
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "es-CL";
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event) => {
        let transcriptFinal = "";
        for (let i = 0; i < event.results.length; i++) {
          transcriptFinal += event.results[i][0].transcript;
        }
        setTranscripcion(transcriptFinal);
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        if (event.error !== "no-speech") {
          setIsRecording(false);
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();

      // Iniciar también MediaRecorder para guardar el audio si se desea
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
          const mediaRecorder = new MediaRecorder(stream);
          audioChunksRef.current = [];
          mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunksRef.current.push(e.data);
          };
          mediaRecorder.onstop = async () => {
            stream.getTracks().forEach((track) => track.stop());
            if (audioChunksRef.current.length > 0) {
              const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
              subirArchivoAudio(audioBlob, "grabacion.webm");
            }
          };
          mediaRecorderRef.current = mediaRecorder;
          mediaRecorder.start();
        }).catch((err) => console.log("Mic media error:", err));
      }
    } catch (err) {
      console.error("Error al iniciar reconocimiento:", err);
      setIsRecording(false);
    }
  }

  function detenerDictado() {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }

  async function subirArchivoAudio(blobOrFile, defaultName = "audio.ogg") {
    try {
      setUploadingAudio(true);
      const formData = new FormData();
      formData.append("file", blobOrFile, blobOrFile.name || defaultName);

      const { data } = await api.post("/admin/pedidos-voz/transcribir-audio", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (data.transcripcion) {
        setTranscripcion(data.transcripcion);
      }
      if (data.audio_url) {
        setAudioUrl(data.audio_url);
      }
    } catch (err) {
      console.error("Error al transcribir audio:", err);
      Swal.fire({
        icon: "error",
        title: "Error al transcribir",
        text: err.response?.data?.detail || "No se pudo transcribir el archivo de audio.",
      });
    } finally {
      setUploadingAudio(false);
    }
  }

  function handleFileSelected(e) {
    const file = e.target.files?.[0];
    if (file) {
      subirArchivoAudio(file);
    }
  }

  // --- Interpretar con IA ---
  async function interpretarDictado() {
    if (!transcripcion.trim()) {
      Swal.fire({
        icon: "warning",
        title: "Dictado vacío",
        text: "Por favor dicta o escribe el pedido antes de interpretar.",
      });
      return;
    }

    try {
      setLoading(true);
      const { data } = await api.post("/admin/pedidos-voz/interpretar", {
        transcripcion: transcripcion.trim(),
        audio_url: audioUrl,
      });

      if (data.estado === "RUIDO") {
        Swal.fire({
          icon: "info",
          title: "Audio no reconocido",
          text: data.mensaje || "Por favor repita el dictado con mayor claridad.",
        });
        return;
      }

      // Preparar pantalla de revisión
      setBorradorActivo(data);
      setClienteSeleccionado(data.cliente || null);
      setDireccionesCliente(data.direcciones || []);
      setDireccionSeleccionadaId(data.direccion_seleccionada_id || (data.direcciones?.[0]?.id || ""));
      setAlertaDuplicado(data.alerta_duplicado || null);
      setLineasPedido(data.lineas || []);
      setNotas("");
      setViewMode("revision");
    } catch (err) {
      console.error("Error interpretando pedido:", err);
      Swal.fire({
        icon: "error",
        title: "Error de interpretación",
        text: err.response?.data?.detail || "Ocurrió un error al interpretar con Gemini. Intente nuevamente.",
      });
    } finally {
      setLoading(false);
    }
  }

  // Cargar borrador existente para revisión
  async function abrirRevisionBorrador(borradorId) {
    try {
      setLoading(true);
      const { data } = await api.get(`/admin/pedidos-voz/${borradorId}`);
      setBorradorActivo(data);
      setClienteSeleccionado(data.cliente || null);
      setNotas(data.notas || "");

      // Cargar direcciones del cliente si existe
      if (data.cliente?.id) {
        const resDir = await api.get(`/direcciones?cliente_id=${data.cliente.id}`).catch(() => ({ data: [] }));
        setDireccionesCliente(resDir.data || []);
        setDireccionSeleccionadaId(data.direccion_id || (resDir.data?.[0]?.id || ""));
      } else {
        setDireccionesCliente([]);
        setDireccionSeleccionadaId("");
      }

      setLineasPedido(data.lineas || []);
      setAlertaDuplicado(null);
      setViewMode("revision");
    } catch (err) {
      console.error("Error abriendo borrador:", err);
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo cargar el borrador seleccionado.",
      });
    } finally {
      setLoading(false);
    }
  }

  // Manejo de líneas en pantalla de revisión
  function cambiarCantidadLinea(index, nuevaCantidad) {
    const qty = Math.max(1, parseInt(nuevaCantidad, 10) || 1);
    const actualizadas = [...lineasPedido];
    actualizadas[index].cantidad = qty;
    actualizadas[index].subtotal = actualizadas[index].precio_unitario * qty;

    // Recalcular alerta de stock si el producto está resuelto
    const prod = actualizadas[index];
    const factor = prod.formato === "caja" ? (prod.cantidad_caja || 1) : 1;
    const unidadesDescontar = qty * factor;
    if (prod.stock_disponible !== undefined && prod.stock_disponible < unidadesDescontar) {
      prod.alerta_stock = true;
      prod.mensaje_stock = `Stock insuficiente: se requieren ${unidadesDescontar} unidades y hay ${prod.stock_disponible} disponibles.`;
    } else {
      prod.alerta_stock = false;
    }

    setLineasPedido(actualizadas);
  }

  function cambiarFormatoLinea(index, nuevoFormato) {
    const actualizadas = [...lineasPedido];
    actualizadas[index].formato = nuevoFormato;
    // Si tiene precio_caja y cambia a caja
    const p = actualizadas[index];
    if (nuevoFormato === "caja" && p.precio_caja) {
      p.precio_unitario = p.precio_caja;
    } else if (p.precio_base_unitario) {
      p.precio_unitario = p.precio_base_unitario;
    }
    p.subtotal = p.precio_unitario * p.cantidad;
    setLineasPedido(actualizadas);
  }

  function seleccionarCandidatoProducto(index, candidato) {
    const actualizadas = [...lineasPedido];
    const linea = actualizadas[index];
    linea.producto_id = candidato.id;
    linea.codigo = candidato.codigo;
    linea.nombre = candidato.nombre;
    linea.precio_base_unitario = candidato.precio_unitario;
    linea.precio_caja = candidato.precio_caja;
    linea.cantidad_caja = candidato.cantidad_caja;
    linea.precio_unitario = linea.formato === "caja" && candidato.precio_caja ? candidato.precio_caja : candidato.precio_unitario;
    linea.subtotal = linea.precio_unitario * linea.cantidad;
    linea.stock_disponible = candidato.stock;
    linea.resuelto = true;
    linea.candidatos = [];

    const factor = linea.formato === "caja" ? (linea.cantidad_caja || 1) : 1;
    if (candidato.stock < linea.cantidad * factor) {
      linea.alerta_stock = true;
      linea.mensaje_stock = `Stock insuficiente: requiere ${linea.cantidad * factor} un. y hay ${candidato.stock} un.`;
    } else {
      linea.alerta_stock = false;
    }

    setLineasPedido(actualizadas);
  }

  function eliminarLinea(index) {
    setLineasPedido(lineasPedido.filter((_, i) => i !== index));
  }

  function agregarLineaManual() {
    setLineasPedido([
      ...lineasPedido,
      {
        id: "manual-" + Date.now(),
        texto_original: "Línea agregada manualmente",
        termino_busqueda: "",
        cantidad: 1,
        formato: "unidad",
        producto_id: null,
        codigo: "",
        nombre: "",
        precio_unitario: 0,
        subtotal: 0,
        alerta_stock: false,
        stock_disponible: 0,
        candidatos: [],
        resuelto: false,
      },
    ]);
  }

  async function cambiarCliente(cliente) {
    setClienteSeleccionado(cliente);
    // Cargar direcciones del cliente
    try {
      const { data } = await api.get(`/direcciones?cliente_id=${cliente.id}`);
      setDireccionesCliente(data || []);
      const principal = data?.find((d) => d.principal) || data?.[0];
      setDireccionSeleccionadaId(principal ? principal.id : "");
    } catch (err) {
      console.error("Error cargando direcciones:", err);
    }
  }

  const totalCalculado = lineasPedido.reduce((sum, l) => sum + (Number(l.subtotal) || 0), 0);

  // --- Confirmar Pedido Definitivo ---
  async function confirmarPedidoFinal() {
    if (!clienteSeleccionado?.id) {
      Swal.fire({
        icon: "warning",
        title: "Cliente no seleccionado",
        text: "Debe identificar o seleccionar un cliente para confirmar el pedido.",
      });
      return;
    }
    if (!direccionSeleccionadaId) {
      Swal.fire({
        icon: "warning",
        title: "Dirección requerida",
        text: "Debe seleccionar una dirección de entrega.",
      });
      return;
    }
    if (lineasPedido.length === 0) {
      Swal.fire({
        icon: "warning",
        title: "Sin productos",
        text: "El pedido debe contener al menos un producto.",
      });
      return;
    }

    const sinResolver = lineasPedido.find((l) => !l.producto_id);
    if (sinResolver) {
      Swal.fire({
        icon: "warning",
        title: "Productos sin seleccionar",
        text: `La línea "${sinResolver.texto_original || sinResolver.termino_busqueda}" no tiene un producto asignado. Por favor elija un candidato o elimine la línea.`,
      });
      return;
    }

    const conStockInsuficiente = lineasPedido.filter((l) => l.alerta_stock);
    if (conStockInsuficiente.length > 0) {
      const confirmStock = await Swal.fire({
        icon: "warning",
        title: "Alerta de Stock Insuficiente",
        html: `Hay ${conStockInsuficiente.length} producto(s) con stock menor al requerido.<br/>¿Desea confirmar el pedido de todas formas?`,
        showCancelButton: true,
        confirmButtonText: "Sí, confirmar pedido",
        cancelButtonText: "Revisar cantidades",
        confirmButtonColor: "#10b981",
      });
      if (!confirmStock.isConfirmed) return;
    }

    try {
      setSavingOrder(true);
      const payload = {
        cliente_id: clienteSeleccionado.id,
        direccion_id: direccionSeleccionadaId,
        lineas: lineasPedido.map((l) => ({
          producto_id: l.producto_id,
          cantidad: l.cantidad,
          formato: l.formato,
        })),
        notas: notas.trim() || null,
      };

      const { data } = await api.post(`/admin/pedidos-voz/${borradorActivo.id || borradorActivo.borrador_id}/confirmar`, payload);

      Swal.fire({
        icon: "success",
        title: "¡Pedido por Voz Creado!",
        html: `El pedido oficial se ha creado exitosamente con origen <b>"voz"</b> y sincronizado con Defontana.<br/><br/><b>Total:</b> ${money.format(data.total)}`,
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#10b981",
      });

      // Recargar y volver a la lista
      setViewMode("list");
      cargarListado();
      cargarMetricas();
    } catch (err) {
      console.error("Error confirmando pedido por voz:", err);
      Swal.fire({
        icon: "error",
        title: "Error al crear pedido",
        text: err.response?.data?.detail || "No se pudo crear el pedido.",
      });
    } finally {
      setSavingOrder(false);
    }
  }

  async function descartarBorrador() {
    const confirm = await Swal.fire({
      icon: "question",
      title: "¿Descartar este borrador?",
      text: "El borrador quedará marcado como Descartado y no se generará ningún pedido en Defontana.",
      showCancelButton: true,
      confirmButtonText: "Sí, descartar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#ef4444",
    });

    if (!confirm.isConfirmed) return;

    try {
      const id = borradorActivo.id || borradorActivo.borrador_id;
      await api.post(`/admin/pedidos-voz/${id}/descartar`);
      Swal.fire({
        icon: "success",
        title: "Borrador descartado",
        timer: 1500,
        showConfirmButton: false,
      });
      setViewMode("list");
      cargarListado();
      cargarMetricas();
    } catch (err) {
      console.error("Error descartando borrador:", err);
    }
  }

  // --- Render según vista ---
  return (
    <div className="pedidos-voz-container">
      {/* Encabezado */}
      <div className="pedidos-voz-header">
        <div>
          <h1>
            <Mic size={28} />
            Pedidos por Voz con IA
          </h1>
          <p>Dicta pedidos en lenguaje natural chileno, revisa con catálogo y stock real, y confirma con origen 'voz'.</p>
        </div>

        {viewMode === "list" ? (
          <button
            type="button"
            className="btn-dictar-cta"
            onClick={() => {
              setTranscripcion("");
              setAudioUrl(null);
              setBorradorActivo(null);
              setViewMode("dictado");
            }}
          >
            <Mic size={20} />
            Dictar nuevo pedido
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-outline-light d-inline-flex align-items-center gap-2"
            onClick={() => setViewMode("list")}
          >
            <ArrowLeft size={18} />
            Volver al listado
          </button>
        )}
      </div>

      {/* VISTA 1: LISTADO E HISTORIAL */}
      {viewMode === "list" && (
        <>
          {/* Bloque resumen de métricas */}
          {metricas && (
            <div className="dashboard-voice-block">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h3 className="h6 font-weight-bold text-uppercase text-secondary m-0">Resumen de Pedidos por Voz del Período</h3>
                <span className="badge bg-success-subtle text-success font-weight-bold">
                  {metricas.porcentaje_ventas_voz}% de las ventas totales
                </span>
              </div>
              <div className="dashboard-voice-metrics">
                <div className="dashboard-voice-metric-card">
                  <span>Dictados Totales</span>
                  <strong>{metricas.dictados_total}</strong>
                  <small>En el período filtrado</small>
                </div>
                <div className="dashboard-voice-metric-card">
                  <span>Confirmados</span>
                  <strong className="text-success">{metricas.confirmados}</strong>
                  <small>Pedidos convertidos a ventas</small>
                </div>
                <div className="dashboard-voice-metric-card">
                  <span>Monto Confirmado</span>
                  <strong>{money.format(metricas.monto_confirmado_voz)}</strong>
                  <small>Total facturado por voz</small>
                </div>
                <div className="dashboard-voice-metric-card">
                  <span>Borradores Pendientes</span>
                  <strong className="text-warning">{metricas.borradores_pendientes_count}</strong>
                  <small>Requieren revisión humana</small>
                </div>
              </div>

              {metricas.borradores_pendientes?.length > 0 && (
                <div className="mt-3 p-3 bg-light rounded-3">
                  <span className="small font-weight-bold text-secondary d-block mb-2">Borradores pendientes de revisión rápida:</span>
                  <div className="d-flex flex-wrap gap-2">
                    {metricas.borradores_pendientes.map((b) => (
                      <button
                        key={b.id}
                        type="button"
                        className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
                        onClick={() => abrirRevisionBorrador(b.id)}
                      >
                        <AlertTriangle size={14} className="text-warning" />
                        <span>{b.cliente_nombre}: {money.format(b.total_estimado)}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Filtros de tabla */}
          <div className="card p-3 border-0 shadow-sm rounded-4">
            <div className="row g-2 align-items-center">
              <div className="col-12 col-md-3">
                <label className="form-label small text-secondary mb-1">Desde</label>
                <input
                  type="date"
                  className="form-control form-control-sm"
                  value={filtros.desde}
                  onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-3">
                <label className="form-label small text-secondary mb-1">Hasta</label>
                <input
                  type="date"
                  className="form-control form-control-sm"
                  value={filtros.hasta}
                  onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-3">
                <label className="form-label small text-secondary mb-1">Estado</label>
                <select
                  className="form-select form-select-sm"
                  value={filtros.estado}
                  onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
                >
                  <option value="">Todos los estados</option>
                  <option value="BORRADOR">Borrador</option>
                  <option value="CONFIRMADO">Confirmado</option>
                  <option value="DESCARTADO">Descartado</option>
                </select>
              </div>
              <div className="col-12 col-md-3 d-flex align-items-end">
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary w-100 d-inline-flex align-items-center justify-content-center gap-1"
                  onClick={() => { cargarListado(); cargarMetricas(); }}
                >
                  <RefreshCw size={14} /> Actualizar
                </button>
              </div>
            </div>
          </div>

          {/* Tabla de pedidos por voz */}
          <div className="card border-0 shadow-sm rounded-4 overflow-hidden">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Fecha y hora</th>
                    <th>Dictado por</th>
                    <th>Cliente</th>
                    <th>Total</th>
                    <th>Estado</th>
                    <th>Correcciones</th>
                    <th>Audio y texto</th>
                    <th className="text-end">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan="8" className="text-center py-4 text-secondary">
                        Cargando pedidos por voz...
                      </td>
                    </tr>
                  ) : pedidosVoz.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="text-center py-5 text-secondary">
                        No hay pedidos por voz registrados en este período.
                      </td>
                    </tr>
                  ) : (
                    pedidosVoz.map((pv) => (
                      <tr key={pv.id}>
                        <td>
                          <span className="small d-block font-weight-bold">
                            {new Date(pv.created_at).toLocaleDateString("es-CL")}
                          </span>
                          <span className="text-secondary small">
                            {new Date(pv.created_at).toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </td>
                        <td>
                          <span className="small">{pv.dictado_por}</span>
                        </td>
                        <td>
                          <strong className="d-block text-dark">{pv.cliente_nombre}</strong>
                          {pv.cliente_alias && <small className="text-muted">Alias: {pv.cliente_alias}</small>}
                        </td>
                        <td>
                          <span className="font-weight-bold text-dark">{money.format(pv.total)}</span>
                        </td>
                        <td>
                          {pv.estado === "CONFIRMADO" && (
                            <span className="badge bg-success-subtle text-success px-2 py-1">Confirmado</span>
                          )}
                          {pv.estado === "BORRADOR" && (
                            <span className="badge bg-warning-subtle text-warning-emphasis px-2 py-1">Borrador</span>
                          )}
                          {pv.estado === "DESCARTADO" && (
                            <span className="badge bg-secondary-subtle text-secondary px-2 py-1">Descartado</span>
                          )}
                        </td>
                        <td>
                          <span className="small text-secondary">
                            {pv.lineas_editadas_count === 0 ? "Sin cambios" : `${pv.lineas_editadas_count} línea(s) editada(s)`}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-info d-inline-flex align-items-center gap-1"
                            onClick={() => setModalAudioTexto(pv)}
                          >
                            <FileText size={14} /> Ver dictado
                          </button>
                        </td>
                        <td className="text-end">
                          {pv.estado === "BORRADOR" ? (
                            <button
                              type="button"
                              className="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"
                              onClick={() => abrirRevisionBorrador(pv.id)}
                            >
                              Revisar y confirmar
                            </button>
                          ) : pv.pedido_id && onNavigateToOrders ? (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-success d-inline-flex align-items-center gap-1"
                              onClick={() => onNavigateToOrders(pv.pedido_id)}
                            >
                              Ver pedido <ExternalLink size={12} />
                            </button>
                          ) : (
                            <span className="text-muted small">-</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* VISTA 2: DICTADO Y CAPTURA */}
      {viewMode === "dictado" && (
        <div className="dictado-card">
          <div className="dictado-controls">
            <div className="mic-button-wrapper">
              <button
                type="button"
                className={`btn-mic-record ${isRecording ? "is-recording" : ""}`}
                onClick={isRecording ? detenerDictado : iniciarDictado}
                title={isRecording ? "Presiona para detener" : "Presiona para hablar"}
              >
                {isRecording ? <MicOff size={38} /> : <Mic size={38} />}
              </button>
            </div>

            <div className="recording-status-text">
              {isRecording ? (
                <>
                  <span className="badge bg-danger rounded-pill">GRABANDO</span>
                  <span>Habla claro: menciona el cliente, dirección y productos con cantidad y formato...</span>
                </>
              ) : (
                <span>Presiona el micrófono para dictar el pedido o sube un audio de WhatsApp</span>
              )}
            </div>

            <div className="upload-audio-box">
              <Upload size={18} />
              <span>O subir nota de voz / audio de WhatsApp:</span>
              <input
                type="file"
                accept="audio/*,.ogg,.mp3,.wav,.m4a,.webm"
                onChange={handleFileSelected}
                disabled={uploadingAudio}
              />
              {uploadingAudio && <span className="text-primary small">Transcribiendo audio con IA...</span>}
            </div>
          </div>

          <div className="mb-3">
            <label className="form-label font-weight-bold d-flex justify-content-between">
              <span>Texto transcrito (puedes editarlo antes de procesar):</span>
              <small className="text-secondary">{transcripcion.length} caracteres</small>
            </label>
            <textarea
              className="transcripcion-textarea"
              placeholder='Ejemplo: "Pedido para Espiga de Oro, despacho a la dirección principal: dos cajas de Pall Mall Azul 20 XL, cuatro displays de Alfajor Classic y una caja de Alfajor Bon o Bon blanco."'
              value={transcripcion}
              onChange={(e) => setTranscripcion(e.target.value)}
            />
          </div>

          <div className="d-flex justify-content-end gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => setViewMode("list")}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn btn-success d-inline-flex align-items-center gap-2 px-4"
              onClick={interpretarDictado}
              disabled={loading || !transcripcion.trim()}
            >
              {loading ? (
                <>
                  <RefreshCw className="animate-spin" size={18} />
                  Interpretando con IA...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} />
                  Interpretar con IA
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* VISTA 3: PANTALLA DE REVISIÓN Y CONFIRMACIÓN */}
      {viewMode === "revision" && (
        <div className="revision-container">
          <div className="revision-header">
            <div>
              <span className="badge bg-primary-subtle text-primary mb-1">REVISIÓN HUMANA OBLIGATORIA</span>
              <h2 className="h4 font-weight-bold text-dark m-0">Confirmación de Pedido por Voz</h2>
              <small className="text-secondary">Verifica el cliente, dirección y cantidades antes de generar el pedido oficial.</small>
            </div>
            <div>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setViewMode("dictado")}
              >
                Volver a dictar
              </button>
            </div>
          </div>

          {/* Alerta de posible duplicado en el mismo día */}
          {alertaDuplicado && (
            <div className="alert-banner warning">
              <AlertTriangle size={24} className="text-warning flex-shrink-0" />
              <div>
                <strong>Aviso de Posible Duplicado</strong>
                <p className="m-0 small">{alertaDuplicado.mensaje}</p>
              </div>
            </div>
          )}

          {/* Sección de Cliente */}
          <div className="card p-3 mb-3 border bg-light-subtle rounded-3">
            <div className="row g-3 align-items-center">
              <div className="col-12 col-md-6">
                <label className="form-label font-weight-bold small text-secondary">Cliente Identificado</label>
                {clienteSeleccionado ? (
                  <div className="d-flex align-items-center justify-content-between p-2 bg-white border rounded">
                    <div>
                      <strong className="d-block text-dark">{clienteSeleccionado.nombre}</strong>
                      <small className="text-secondary">RUT: {clienteSeleccionado.rut || "Sin RUT"} | Alias: {clienteSeleccionado.alias || "-"}</small>
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => setClienteSeleccionado(null)}
                    >
                      Cambiar
                    </button>
                  </div>
                ) : (
                  <div>
                    <select
                      className="form-select form-select-sm"
                      onChange={(e) => {
                        const cli = clientesDisponibles.find((c) => c.id === e.target.value);
                        if (cli) cambiarCliente(cli);
                      }}
                    >
                      <option value="">-- Seleccione un cliente de la cartera --</option>
                      {clientesDisponibles.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre} {c.alias ? `(${c.alias})` : ""} - {c.rut}
                        </option>
                      ))}
                    </select>

                    {/* Candidatos sugeridos por IA */}
                    {borradorActivo?.candidatos_cliente?.length > 0 && (
                      <div className="mt-2">
                        <small className="text-secondary d-block">Opciones sugeridas por el dictado:</small>
                        <div className="candidatos-chips">
                          {borradorActivo.candidatos_cliente.map((cand) => (
                            <button
                              key={cand.id}
                              type="button"
                              className="chip-candidato"
                              onClick={() => cambiarCliente(cand)}
                            >
                              {cand.nombre} ({cand.alias || cand.rut})
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Dirección de despacho */}
              <div className="col-12 col-md-6">
                <label className="form-label font-weight-bold small text-secondary">Dirección de Despacho</label>
                {direccionesCliente.length > 0 ? (
                  <select
                    className="form-select form-select-sm"
                    value={direccionSeleccionadaId}
                    onChange={(e) => setDireccionSeleccionadaId(e.target.value)}
                  >
                    {direccionesCliente.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.direccion} {d.comuna ? `(${d.comuna})` : ""} {d.principal ? "★ Principal" : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="small text-danger m-0">No se encontraron direcciones para este cliente.</p>
                )}
              </div>
            </div>
          </div>

          {/* Tabla de Líneas del Pedido */}
          <div className="table-responsive">
            <table className="lineas-table">
              <thead>
                <tr>
                  <th style={{ width: "40%" }}>Producto</th>
                  <th style={{ width: "15%" }}>Cantidad</th>
                  <th style={{ width: "15%" }}>Formato</th>
                  <th style={{ width: "15%" }}>Precio Unit.</th>
                  <th style={{ width: "15%" }}>Subtotal</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineasPedido.map((linea, index) => (
                  <tr key={linea.id || index}>
                    <td>
                      {linea.resuelto ? (
                        <div>
                          <strong className="d-block text-dark">{linea.nombre}</strong>
                          <small className="text-secondary">Cód: {linea.codigo}</small>
                          {linea.alerta_stock && (
                            <div className="badge-stock low mt-1">
                              <AlertTriangle size={12} /> {linea.mensaje_stock}
                            </div>
                          )}
                          {!linea.alerta_stock && linea.stock_disponible > 0 && (
                            <div className="badge-stock ok mt-1">
                              <CheckCircle2 size={12} /> Stock disp: {linea.stock_disponible} un.
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <span className="badge bg-warning-subtle text-warning-emphasis mb-1">
                            Dictado: "{linea.texto_original}"
                          </span>
                          <select
                            className="form-select form-select-sm"
                            onChange={(e) => {
                              const cand = (linea.candidatos || catalogoProductos).find((p) => p.id === e.target.value);
                              if (cand) seleccionarCandidatoProducto(index, cand);
                            }}
                          >
                            <option value="">-- Selecciona el producto correspondiente --</option>
                            {linea.candidatos?.map((cand) => (
                              <option key={cand.id} value={cand.id}>
                                {cand.nombre} ({cand.codigo}) - Stock: {cand.stock}
                              </option>
                            ))}
                            <optgroup label="Todo el catálogo">
                              {catalogoProductos.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.nombre} ({p.codigo})
                                </option>
                              ))}
                            </optgroup>
                          </select>
                        </div>
                      )}
                    </td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        className="form-control form-control-sm text-center font-weight-bold"
                        value={linea.cantidad}
                        onChange={(e) => cambiarCantidadLinea(index, e.target.value)}
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={linea.formato}
                        onChange={(e) => cambiarFormatoLinea(index, e.target.value)}
                      >
                        <option value="unidad">Unidad</option>
                        <option value="caja">Caja</option>
                        <option value="display">Display</option>
                      </select>
                    </td>
                    <td>
                      <span className="small text-secondary">{money.format(linea.precio_unitario)}</span>
                    </td>
                    <td>
                      <strong className="text-dark">{money.format(linea.subtotal)}</strong>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm btn-link text-danger p-0"
                        onClick={() => eliminarLinea(index)}
                        title="Eliminar producto"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="d-flex justify-content-between align-items-center mb-4">
            <button
              type="button"
              className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
              onClick={agregarLineaManual}
            >
              <Plus size={16} /> Agregar otro producto
            </button>

            <div className="text-end">
              <span className="text-secondary small d-block">TOTAL DEL PEDIDO:</span>
              <strong className="h3 text-success font-weight-bold m-0">{money.format(totalCalculado)}</strong>
            </div>
          </div>

          {/* Notas */}
          <div className="mb-4">
            <label className="form-label small text-secondary">Notas internas o instrucciones de despacho (opcional)</label>
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Ej: Despachar antes de las 14:00 hrs"
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
            />
          </div>

          {/* Botones de Confirmación */}
          <div className="d-flex justify-content-end gap-3 pt-3 border-top">
            <button
              type="button"
              className="btn btn-outline-danger d-inline-flex align-items-center gap-2"
              onClick={descartarBorrador}
            >
              <Trash2 size={18} /> Descartar borrador
            </button>
            <button
              type="button"
              className="btn btn-success d-inline-flex align-items-center gap-2 px-4 py-2 font-weight-bold"
              onClick={confirmarPedidoFinal}
              disabled={savingOrder}
            >
              {savingOrder ? (
                <>
                  <RefreshCw className="animate-spin" size={18} /> Sincronizando con Defontana...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} /> Confirmar Pedido (Crear con origen 'voz')
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* MODAL PARA VER AUDIO Y TEXTO HISTÓRICO */}
      {modalAudioTexto && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content rounded-4 border-0 shadow">
              <div className="modal-header">
                <h5 className="modal-title font-weight-bold">Detalle del Dictado por Voz</h5>
                <button type="button" className="btn-close" onClick={() => setModalAudioTexto(null)}></button>
              </div>
              <div className="modal-body">
                {modalAudioTexto.audio_url && (
                  <div className="mb-3 p-3 bg-light rounded text-center">
                    <label className="form-label small font-weight-bold d-block text-secondary mb-2">
                      <Volume2 size={16} className="d-inline me-1" /> Grabación de Audio
                    </label>
                    <audio controls src={modalAudioTexto.audio_url} className="w-100" />
                  </div>
                )}
                <div>
                  <label className="form-label small font-weight-bold text-secondary">Transcripción Registrada</label>
                  <p className="p-3 bg-light rounded text-dark" style={{ whiteSpace: "pre-wrap", fontSize: "0.95rem" }}>
                    {modalAudioTexto.transcripcion}
                  </p>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setModalAudioTexto(null)}>
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
