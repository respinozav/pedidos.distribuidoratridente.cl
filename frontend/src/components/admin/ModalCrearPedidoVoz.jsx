import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronDown,
  MapPin,
  Mic,
  MicOff,
  Minus,
  Package,
  Plus,
  RotateCcw,
  Search,
  Sparkles,
  Trash2,
  User,
  X,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
});

export default function ModalCrearPedidoVoz({ isOpen, onClose, onOrderCreated }) {
  if (!isOpen) return null;

  // Estados de Clientes
  const [customers, setCustomers] = useState([]);
  const [loadingCustomers, setLoadingCustomers] = useState(false);
  const [customerSearch, setCustomerSearch] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerAddresses, setCustomerAddresses] = useState([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");

  // Estados de Asistente por Voz / Dictado
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [assistantMessage, setAssistantMessage] = useState(
    "Hola, ¿cómo deseas armar el pedido? Puedes dictarme el cliente y los productos con sus cantidades (ej: 'Bolsa camiseta 35x45 5 unidades, Pall Mall Azul 2 cartones y Kent Actron 1 carton')."
  );
  const [ambiguousItems, setAmbiguousItems] = useState([]);

  // Estados del Borrador del Pedido
  const [cartItems, setCartItems] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState([]);
  const [manualSearch, setManualSearch] = useState("");
  const [manualSearchResults, setManualSearchResults] = useState([]);

  // Reconocimiento de Voz nativo
  const recognitionRef = useRef(null);

  // Cargar clientes y catálogo al montar
  useEffect(() => {
    cargarClientes();
    cargarCatalogo();
    inicializarReconocimientoVoz();

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
    };
  }, []);

  const inicializarReconocimientoVoz = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("SpeechRecognition no soportado en este navegador.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "es-CL";

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (event) => {
      let currentTranscript = "";
      for (let i = 0; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }
      setTranscript(currentTranscript);
    };

    rec.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      Swal.fire({
        icon: "info",
        title: "Micrófono no soportado",
        text: "Tu navegador no soporta reconocimiento de voz nativo (Web Speech API). Puedes escribir el dictado directamente en el campo de texto.",
      });
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setTranscript("");
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error(e);
      }
    }
  };

  const cargarClientes = async () => {
    setLoadingCustomers(true);
    try {
      const { data } = await api.get("/clientes");
      setCustomers(data || []);
    } catch (e) {
      console.error("Error al cargar clientes:", e);
    } finally {
      setLoadingCustomers(false);
    }
  };

  const cargarCatalogo = async () => {
    try {
      const { data } = await api.get("/productos");
      setCatalogProducts(data || []);
    } catch (e) {
      console.error("Error al cargar productos:", e);
    }
  };

  // Filtrado de clientes para selector
  const filteredCustomers = customers.filter((c) => {
    if (!customerSearch.trim()) return false;
    const term = customerSearch.toLowerCase();
    const alias = (c.alias || "").toLowerCase();
    const nombre = (c.nombre || "").toLowerCase();
    const rut = (c.rut || "").toLowerCase().replace(/[\.\-]/g, "");
    const cleanTerm = term.replace(/[\.\-]/g, "");
    return (
      alias.includes(term) ||
      nombre.includes(term) ||
      rut.includes(cleanTerm) ||
      (c.celular || "").includes(term)
    );
  });

  const handleSelectCustomer = (client) => {
    setSelectedCustomer(client);
    setCustomerSearch("");
    const dirs = client.direcciones || [];
    setCustomerAddresses(dirs);
    const principalDir = dirs.find((d) => d.principal) || dirs[0];
    setSelectedAddressId(principalDir ? principalDir.id : "");
  };

  // Interpretar Dictado con Backend
  const procesarDictado = async () => {
    if (!transcript.trim()) return;

    setIsProcessingVoice(true);
    try {
      const { data } = await api.post(
        "/pedidos/asistente-ia/interpretar-dictado",
        {
          texto: transcript,
          cliente_id: selectedCustomer ? selectedCustomer.id : null,
        }
      );

      // Si detectó cliente y no teníamos cliente seleccionado
      if (data.cliente_detectado_id && !selectedCustomer) {
        const foundClient = customers.find(
          (c) => c.id === data.cliente_detectado_id
        );
        if (foundClient) {
          handleSelectCustomer(foundClient);
        }
      }

      setAssistantMessage(data.mensaje_asistente || "Dictado procesado.");

      const newAmbiguos = [];
      const newItemsToAdd = [];

      for (const it of data.items || []) {
        if (it.estado === "exacto" && it.producto) {
          newItemsToAdd.push({
            producto: it.producto,
            cantidad: it.cantidad || 1,
            tipo_empaque: it.tipo_empaque || "unidad",
          });
        } else if (it.estado === "multiple" && it.opciones?.length > 0) {
          newAmbiguos.push(it);
        }
      }

      setAmbiguousItems(newAmbiguos);

      // Agregar ítems exactos al carrito
      for (const item of newItemsToAdd) {
        agregarProductoAlBorrador(
          item.producto,
          item.cantidad,
          item.tipo_empaque
        );
      }
    } catch (e) {
      console.error("Error al interpretar dictado:", e);
      setAssistantMessage(
        "Hubo un problema al procesar el dictado. Por favor intenta de nuevo o escribe los productos."
      );
    } finally {
      setIsProcessingVoice(false);
    }
  };

  // Resolver ítem ambiguo seleccionado por el usuario
  const resolverItemAmbiguo = (ambiguo, opcionSeleccionada) => {
    agregarProductoAlBorrador(
      opcionSeleccionada,
      ambiguo.cantidad || 1,
      ambiguo.tipo_empaque || "unidad"
    );
    setAmbiguousItems((prev) => prev.filter((item) => item !== ambiguo));
  };

  // Agregar al borrador del pedido
  const agregarProductoAlBorrador = (prod, cantidad = 1, tipo_empaque = "unidad") => {
    setCartItems((prev) => {
      const index = prev.findIndex(
        (p) => p.id === prod.id && p.tipo_empaque === tipo_empaque
      );

      // Determinar precio según tipo de empaque
      let precioFinal = Number(prod.precio) || 0;
      if (tipo_empaque === "caja" && prod.precio_caja) {
        precioFinal = Number(prod.precio_caja);
      }

      if (index >= 0) {
        const copy = [...prev];
        copy[index] = {
          ...copy[index],
          cantidad: copy[index].cantidad + cantidad,
          subtotal: (copy[index].cantidad + cantidad) * precioFinal,
        };
        return copy;
      }

      return [
        ...prev,
        {
          id: prod.id,
          codigo: prod.codigo,
          nombre: prod.nombre,
          precio_unitario: precioFinal,
          cantidad: cantidad,
          tipo_empaque: tipo_empaque,
          cantidad_caja: prod.cantidad_caja,
          tiene_caja: prod.tiene_caja,
          afecto: Boolean(prod.afecto),
          subtotal: cantidad * precioFinal,
        },
      ];
    });
  };

  const modificarCantidad = (index, delta) => {
    setCartItems((prev) => {
      const copy = [...prev];
      const target = copy[index];
      const newCant = target.cantidad + delta;
      if (newCant <= 0) {
        return copy.filter((_, i) => i !== index);
      }
      target.cantidad = newCant;
      target.subtotal = newCant * target.precio_unitario;
      return copy;
    });
  };

  const eliminarLinea = (index) => {
    setCartItems((prev) => prev.filter((_, i) => i !== index));
  };

  // Búsqueda manual de productos
  useEffect(() => {
    if (!manualSearch.trim()) {
      setManualSearchResults([]);
      return;
    }
    const term = manualSearch.toLowerCase();
    const results = catalogProducts
      .filter(
        (p) =>
          p.activo &&
          ((p.nombre && p.nombre.toLowerCase().includes(term)) ||
            (p.codigo && p.codigo.toLowerCase().includes(term)))
      )
      .slice(0, 8);
    setManualSearchResults(results);
  }, [manualSearch, catalogProducts]);

  // Cálculos de Totales
  const totales = cartItems.reduce(
    (acc, line) => {
      acc.total += line.subtotal;
      if (line.afecto) {
        acc.afecto += line.subtotal;
      } else {
        acc.exento += line.subtotal;
      }
      return acc;
    },
    { afecto: 0, exento: 0, total: 0 }
  );

  // Confirmar y Emitir Pedido
  const handleConfirmarPedido = async () => {
    if (!selectedCustomer) {
      Swal.fire("Atención", "Debes seleccionar un cliente de destino.", "warning");
      return;
    }
    if (!selectedAddressId) {
      Swal.fire(
        "Atención",
        "El cliente seleccionado debe tener al menos una dirección de despacho activa.",
        "warning"
      );
      return;
    }
    if (!cartItems.length) {
      Swal.fire("Atención", "El pedido no contiene productos.", "warning");
      return;
    }

    const confirmRes = await Swal.fire({
      title: "¿Confirmar y Emitir Pedido?",
      html: `
        <div style="text-align: left; font-size: 0.95rem;">
          <p><strong>Cliente:</strong> ${selectedCustomer.alias || selectedCustomer.nombre}</p>
          <p><strong>RUT:</strong> ${selectedCustomer.rut || "N/A"}</p>
          <p><strong>Total Pedido:</strong> <span style="font-size: 1.15rem; color: #16a34a; font-weight: bold;">${money.format(
            totales.total
          )}</span></p>
          <p style="color: #64748b; font-size: 0.85rem;">Se descontará el stock y se sincronizará automáticamente con Defontana ERP.</p>
        </div>
      `,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, emitir pedido",
      cancelButtonText: "Revisar",
      confirmButtonColor: "#0d6efd",
    });

    if (!confirmRes.isConfirmed) return;

    setIsSubmitting(true);
    try {
      const payload = {
        cliente_id: selectedCustomer.id,
        direccion_id: selectedAddressId,
        productos: cartItems.map((line) => ({
          producto_id: line.id,
          cantidad: line.cantidad,
          tipo_empaque: line.tipo_empaque || "unidad",
        })),
      };

      const { data } = await api.post("/pedidos/admin/crear-pedido", payload);

      Swal.fire({
        icon: "success",
        title: "¡Pedido Emitido con Éxito!",
        html: `
          <p>El pedido <strong>#${data.id?.slice(0, 8).toUpperCase()}</strong> fue generado exitosamente.</p>
          ${
            data.folio_defontana_afecto || data.folio_defontana
              ? `<p class="badge bg-success p-2 mt-2">Folio Defontana: ${
                  data.folio_defontana_afecto || data.folio_defontana
                }</p>`
              : ""
          }
        `,
      });

      if (onOrderCreated) {
        onOrderCreated(data);
      }
      onClose();
    } catch (e) {
      console.error("Error al emitir pedido:", e);
      const errorMsg =
        e.response?.data?.detail || "Ocurrió un error al emitir el pedido.";
      Swal.fire("Error", errorMsg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop-custom" role="presentation" style={{ zIndex: 1060 }}>
      <div
        className="category-modal"
        style={{ maxWidth: "980px", width: "95%", maxHeight: "92vh", display: "flex", flexDirection: "column" }}
      >
        {/* Header Modal */}
        <header className="d-flex justify-content-between align-items-center pb-2 border-bottom">
          <div className="d-flex align-items-center gap-2">
            <div
              className="p-2 rounded-circle"
              style={{ backgroundColor: "#eff6ff", color: "#2563eb" }}
            >
              <Sparkles size={22} />
            </div>
            <div>
              <p className="eyebrow mb-0" style={{ color: "#2563eb" }}>
                ASISTENTE TRIDENTE IA
              </p>
              <h2 className="mb-0" style={{ fontSize: "1.35rem" }}>
                Crear Pedido Asistido por Voz
              </h2>
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Cerrar modal"
          >
            <X size={20} />
          </button>
        </header>

        {/* Cuerpo del Modal */}
        <div
          className="modal-body-custom"
          style={{ overflowY: "auto", flex: "1 1 auto", padding: "1.25rem 0.5rem" }}
        >
          {/* PASO 1: Selección de Cliente */}
          <div className="card mb-3 p-3 shadow-sm border-0" style={{ backgroundColor: "#f8fafc" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <strong className="d-flex align-items-center gap-2 text-dark">
                <User size={18} className="text-primary" /> Paso 1: Cliente de Destino
              </strong>
              {selectedCustomer && (
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary py-0"
                  onClick={() => {
                    setSelectedCustomer(null);
                    setCustomerAddresses([]);
                    setSelectedAddressId("");
                  }}
                >
                  Cambiar cliente
                </button>
              )}
            </div>

            {!selectedCustomer ? (
              <div className="position-relative">
                <input
                  type="text"
                  className="form-control"
                  placeholder="Buscar cliente por Razón Social, Alias, RUT o Celular..."
                  value={customerSearch}
                  onChange={(e) => setCustomerSearch(e.target.value)}
                  autoFocus
                />
                {filteredCustomers.length > 0 && (
                  <div
                    className="dropdown-menu show w-100 position-absolute shadow mt-1"
                    style={{ maxHeight: "220px", overflowY: "auto", zIndex: 1070 }}
                  >
                    {filteredCustomers.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        className="dropdown-item d-flex justify-content-between align-items-center py-2 border-bottom"
                        onClick={() => handleSelectCustomer(c)}
                      >
                        <div>
                          <strong>{c.alias || c.nombre}</strong>
                          {c.alias && c.nombre && (
                            <small className="text-muted d-block">{c.nombre}</small>
                          )}
                          <small className="text-secondary">{c.rut || "Sin RUT"}</small>
                        </div>
                        <span className="badge bg-light text-dark border">
                          {c.porcentaje ? `${c.porcentaje}% desc.` : "Precio lista"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                <small className="text-muted mt-1 d-block">
                  Tip: También puedes dictar directamente: <em>"pedido para Minimarket San Jorge..."</em>
                </small>
              </div>
            ) : (
              <div className="row g-2 align-items-center">
                <div className="col-md-7">
                  <div className="p-2 bg-white rounded border">
                    <strong className="d-block text-primary">
                      {selectedCustomer.alias || selectedCustomer.nombre}
                    </strong>
                    <small className="text-secondary d-block">
                      {selectedCustomer.nombre && selectedCustomer.alias ? `${selectedCustomer.nombre} · ` : ""}
                      {selectedCustomer.rut || "Sin RUT"} · Cel: {selectedCustomer.celular || "-"}
                    </small>
                  </div>
                </div>
                <div className="col-md-5">
                  <label className="form-label small text-secondary mb-1">
                    <MapPin size={14} className="me-1" /> Dirección de Despacho
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={selectedAddressId}
                    onChange={(e) => setSelectedAddressId(e.target.value)}
                  >
                    {customerAddresses.map((dir) => (
                      <option key={dir.id} value={dir.id}>
                        {dir.direccion} {dir.comuna ? `(${dir.comuna})` : ""} {dir.principal ? "⭐ Principal" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* PASO 2: Asistente Agéntico por Voz */}
          <div className="card mb-3 p-3 border-0 shadow-sm" style={{ backgroundColor: "#f0fdf4" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <strong className="d-flex align-items-center gap-2" style={{ color: "#166534" }}>
                <Sparkles size={18} /> Paso 2: Dictado por Voz e IA
              </strong>
              {isListening && (
                <span className="badge bg-danger animate-pulse d-flex align-items-center gap-1">
                  🔴 Grabando audio...
                </span>
              )}
            </div>

            {/* Burbuja del Asistente */}
            <div className="p-2 mb-2 rounded bg-white border small" style={{ color: "#334155" }}>
              🤖 <strong>Asistente:</strong> {assistantMessage}
            </div>

            {/* Barra de Micrófono y Transcripción */}
            <div className="d-flex gap-2 align-items-center">
              <button
                type="button"
                className={`btn btn-lg d-flex align-items-center justify-content-center p-3 rounded-circle shadow-sm ${
                  isListening ? "btn-danger pulse-recording" : "btn-primary"
                }`}
                style={{ width: "54px", height: "54px", flexShrink: 0 }}
                onClick={toggleListening}
                title={isListening ? "Detener grabación" : "Iniciar dictado por voz"}
              >
                {isListening ? <MicOff size={24} /> : <Mic size={24} />}
              </button>

              <div className="flex-grow-1 position-relative">
                <input
                  type="text"
                  className="form-control"
                  placeholder={
                    isListening
                      ? "Escuchando... habla ahora..."
                      : "Escribe o dicta aquí tus productos (ej: Bolsa camiseta 5 un, Pall mall 2 cartones...)"
                  }
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      procesarDictado();
                    }
                  }}
                />
              </div>

              <button
                type="button"
                className="btn btn-success d-flex align-items-center gap-1"
                disabled={isProcessingVoice || !transcript.trim()}
                onClick={procesarDictado}
              >
                {isProcessingVoice ? (
                  <RotateCcw size={16} className="animate-spin" />
                ) : (
                  <Sparkles size={16} />
                )}
                Interpretar
              </button>
            </div>

            {/* Desambiguación: Opciones Encontradas */}
            {ambiguousItems.length > 0 && (
              <div className="mt-3 p-3 bg-white rounded border border-warning">
                <strong className="text-warning-emphasis d-flex align-items-center gap-1 mb-2">
                  <AlertCircle size={16} /> Productos con múltiples opciones encontradas:
                </strong>
                {ambiguousItems.map((amb, idx) => (
                  <div key={idx} className="mb-2 p-2 bg-light rounded">
                    <span className="small text-secondary d-block mb-1">
                      Para el dictado: <strong>"{amb.termino_original}"</strong> ({amb.cantidad}{" "}
                      {amb.tipo_empaque}):
                    </span>
                    <div className="d-flex flex-wrap gap-2">
                      {amb.opciones.map((opc) => (
                        <button
                          key={opc.id}
                          type="button"
                          className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1 text-start"
                          onClick={() => resolverItemAmbiguo(amb, opc)}
                        >
                          <Plus size={14} />
                          <span>
                            <strong>{opc.nombre}</strong>{" "}
                            <small className="text-muted">({money.format(opc.precio)})</small>
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* PASO 3: Vista Previa y Borrador de Pedido */}
          <div className="card p-3 border-0 shadow-sm" style={{ backgroundColor: "#f8fafc" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <strong className="text-dark d-flex align-items-center gap-2">
                <Package size={18} className="text-primary" /> Paso 3: Vista Previa del Pedido
              </strong>

              {/* Búsqueda manual rápida */}
              <div className="position-relative" style={{ width: "280px" }}>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="+ Agregar producto manualmente..."
                  value={manualSearch}
                  onChange={(e) => setManualSearch(e.target.value)}
                />
                {manualSearchResults.length > 0 && (
                  <div
                    className="dropdown-menu show w-100 position-absolute shadow mt-1"
                    style={{ maxHeight: "200px", overflowY: "auto", zIndex: 1070 }}
                  >
                    {manualSearchResults.map((prod) => (
                      <button
                        key={prod.id}
                        type="button"
                        className="dropdown-item d-flex justify-content-between align-items-center py-1 small"
                        onClick={() => {
                          agregarProductoAlBorrador(prod, 1, "unidad");
                          setManualSearch("");
                        }}
                      >
                        <span className="text-truncate" style={{ maxWidth: "190px" }}>
                          {prod.nombre}
                        </span>
                        <strong>{money.format(prod.precio)}</strong>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Tabla del Borrador */}
            {cartItems.length === 0 ? (
              <p className="text-secondary text-center py-4 mb-0">
                Aún no has agregado productos. Dicta mediante el micrófono o búscalos manualmente.
              </p>
            ) : (
              <div className="table-responsive bg-white rounded border">
                <table className="table table-sm table-hover mb-0 align-middle">
                  <thead className="table-light small">
                    <tr>
                      <th>Código</th>
                      <th>Producto</th>
                      <th className="text-center">Empaque</th>
                      <th className="text-center" style={{ width: "120px" }}>
                        Cantidad
                      </th>
                      <th className="text-end">Precio Unit.</th>
                      <th className="text-end">Subtotal</th>
                      <th style={{ width: "40px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {cartItems.map((item, idx) => (
                      <tr key={`${item.id}-${item.tipo_empaque}-${idx}`}>
                        <td className="small text-muted">{item.codigo}</td>
                        <td>
                          <strong>{item.nombre}</strong>
                          {item.afecto ? (
                            <span className="badge bg-primary ms-1" style={{ fontSize: "0.65rem" }}>
                              Afecto
                            </span>
                          ) : (
                            <span className="badge bg-secondary ms-1" style={{ fontSize: "0.65rem" }}>
                              Exento
                            </span>
                          )}
                        </td>
                        <td className="text-center">
                          <span
                            className={`badge ${
                              item.tipo_empaque === "caja" ? "bg-info text-dark" : "bg-light text-dark border"
                            }`}
                          >
                            {item.tipo_empaque === "caja"
                              ? `Caja ${item.cantidad_caja ? `x${item.cantidad_caja}` : ""}`
                              : "Unidad"}
                          </span>
                        </td>
                        <td>
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary p-1"
                              style={{ width: "24px", height: "24px", lineHeight: 1 }}
                              onClick={() => modificarCantidad(idx, -1)}
                            >
                              <Minus size={12} />
                            </button>
                            <span className="fw-bold px-2">{item.cantidad}</span>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary p-1"
                              style={{ width: "24px", height: "24px", lineHeight: 1 }}
                              onClick={() => modificarCantidad(idx, 1)}
                            >
                              <Plus size={12} />
                            </button>
                          </div>
                        </td>
                        <td className="text-end">{money.format(item.precio_unitario)}</td>
                        <td className="text-end fw-bold text-success">
                          {money.format(item.subtotal)}
                        </td>
                        <td className="text-center">
                          <button
                            type="button"
                            className="btn btn-sm text-danger p-0"
                            onClick={() => eliminarLinea(idx)}
                            title="Eliminar producto"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Resumen de Totales */}
            {cartItems.length > 0 && (
              <div className="d-flex justify-content-end mt-3">
                <div className="p-3 bg-white rounded border shadow-sm" style={{ minWidth: "260px" }}>
                  <div className="d-flex justify-content-between small text-secondary mb-1">
                    <span>Afecto Neto:</span>
                    <span>{money.format(totales.afecto)}</span>
                  </div>
                  <div className="d-flex justify-content-between small text-secondary mb-1">
                    <span>Exento:</span>
                    <span>{money.format(totales.exento)}</span>
                  </div>
                  <div className="d-flex justify-content-between small text-secondary mb-2">
                    <span>IVA (19%):</span>
                    <span>{money.format(Math.round(totales.afecto * 0.19))}</span>
                  </div>
                  <div className="d-flex justify-content-between border-top pt-2">
                    <strong className="fs-6">Total Pedido:</strong>
                    <strong className="fs-5 text-success">{money.format(totales.total)}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Modal */}
        <footer className="d-flex justify-content-between align-items-center pt-3 border-top">
          <button type="button" className="btn btn-light" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </button>

          <button
            type="button"
            className="btn btn-primary btn-lg d-flex align-items-center gap-2"
            disabled={isSubmitting || !selectedCustomer || cartItems.length === 0}
            onClick={handleConfirmarPedido}
          >
            {isSubmitting ? (
              <>
                <RotateCcw size={18} className="animate-spin" />
                Emitiendo a Defontana...
              </>
            ) : (
              <>
                <CheckCircle2 size={18} />
                Confirmar y Emitir Pedido ({money.format(totales.total)})
              </>
            )}
          </button>
        </footer>
      </div>
    </div>
  );
}

