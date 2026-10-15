import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Calculator,
  Search,
  Plus,
  Minus,
  Trash2,
  FileText,
  Send,
  Mail,
  Phone,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  UserCheck,
  UserPlus,
  FileDown,
  Building,
  MapPin,
  Hash,
  Clock,
  Sparkles,
  ArrowRight,
  Package,
  X,
  FileSpreadsheet,
  Info,
} from "lucide-react";
import { api } from "../../services/api";
import StockAlertBell from "../../components/admin/StockAlertBell";
import Swal from "sweetalert2";

const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

// =============================================================================
// VALIDACIONES REGEX ESTRICTAS
// =============================================================================
export const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
export const PHONE_REGEX = /^(\+?56)?\s?9\d{8}$/;

export function isValidEmail(email) {
  if (!email || typeof email !== "string") return false;
  return EMAIL_REGEX.test(email.trim());
}

export function isValidPhone(phone) {
  if (!phone || typeof phone !== "string") return false;
  const clean = phone.replace(/[\s\-()]/g, "");
  return PHONE_REGEX.test(clean);
}

export default function CotizadorManager() {
  // ---------------------------------------------------------------------------
  // ESTADO: CLIENTE
  // ---------------------------------------------------------------------------
  const [clientMode, setClientMode] = useState("database"); // "database" | "manual"
  const [clientesList, setClientesList] = useState([]);
  const [isLoadingClients, setIsLoadingClients] = useState(false);
  const [clientSearchQuery, setClientSearchQuery] = useState("");
  const [showClientDropdown, setShowClientDropdown] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);

  const [clientForm, setClientForm] = useState({
    nombre: "",
    rut: "",
    correo: "",
    telefono: "",
    direccion: "",
    comuna: "",
  });

  // ---------------------------------------------------------------------------
  // ESTADO: BUSCADOR DE PRODUCTOS
  // ---------------------------------------------------------------------------
  const [productSearch, setProductSearch] = useState("");
  const [productResults, setProductResults] = useState([]);
  const [isSearchingProducts, setIsSearchingProducts] = useState(false);
  const [showProductDropdown, setShowProductDropdown] = useState(false);
  const productSearchRef = useRef(null);

  // ---------------------------------------------------------------------------
  // ESTADO: ITEMS DE LA COTIZACIÓN
  // ---------------------------------------------------------------------------
  const [quoteItems, setQuoteItems] = useState([]);
  const [validezDias, setValidezDias] = useState(15);
  const [observaciones, setObservaciones] = useState("");
  const [quoteCode, setQuoteCode] = useState(() => {
    return `COT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
  });

  // ---------------------------------------------------------------------------
  // ESTADO: ACCIONES DE DESPACHO
  // ---------------------------------------------------------------------------
  const [emailDestino, setEmailDestino] = useState("");
  const [phoneDestino, setPhoneDestino] = useState("");
  const [mensajeAdicional, setMensajeAdicional] = useState("");
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [isSendingWsp, setIsSendingWsp] = useState(false);

  // ---------------------------------------------------------------------------
  // CARGA INICIAL DE CLIENTES (Para el autocompletado)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;
    async function fetchClients() {
      setIsLoadingClients(true);
      try {
        const res = await api.get("/clientes");
        if (isMounted) {
          setClientesList(Array.isArray(res.data) ? res.data : []);
        }
      } catch (err) {
        console.warn("No fue posible precargar clientes:", err);
      } finally {
        if (isMounted) setIsLoadingClients(false);
      }
    }
    fetchClients();
    return () => {
      isMounted = false;
    };
  }, []);

  // ---------------------------------------------------------------------------
  // FILTRADO DINÁMICO DE CLIENTES
  // ---------------------------------------------------------------------------
  const filteredClients = useMemo(() => {
    const q = clientSearchQuery.trim().toLowerCase();
    if (!q) return clientesList.slice(0, 10);
    return clientesList
      .filter((c) => {
        const nombre = (c.nombre || c.razon_social || "").toLowerCase();
        const rut = (c.rut || "").toLowerCase();
        const email = (c.correo || c.email || "").toLowerCase();
        return nombre.includes(q) || rut.includes(q) || email.includes(q);
      })
      .slice(0, 15);
  }, [clientesList, clientSearchQuery]);

  // Manejar selección de cliente de la BD
  const handleSelectClient = (client) => {
    setSelectedClient(client);
    const nombre = client.nombre || client.razon_social || "";
    const rut = client.rut || "";
    const correo = client.correo || client.email || "";
    const telefono = client.celular || client.telefono || "";
    
    // Buscar dirección principal si existe
    let direccion = "";
    let comuna = "";
    if (Array.isArray(client.direcciones) && client.direcciones.length > 0) {
      const dirPrincipal = client.direcciones.find((d) => d.principal) || client.direcciones[0];
      direccion = dirPrincipal.direccion || "";
      comuna = dirPrincipal.comuna || "";
    }

    setClientForm({
      nombre,
      rut,
      correo,
      telefono,
      direccion,
      comuna,
    });

    if (correo && isValidEmail(correo)) {
      setEmailDestino(correo);
    }
    if (telefono && isValidPhone(telefono)) {
      setPhoneDestino(telefono);
    }

    setClientSearchQuery(nombre);
    setShowClientDropdown(false);
  };

  const handleClearClient = () => {
    setSelectedClient(null);
    setClientSearchQuery("");
    setClientForm({
      nombre: "",
      rut: "",
      correo: "",
      telefono: "",
      direccion: "",
      comuna: "",
    });
    setEmailDestino("");
    setPhoneDestino("");
  };

  // ---------------------------------------------------------------------------
  // BUSCADOR DE PRODUCTOS (Debounced)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const term = productSearch.trim();
    if (term.length < 2) {
      setProductResults([]);
      setShowProductDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearchingProducts(true);
      try {
        const res = await api.get("/admin/productos", {
          params: { search: term, page_size: 15 },
        });
        const items = res.data?.items || (Array.isArray(res.data) ? res.data : []);
        setProductResults(items);
        setShowProductDropdown(true);
      } catch (err) {
        console.error("Error al buscar productos:", err);
      } finally {
        setIsSearchingProducts(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [productSearch]);

  // Cerrar dropdown al hacer clic fuera del buscador
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        productSearchRef.current &&
        !productSearchRef.current.contains(event.target)
      ) {
        setShowProductDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Agregar producto a la cotización
  const handleAddProduct = (product) => {
    setQuoteItems((prev) => {
      const existingIndex = prev.findIndex((item) => item.producto_id === product.id);
      const isCaja = Boolean(product.tiene_caja && product.precio_caja);
      const unitPrice = Number(product.precio) || 0;

      if (existingIndex >= 0) {
        const updated = [...prev];
        const current = updated[existingIndex];
        const newQty = current.cantidad + 1;
        updated[existingIndex] = {
          ...current,
          cantidad: newQty,
          subtotal: newQty * current.precio_unitario,
        };
        return updated;
      }

      return [
        ...prev,
        {
          producto_id: product.id,
          codigo_producto: product.codigo || "",
          nombre_producto: product.nombre || "Producto sin nombre",
          precio_unitario: unitPrice,
          cantidad: 1,
          subtotal: unitPrice,
          afecto: product.afecto !== false,
          tipo_empaque: product.tipo_empaque || (product.tiene_caja ? "caja" : "unidad"),
          cantidad_caja: product.cantidad_caja || null,
          stock_actual: product.cantidad ?? 0,
        },
      ];
    });

    // Mantenemos el dropdown abierto y la búsqueda activa para permitir seleccionar múltiples productos
  };

  // Modificar cantidad de un ítem
  const handleQuantityChange = (index, deltaOrValue) => {
    setQuoteItems((prev) => {
      const updated = [...prev];
      const item = updated[index];
      if (!item) return prev;

      let newQty = 1;
      if (typeof deltaOrValue === "number" && (deltaOrValue === 1 || deltaOrValue === -1)) {
        newQty = Math.max(1, item.cantidad + deltaOrValue);
      } else {
        const parsed = parseInt(deltaOrValue, 10);
        newQty = isNaN(parsed) || parsed < 1 ? 1 : parsed;
      }

      updated[index] = {
        ...item,
        cantidad: newQty,
        subtotal: newQty * item.precio_unitario,
      };
      return updated;
    });
  };

  // Modificar precio unitario de un ítem
  const handlePriceChange = (index, value) => {
    setQuoteItems((prev) => {
      const updated = [...prev];
      const item = updated[index];
      if (!item) return prev;

      const numPrice = Math.max(0, parseFloat(value) || 0);
      updated[index] = {
        ...item,
        precio_unitario: numPrice,
        subtotal: item.cantidad * numPrice,
      };
      return updated;
    });
  };

  // Alternar condición de afecto / exento
  const handleToggleAfecto = (index) => {
    setQuoteItems((prev) => {
      const updated = [...prev];
      if (!updated[index]) return prev;
      updated[index] = {
        ...updated[index],
        afecto: !updated[index].afecto,
      };
      return updated;
    });
  };

  // Eliminar un ítem de la tabla
  const handleRemoveItem = (index) => {
    setQuoteItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  // ---------------------------------------------------------------------------
  // CÁLCULOS GENERALES
  // ---------------------------------------------------------------------------
  const { totalNetoAfecto, totalNetoExento, totalIva, totalGeneral, totalUnidades, totalCajas } = useMemo(() => {
    let netoAfecto = 0;
    let netoExento = 0;
    let unidades = 0;
    let cajas = 0;

    quoteItems.forEach((item) => {
      const sub = Number(item.subtotal) || 0;
      if (item.afecto) {
        netoAfecto += sub;
      } else {
        netoExento += sub;
      }

      if (item.tipo_empaque === "caja") {
        cajas += item.cantidad;
      } else {
        unidades += item.cantidad;
      }
    });

    const iva = Math.round(netoAfecto * 0.19);
    const total = netoAfecto + netoExento + iva;

    return {
      totalNetoAfecto: netoAfecto,
      totalNetoExento: netoExento,
      totalIva: iva,
      totalGeneral: total,
      totalUnidades: unidades,
      totalCajas: cajas,
    };
  }, [quoteItems]);

  // ---------------------------------------------------------------------------
  // CONSTRUCCIÓN DEL PAYLOAD PARA LA API
  // ---------------------------------------------------------------------------
  const buildCotizacionPayload = useCallback(() => {
    const clienteNombre = clientForm.nombre.trim();
    if (!clienteNombre) {
      throw new Error("Debes indicar el nombre del cliente para la cotización.");
    }
    if (quoteItems.length === 0) {
      throw new Error("Debes agregar al menos un producto a la cotización.");
    }

    return {
      codigo: quoteCode,
      cliente_id: selectedClient?.id ? String(selectedClient.id) : null,
      cliente_nombre: clienteNombre,
      cliente_rut: clientForm.rut.trim() || null,
      cliente_correo: clientForm.correo.trim() || null,
      cliente_telefono: clientForm.telefono.trim() || null,
      cliente_direccion: clientForm.direccion.trim() || null,
      cliente_comuna: clientForm.comuna.trim() || null,
      validez_dias: Number(validezDias) || 15,
      observaciones: observaciones.trim() || null,
      items: quoteItems.map((item) => ({
        producto_id: item.producto_id ? String(item.producto_id) : null,
        codigo_producto: item.codigo_producto || "",
        nombre_producto: item.nombre_producto,
        precio_unitario: Number(item.precio_unitario),
        cantidad: Number(item.cantidad),
        subtotal: Number(item.subtotal),
        afecto: Boolean(item.afecto),
        tipo_empaque: item.tipo_empaque || "unidad",
        cantidad_caja: item.cantidad_caja ? Number(item.cantidad_caja) : null,
      })),
    };
  }, [clientForm, selectedClient, quoteCode, validezDias, observaciones, quoteItems]);

  // ---------------------------------------------------------------------------
  // ACCIÓN 1: GENERAR Y DESCARGAR PDF
  // ---------------------------------------------------------------------------
  const handleGenerarPdf = async () => {
    try {
      const payload = buildCotizacionPayload();
      setIsGeneratingPdf(true);

      const response = await api.post("/cotizaciones/pdf", payload, {
        responseType: "blob",
      });

      const blob = new Blob([response.data], { type: "application/pdf" });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;

      // Obtener nombre desde cabecera si está disponible
      const disposition = response.headers["content-disposition"];
      let filename = `Cotizacion_${quoteCode}_${payload.cliente_nombre.replace(/\s+/g, "_")}.pdf`;
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) filename = match[1];
      }

      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      Swal.fire({
        icon: "success",
        title: "¡PDF generado con éxito!",
        text: `El documento ${filename} ha sido descargado.`,
        timer: 3500,
        showConfirmButton: false,
        toast: true,
        position: "top-end",
      });
    } catch (err) {
      console.error("Error al generar PDF:", err);
      const errMsg = err?.response?.data?.detail || err.message || "No fue posible generar el PDF.";
      Swal.fire({
        icon: "error",
        title: "Error al generar cotización",
        text: typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg),
      });
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  // ---------------------------------------------------------------------------
  // ACCIÓN 2: ENVIAR POR CORREO ELECTRÓNICO
  // ---------------------------------------------------------------------------
  const emailValido = isValidEmail(emailDestino);

  const handleEnviarCorreo = async () => {
    if (!emailValido) {
      Swal.fire({
        icon: "warning",
        title: "Correo inválido",
        text: "Por favor ingresa un correo electrónico válido antes de enviar.",
      });
      return;
    }

    try {
      const cotizacion = buildCotizacionPayload();
      setIsSendingEmail(true);

      const res = await api.post("/cotizaciones/enviar-correo", {
        cotizacion,
        destinatario_correo: emailDestino.trim(),
        mensaje_adicional: mensajeAdicional.trim() || null,
      });

      Swal.fire({
        icon: "success",
        title: "Correo enviado",
        text: res.data?.message || `Cotización enviada exitosamente a ${emailDestino}.`,
        confirmButtonColor: "#146CCE",
      });
    } catch (err) {
      console.error("Error al enviar correo:", err);
      const errMsg = err?.response?.data?.detail || err.message || "Error al enviar la cotización por correo.";
      Swal.fire({
        icon: "error",
        title: "Error en el envío",
        text: typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg),
      });
    } finally {
      setIsSendingEmail(false);
    }
  };

  // ---------------------------------------------------------------------------
  // ACCIÓN 3: ENVIAR POR WHATSAPP
  // ---------------------------------------------------------------------------
  const telefonoValido = isValidPhone(phoneDestino);

  const handleEnviarWhatsApp = async () => {
    if (!telefonoValido) {
      Swal.fire({
        icon: "warning",
        title: "Teléfono no válido",
        text: "Por favor ingresa un número móvil chileno válido (+569... o 9 dígitos).",
      });
      return;
    }

    try {
      const cotizacion = buildCotizacionPayload();
      setIsSendingWsp(true);

      const res = await api.post("/cotizaciones/enviar-whatsapp", {
        cotizacion,
        destinatario_telefono: phoneDestino.trim(),
        mensaje_adicional: mensajeAdicional.trim() || null,
      });

      Swal.fire({
        icon: "success",
        title: "WhatsApp enviado",
        text: res.data?.message || `Cotización y PDF enviados exitosamente por WhatsApp.`,
        confirmButtonColor: "#25D366",
      });
    } catch (err) {
      console.error("Error al enviar WhatsApp:", err);
      const errMsg = err?.response?.data?.detail || err.message || "Error al enviar la cotización por WhatsApp.";
      Swal.fire({
        icon: "error",
        title: "Error en envío WhatsApp",
        text: typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg),
      });
    } finally {
      setIsSendingWsp(false);
    }
  };

  // Reiniciar cotización completa
  const handleResetCotizacion = () => {
    if (quoteItems.length > 0) {
      Swal.fire({
        title: "¿Reiniciar cotización?",
        text: "Se limpiará el cliente y todos los productos agregados a la tabla.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#64748b",
        confirmButtonText: "Sí, reiniciar",
        cancelButtonText: "Cancelar",
      }).then((result) => {
        if (result.isConfirmed) {
          handleClearClient();
          setQuoteItems([]);
          setObservaciones("");
          setValidezDias(15);
          setQuoteCode(`COT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
          setMensajeAdicional("");
        }
      });
    } else {
      handleClearClient();
      setQuoteItems([]);
      setObservaciones("");
      setValidezDias(15);
      setQuoteCode(`COT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
      setMensajeAdicional("");
    }
  };

  return (
    <>
      {/* ===================================================================== */}
      {/* 1. TOPBAR ESTÁNDAR TRIDENTE */}
      {/* ===================================================================== */}
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">VENTAS Y COTIZACIONES</p>
          <div className="d-flex align-items-center gap-2">
            <h1>Cotizador</h1>
            <span className="badge bg-primary text-white" style={{ fontSize: "0.75rem", padding: "4px 8px" }}>
              #{quoteCode}
            </span>
          </div>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={handleResetCotizacion}
            title="Limpiar y crear nueva cotización"
          >
            <RefreshCw size={15} />
            <span>Nueva cotización</span>
          </button>
          <StockAlertBell />
        </div>
      </header>

      {/* ===================================================================== */}
      {/* 2. CONTENIDO PRINCIPAL */}
      {/* ===================================================================== */}
      <div className="admin-content dashboard-content p-3 p-md-4">
        {/* Banner Hero */}
        <section className="dashboard-hero mb-3">
          <div>
            <p className="eyebrow">MODULO COMERCIAL</p>
            <h2>Generador y Despacho de Cotizaciones</h2>
            <p>
              Prepara cotizaciones formales para clientes registrados o prospectos rápidos. Calcula totales con IVA,
              descarga el documento oficial en PDF o envíalo directamente por Correo y WhatsApp.
            </p>
          </div>
        </section>

        {/* =================================================================== */}
        {/* SECCIÓN 1: CLIENTE */}
        {/* =================================================================== */}
        <section className="content-panel mb-4">
          <div className="panel-heading border-bottom pb-3 mb-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div>
              <div className="d-flex align-items-center gap-2">
                <span className="badge bg-primary-subtle text-primary p-2 rounded-circle">
                  <UserCheck size={18} />
                </span>
                <h2 className="m-0 fs-5">1. Datos del Cliente</h2>
              </div>
              <p className="text-muted small mb-0 mt-1">
                Selecciona un cliente registrado o ingresa datos para un prospecto libre.
              </p>
            </div>

            {/* Alternar modo */}
            <div className="btn-group" role="group">
              <button
                type="button"
                className={`btn btn-sm ${clientMode === "database" ? "btn-primary" : "btn-outline-primary"}`}
                onClick={() => setClientMode("database")}
              >
                <UserCheck size={15} className="me-1" />
                Cliente Registrado
              </button>
              <button
                type="button"
                className={`btn btn-sm ${clientMode === "manual" ? "btn-primary" : "btn-outline-primary"}`}
                onClick={() => setClientMode("manual")}
              >
                <UserPlus size={15} className="me-1" />
                Ingreso Rápido (Manual)
              </button>
            </div>
          </div>

          {/* Modo: Buscador de Base de Datos */}
          {clientMode === "database" && (
            <div className="mb-3 position-relative">
              <label className="form-label fw-semibold">
                Buscar Cliente Registrado (Nombre, RUT o Correo):
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white">
                  <Search size={16} className="text-muted" />
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Escribe el nombre, RUT o correo para autocompletar..."
                  value={clientSearchQuery}
                  onChange={(e) => {
                    setClientSearchQuery(e.target.value);
                    setShowClientDropdown(true);
                  }}
                  onFocus={() => setShowClientDropdown(true)}
                />
                {selectedClient && (
                  <button
                    type="button"
                    className="btn btn-outline-danger"
                    onClick={handleClearClient}
                    title="Quitar cliente seleccionado"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>

              {/* Dropdown de autocompletado */}
              {showClientDropdown && filteredClients.length > 0 && (
                <div
                  className="dropdown-menu show w-100 position-absolute shadow-sm"
                  style={{
                    top: "100%",
                    zIndex: 1050,
                    maxHeight: "240px",
                    overflowY: "auto",
                    background: "#ffffff",
                    border: "1px solid #cbd5e1",
                  }}
                >
                  {filteredClients.map((c) => {
                    const cName = c.nombre || c.razon_social || "Cliente sin nombre";
                    return (
                      <button
                        key={c.id}
                        type="button"
                        className="dropdown-item d-flex justify-content-between align-items-center py-2 border-bottom"
                        onClick={() => handleSelectClient(c)}
                      >
                        <div>
                          <strong className="d-block text-truncate" style={{ maxWidth: "340px" }}>
                            {cName}
                          </strong>
                          <small className="text-muted">
                            {c.rut ? `RUT: ${c.rut}` : "Sin RUT"} · {c.correo || c.email || "Sin correo"}
                          </small>
                        </div>
                        <span className="badge bg-light text-primary border">Seleccionar</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Formulario de Datos del Cliente (Prellenado o Manual) */}
          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label small fw-semibold">Nombre / Razón Social *</label>
              <input
                type="text"
                className="form-control form-control-sm"
                placeholder="Ej. Comercial Los Alerces SpA"
                value={clientForm.nombre}
                onChange={(e) => {
                  setClientForm((f) => ({ ...f, nombre: e.target.value }));
                  if (clientMode === "manual") setClientSearchQuery(e.target.value);
                }}
                required
              />
            </div>
            <div className="col-md-2">
              <label className="form-label small fw-semibold">RUT / Identificador</label>
              <input
                type="text"
                className="form-control form-control-sm"
                placeholder="76.123.456-7"
                value={clientForm.rut}
                onChange={(e) => setClientForm((f) => ({ ...f, rut: e.target.value }))}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label small fw-semibold">Correo Electrónico</label>
              <input
                type="email"
                className={`form-control form-control-sm ${clientForm.correo && !isValidEmail(clientForm.correo) ? "is-invalid" : ""}`}
                placeholder="cliente@empresa.cl"
                value={clientForm.correo}
                onChange={(e) => {
                  const val = e.target.value;
                  setClientForm((f) => ({ ...f, correo: val }));
                  if (isValidEmail(val)) setEmailDestino(val);
                }}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label small fw-semibold">Teléfono / WhatsApp</label>
              <input
                type="text"
                className={`form-control form-control-sm ${clientForm.telefono && !isValidPhone(clientForm.telefono) ? "is-invalid" : ""}`}
                placeholder="+56912345678"
                value={clientForm.telefono}
                onChange={(e) => {
                  const val = e.target.value;
                  setClientForm((f) => ({ ...f, telefono: val }));
                  if (isValidPhone(val)) setPhoneDestino(val);
                }}
              />
            </div>
            <div className="col-md-8">
              <label className="form-label small fw-semibold">Dirección de Despacho</label>
              <input
                type="text"
                className="form-control form-control-sm"
                placeholder="Av. Providencia 1234, Of. 501"
                value={clientForm.direccion}
                onChange={(e) => setClientForm((f) => ({ ...f, direccion: e.target.value }))}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label small fw-semibold">Comuna / Ciudad</label>
              <input
                type="text"
                className="form-control form-control-sm"
                placeholder="Santiago / Providencia"
                value={clientForm.comuna}
                onChange={(e) => setClientForm((f) => ({ ...f, comuna: e.target.value }))}
              />
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* SECCIÓN 2: BUSCADOR DE PRODUCTOS Y TABLA DE COTIZACIÓN */}
        {/* =================================================================== */}
        <section className="content-panel mb-4">
          <div className="panel-heading border-bottom pb-3 mb-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div>
              <div className="d-flex align-items-center gap-2">
                <span className="badge bg-primary-subtle text-primary p-2 rounded-circle">
                  <Package size={18} />
                </span>
                <h2 className="m-0 fs-5">2. Selección de Productos</h2>
              </div>
              <p className="text-muted small mb-0 mt-1">
                Busca productos por SKU o nombre y agrégalos a la lista de cotización.
              </p>
            </div>
            <span className="badge bg-secondary text-white">
              {quoteItems.length} {quoteItems.length === 1 ? "producto" : "productos"}
            </span>
          </div>

          {/* Buscador de productos */}
          <div className="position-relative mb-4" ref={productSearchRef}>
            <label className="form-label fw-semibold">
              Buscar Producto por Nombre o SKU:
            </label>
            <div className="input-group">
              <span className="input-group-text bg-white">
                <Search size={16} className="text-muted" />
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Ejemplo: 'TRID-001' o 'Bebida 1.5L'..."
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                onFocus={() => {
                  if (productResults.length > 0) setShowProductDropdown(true);
                }}
              />
              {productSearch && (
                <button
                  type="button"
                  className="btn btn-outline-secondary border-start-0"
                  onClick={() => {
                    setProductSearch("");
                    setProductResults([]);
                    setShowProductDropdown(false);
                  }}
                  title="Limpiar búsqueda"
                >
                  <X size={15} />
                </button>
              )}
              {isSearchingProducts && (
                <span className="input-group-text bg-white text-muted">
                  <RefreshCw size={15} className="spinner-border spinner-border-sm" />
                </span>
              )}
            </div>

            {/* Dropdown de productos con soporte para multiselección */}
            {showProductDropdown && productResults.length > 0 && (
              <div
                className="dropdown-menu show w-100 position-absolute shadow-lg"
                style={{
                  top: "100%",
                  zIndex: 1050,
                  maxHeight: "320px",
                  overflowY: "auto",
                  background: "#ffffff",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  marginTop: "4px",
                }}
              >
                {/* Cabecera informativa para multi-selección */}
                <div className="d-flex justify-content-between align-items-center px-3 py-2 bg-light border-bottom text-muted small">
                  <span style={{ fontSize: "0.82rem" }}>
                    Haz clic o presiona <strong>[+]</strong> para agregar varios productos a la cotización:
                  </span>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary py-0 px-2 d-flex align-items-center gap-1"
                    style={{ fontSize: "0.75rem" }}
                    onClick={() => setShowProductDropdown(false)}
                    title="Cerrar lista desplegable"
                  >
                    <span>Listo / Cerrar</span>
                    <X size={13} />
                  </button>
                </div>

                {productResults.map((p) => {
                  const hasCaja = Boolean(p.tiene_caja && p.cantidad_caja);
                  const existingItem = quoteItems.find((item) => item.producto_id === p.id);
                  const qtyInQuote = existingItem ? existingItem.cantidad : 0;

                  return (
                    <div
                      key={p.id}
                      className="dropdown-item d-flex justify-content-between align-items-center py-2 px-3 border-bottom"
                      style={{ cursor: "pointer", transition: "background-color 0.15s ease" }}
                      onClick={() => handleAddProduct(p)}
                    >
                      <div className="d-flex flex-column text-start flex-grow-1 me-2" style={{ minWidth: 0 }}>
                        <strong className="text-truncate text-dark" style={{ maxWidth: "480px" }}>
                          {p.nombre}
                        </strong>
                        <small className="text-muted">
                          SKU: <code className="text-secondary">{p.codigo || "S/C"}</code> · Stock: {p.cantidad} un.
                          {hasCaja && ` · Empaque: Caja x${p.cantidad_caja}`}
                          {p.afecto ? " · Afecto a IVA" : " · Exento"}
                        </small>
                      </div>
                      <div className="d-flex align-items-center gap-2 flex-shrink-0">
                        {qtyInQuote > 0 && (
                          <span
                            className="badge bg-success-subtle text-success border border-success"
                            style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                          >
                            ✓ Agregado (x{qtyInQuote})
                          </span>
                        )}
                        <span className="fw-bold text-primary">{money.format(p.precio)}</span>
                        <button
                          type="button"
                          className="btn btn-sm btn-primary p-1 d-flex align-items-center justify-content-center"
                          style={{ width: "26px", height: "26px", borderRadius: "6px" }}
                          title="Agregar una unidad más"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddProduct(p);
                          }}
                        >
                          <Plus size={15} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Tabla de Productos de la Cotización */}
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: "35%" }}>Producto / SKU</th>
                  <th style={{ width: "18%", textAlign: "center" }}>Cantidad</th>
                  <th style={{ width: "18%" }}>Precio Unit. (CLP)</th>
                  <th style={{ width: "12%", textAlign: "center" }}>IVA</th>
                  <th style={{ width: "12%", textAlign: "right" }}>Subtotal</th>
                  <th style={{ width: "5%", textAlign: "center" }}></th>
                </tr>
              </thead>
              <tbody>
                {quoteItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-4 text-muted">
                      <Package size={32} className="text-secondary opacity-50 mb-2 d-block mx-auto" />
                      Aún no has agregado productos a esta cotización.
                      <small className="d-block text-secondary">
                        Utiliza el buscador superior para seleccionar ítems.
                      </small>
                    </td>
                  </tr>
                ) : (
                  quoteItems.map((item, idx) => (
                    <tr key={item.producto_id || idx}>
                      <td>
                        <strong className="d-block text-dark">{item.nombre_producto}</strong>
                        <small className="text-muted">
                          SKU: <code>{item.codigo_producto || "S/C"}</code>
                          {item.tipo_empaque === "caja" && (
                            <span className="badge bg-info-subtle text-info ms-2">
                              Caja {item.cantidad_caja ? `x${item.cantidad_caja}` : ""}
                            </span>
                          )}
                        </small>
                      </td>
                      <td className="text-center">
                        <div className="d-inline-flex align-items-center gap-1 border rounded p-1 bg-white">
                          <button
                            type="button"
                            className="btn btn-sm btn-light p-1 border-0"
                            onClick={() => handleQuantityChange(idx, -1)}
                          >
                            <Minus size={14} />
                          </button>
                          <input
                            type="number"
                            min="1"
                            step="1"
                            className="form-control form-control-sm text-center border-0 p-0"
                            style={{ width: "45px", fontWeight: "bold" }}
                            value={item.cantidad}
                            onChange={(e) => handleQuantityChange(idx, e.target.value)}
                          />
                          <button
                            type="button"
                            className="btn btn-sm btn-light p-1 border-0"
                            onClick={() => handleQuantityChange(idx, 1)}
                          >
                            <Plus size={14} />
                          </button>
                        </div>
                      </td>
                      <td>
                        <div className="input-group input-group-sm" style={{ maxWidth: "140px" }}>
                          <span className="input-group-text">$</span>
                          <input
                            type="number"
                            min="0"
                            step="1"
                            className="form-control text-end fw-semibold"
                            value={item.precio_unitario}
                            onChange={(e) => handlePriceChange(idx, e.target.value)}
                          />
                        </div>
                      </td>
                      <td className="text-center">
                        <button
                          type="button"
                          className={`btn btn-sm ${item.afecto ? "btn-outline-primary" : "btn-outline-secondary"}`}
                          style={{ fontSize: "0.75rem", padding: "2px 6px" }}
                          onClick={() => handleToggleAfecto(idx)}
                          title="Clic para cambiar entre Afecto y Exento"
                        >
                          {item.afecto ? "Afecto (19%)" : "Exento"}
                        </button>
                      </td>
                      <td className="text-end fw-bold text-dark">
                        {money.format(item.subtotal)}
                      </td>
                      <td className="text-center">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger border-0 p-1"
                          onClick={() => handleRemoveItem(idx)}
                          title="Quitar producto"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Resumen de Totales y Condiciones Comerciales */}
          <div className="row g-3 mt-3 pt-3 border-top">
            {/* Columna Izquierda: Condiciones */}
            <div className="col-md-7">
              <div className="row g-2">
                <div className="col-sm-5">
                  <label className="form-label small fw-semibold">
                    <Clock size={14} className="me-1 text-muted" />
                    Validez de la oferta (días)
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={validezDias}
                    onChange={(e) => setValidezDias(Number(e.target.value))}
                  >
                    <option value={7}>7 días</option>
                    <option value={15}>15 días (estándar)</option>
                    <option value={30}>30 días (1 mes)</option>
                    <option value={60}>60 días</option>
                  </select>
                </div>
                <div className="col-sm-7">
                  <label className="form-label small fw-semibold">Código de Cotización</label>
                  <input
                    type="text"
                    className="form-control form-control-sm text-uppercase fw-semibold"
                    value={quoteCode}
                    onChange={(e) => setQuoteCode(e.target.value.toUpperCase())}
                  />
                </div>
                <div className="col-12 mt-2">
                  <label className="form-label small fw-semibold">Observaciones / Condiciones Comerciales</label>
                  <textarea
                    rows={2}
                    className="form-control form-control-sm"
                    placeholder="Ej. Precios sujetos a confirmación de stock. Forma de pago: Transferencia bancaria."
                    value={observaciones}
                    onChange={(e) => setObservaciones(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Columna Derecha: Tarjeta de Totales */}
            <div className="col-md-5">
              <div className="card bg-light border-0 p-3 shadow-none">
                <div className="d-flex justify-content-between mb-1 small text-muted">
                  <span>Productos:</span>
                  <span>{quoteItems.length} ítems ({totalUnidades} un., {totalCajas} cj.)</span>
                </div>
                <div className="d-flex justify-content-between mb-1 small">
                  <span>Subtotal Neto Afecto:</span>
                  <span className="fw-semibold">{money.format(totalNetoAfecto)}</span>
                </div>
                {totalNetoExento > 0 && (
                  <div className="d-flex justify-content-between mb-1 small">
                    <span>Subtotal Neto Exento:</span>
                    <span className="fw-semibold">{money.format(totalNetoExento)}</span>
                  </div>
                )}
                <div className="d-flex justify-content-between mb-2 small">
                  <span>IVA Estimado (19%):</span>
                  <span className="fw-semibold">{money.format(totalIva)}</span>
                </div>
                <hr className="my-2" />
                <div className="d-flex justify-content-between align-items-center">
                  <span className="fw-bold fs-6">TOTAL COTIZACIÓN:</span>
                  <span className="fw-bold fs-5 text-primary">{money.format(totalGeneral)}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* SECCIÓN 3: GENERACIÓN Y DESPACHO (PDF, CORREO, WHATSAPP) */}
        {/* =================================================================== */}
        <section className="content-panel mb-4">
          <div className="panel-heading border-bottom pb-3 mb-3">
            <div className="d-flex align-items-center gap-2">
              <span className="badge bg-primary-subtle text-primary p-2 rounded-circle">
                <Send size={18} />
              </span>
              <h2 className="m-0 fs-5">3. Generación y Envío</h2>
            </div>
            <p className="text-muted small mb-0 mt-1">
              Descarga el PDF oficial con el formato de Pedidos o envíalo directamente al cliente por Correo o WhatsApp.
            </p>
          </div>

          <div className="row g-4">
            {/* Tarjeta PDF */}
            <div className="col-lg-4">
              <div className="card h-100 border p-3 bg-white shadow-sm d-flex flex-column justify-content-between">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-2 text-primary">
                    <FileDown size={22} />
                    <h3 className="fs-6 m-0 fw-bold">Descarga de Documento</h3>
                  </div>
                  <p className="text-muted small">
                    Genera un PDF oficial idéntico al formato de Pedidos de Distribuidora Tridente, listo para imprimir
                    o archivar.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary w-100 d-flex align-items-center justify-content-center gap-2 mt-3"
                  onClick={handleGenerarPdf}
                  disabled={isGeneratingPdf || quoteItems.length === 0}
                >
                  {isGeneratingPdf ? (
                    <>
                      <RefreshCw size={17} className="spinner-border spinner-border-sm" />
                      Generando PDF...
                    </>
                  ) : (
                    <>
                      <FileDown size={17} />
                      Generar PDF
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Tarjeta Envío por Correo */}
            <div className="col-lg-4">
              <div className="card h-100 border p-3 bg-white shadow-sm d-flex flex-column justify-content-between">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-2 text-primary">
                    <Mail size={22} />
                    <h3 className="fs-6 m-0 fw-bold">Envío por Correo</h3>
                  </div>
                  <p className="text-muted small mb-2">
                    Adjunta el PDF oficial y lo envía al correo indicado usando el servidor SMTP.
                  </p>
                  <label className="form-label small fw-semibold">Correo destinatario:</label>
                  <input
                    type="email"
                    className={`form-control form-control-sm ${emailDestino && !emailValido ? "is-invalid" : emailValido ? "is-valid" : ""}`}
                    placeholder="contacto@cliente.cl"
                    value={emailDestino}
                    onChange={(e) => setEmailDestino(e.target.value)}
                  />
                  {emailDestino && !emailValido && (
                    <small className="text-danger d-block mt-1">Formato de correo no válido</small>
                  )}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary w-100 d-flex align-items-center justify-content-center gap-2 mt-3"
                  onClick={handleEnviarCorreo}
                  disabled={isSendingEmail || !emailValido || quoteItems.length === 0}
                >
                  {isSendingEmail ? (
                    <>
                      <RefreshCw size={17} className="spinner-border spinner-border-sm" />
                      Enviando Correo...
                    </>
                  ) : (
                    <>
                      <Mail size={17} />
                      Enviar por Correo
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Tarjeta Envío por WhatsApp */}
            <div className="col-lg-4">
              <div className="card h-100 border p-3 bg-white shadow-sm d-flex flex-column justify-content-between">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-2 text-success">
                    <MessageSquare size={22} />
                    <h3 className="fs-6 m-0 fw-bold">Envío por WhatsApp</h3>
                  </div>
                  <p className="text-muted small mb-2">
                    Envía el documento PDF y un resumen estructurado al cliente vía Evolution API.
                  </p>
                  <label className="form-label small fw-semibold">Teléfono destinatario (Chile):</label>
                  <input
                    type="tel"
                    className={`form-control form-control-sm ${phoneDestino && !telefonoValido ? "is-invalid" : telefonoValido ? "is-valid" : ""}`}
                    placeholder="+56912345678 o 912345678"
                    value={phoneDestino}
                    onChange={(e) => setPhoneDestino(e.target.value)}
                  />
                  {phoneDestino && !telefonoValido && (
                    <small className="text-danger d-block mt-1">
                      Debe ser número móvil chileno (+569... o 9 dígitos)
                    </small>
                  )}
                </div>
                <button
                  type="button"
                  className="btn btn-success text-white w-100 d-flex align-items-center justify-content-center gap-2 mt-3"
                  onClick={handleEnviarWhatsApp}
                  disabled={isSendingWsp || !telefonoValido || quoteItems.length === 0}
                >
                  {isSendingWsp ? (
                    <>
                      <RefreshCw size={17} className="spinner-border spinner-border-sm" />
                      Enviando WhatsApp...
                    </>
                  ) : (
                    <>
                      <MessageSquare size={17} />
                      Enviar por WhatsApp
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Mensaje adicional opcional para Correo y WhatsApp */}
          <div className="mt-3">
            <label className="form-label small fw-semibold">
              Mensaje o nota adicional para el envío (opcional):
            </label>
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Ej. Estimado cliente, adjuntamos la cotización solicitada el día de hoy..."
              value={mensajeAdicional}
              onChange={(e) => setMensajeAdicional(e.target.value)}
            />
          </div>
        </section>
      </div>
    </>
  );
}
