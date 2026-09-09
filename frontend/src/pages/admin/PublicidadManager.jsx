import React, { useState, useEffect } from "react";
import {
  Megaphone,
  Plus,
  Pencil,
  Trash2,
  X,
  Save,
  CheckCircle2,
  AlertCircle,
  Eye,
  Package,
  Layers,
  Image as ImageIcon,
  Sparkles,
  Tag,
  Palette,
  Mail,
  Send,
  Users,
  CheckSquare,
  Square,
  Search,
  ShieldCheck,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import PromoBannerCarousel from "../../components/PromoBannerCarousel";
import StockAlertBell from "../../components/admin/StockAlertBell";
import {
  formatImageSrc,
  getBannerTheme,
  BANNER_COLOR_PRESETS,
} from "../../utils/imageHelper";

export default function PublicidadManager() {
  const [publicidades, setPublicidades] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);

  // Modal Campaña de Correo State
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [selectedBannerForEmail, setSelectedBannerForEmail] = useState(null);
  const [emailSubject, setEmailSubject] = useState("");
  const [emailCustomMessage, setEmailCustomMessage] = useState("");
  const [targetMode, setTargetMode] = useState("all"); // "all" | "individual"
  const [selectedClientIds, setSelectedClientIds] = useState(new Set());
  const [clientSearch, setClientSearch] = useState("");
  const [clientsList, setClientsList] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);

  // Form Fields
  const [formData, setFormData] = useState({
    producto_id: "",
    titulo: "",
    subtitulo: "",
    etiqueta_1: "DESTACADO",
    etiqueta_roja: "PROMOCIÓN",
    texto_boton: "Aprovechar Beneficio →",
    color_fondo: "#082620",
    orden: 0,
  });

  const [selectedProduct, setSelectedProduct] = useState(null);
  const [brokenImages, setBrokenImages] = useState({});

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const resPubs = await api.get("/admin/publicidades");
      setPublicidades(resPubs.data || []);
    } catch (err) {
      setError("No fue posible cargar las publicidades.");
    }

    try {
      const resProds = await api.get("/admin/productos", { params: { page: 1, page_size: 500 } });
      setProducts(resProds.data.items || []);
    } catch (err) {
      console.warn("No fue posible cargar el selector de productos", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function getNextCorrelativeOrder() {
    if (!publicidades || publicidades.length === 0) return 1;
    const maxOrder = Math.max(0, ...publicidades.map((p) => Number(p.orden) || 0));
    return maxOrder + 1;
  }

  function handleOpenCreate() {
    setEditingId(null);
    const firstProd = products.length > 0 ? products[0] : null;
    setSelectedProduct(firstProd);
    const nextOrder = getNextCorrelativeOrder();
    setFormData({
      producto_id: firstProd ? firstProd.id : "",
      titulo: firstProd ? `OFERTA ${firstProd.nombre.toUpperCase()}` : "",
      subtitulo: "Asegura tus unidades a un precio preferencial directamente en tu pedido.",
      etiqueta_1: "DESTACADO",
      etiqueta_roja: "PROMOCIÓN",
      texto_boton: "Aprovechar Beneficio →",
      color_fondo: "#082620",
      orden: nextOrder,
    });
    setIsModalOpen(true);
  }

  function handleOpenEdit(pub) {
    setEditingId(pub.id);
    const prod = products.find((p) => p.id === pub.producto_id) || pub.producto || null;
    setSelectedProduct(prod);

    setFormData({
      producto_id: pub.producto_id || (prod ? prod.id : ""),
      titulo: pub.titulo || "",
      subtitulo: pub.subtitulo || "",
      etiqueta_1: pub.etiqueta_1 || "",
      etiqueta_roja: pub.etiqueta_roja || "PROMOCIÓN",
      texto_boton: pub.texto_boton || "Aprovechar Beneficio →",
      color_fondo: pub.color_fondo || "#082620",
      orden: pub.orden ?? 1,
    });
    setIsModalOpen(true);
  }

  function handleProductSelect(e) {
    const prodId = e.target.value;
    const prod = products.find((p) => p.id === prodId) || null;
    setSelectedProduct(prod);
    setFormData((prev) => ({
      ...prev,
      producto_id: prodId || "",
      titulo: prod ? `OFERTA ${prod.nombre.toUpperCase()}` : prev.titulo,
    }));
  }

  function handleOrderBlur() {
    const entered = parseInt(formData.orden, 10);
    const nextCorrelative = getNextCorrelativeOrder();
    if (isNaN(entered) || entered <= 0) {
      setFormData((prev) => ({ ...prev, orden: nextCorrelative }));
    }
  }

  // --- Handlers Campaña de Correo Electrónico ---
  async function handleOpenEmailModal(pub) {
    setSelectedBannerForEmail(pub);
    setEmailSubject(`Promoción: ${pub.titulo}`);
    setEmailCustomMessage("");
    setTargetMode("all");
    setSelectedClientIds(new Set());
    setClientSearch("");
    setIsEmailModalOpen(true);

    if (clientsList.length === 0) {
      setLoadingClients(true);
      try {
        const res = await api.get("/clientes");
        const allClients = res.data || [];
        const withEmail = allClients.filter(
          (c) => c.activo && c.correo && c.correo.includes("@") && c.correo.trim() !== ""
        );
        withEmail.sort((a, b) => (a.nombre || "").localeCompare(b.nombre || ""));
        setClientsList(withEmail);
      } catch (err) {
        console.error("Error al cargar lista de clientes:", err);
      } finally {
        setLoadingClients(false);
      }
    }
  }

  function toggleClientSelection(clientId) {
    setSelectedClientIds((prev) => {
      const next = new Set(prev);
      if (next.has(clientId)) {
        next.delete(clientId);
      } else {
        next.add(clientId);
      }
      return next;
    });
  }

  function handleSelectAllFiltered(filteredList) {
    setSelectedClientIds((prev) => {
      const next = new Set(prev);
      filteredList.forEach((c) => next.add(c.id));
      return next;
    });
  }

  function handleDeselectAllFiltered(filteredList) {
    setSelectedClientIds((prev) => {
      const next = new Set(prev);
      filteredList.forEach((c) => next.delete(c.id));
      return next;
    });
  }

  async function handleSendEmailCampaign() {
    if (!selectedBannerForEmail) return;

    if (!emailSubject.trim()) {
      Swal.fire({
        icon: "warning",
        title: "Asunto requerido",
        text: "Por favor ingresa un asunto para la campaña de correo.",
      });
      return;
    }

    const isAll = targetMode === "all";
    const clientIdsArray = isAll ? [] : Array.from(selectedClientIds);

    if (!isAll && clientIdsArray.length === 0) {
      Swal.fire({
        icon: "warning",
        title: "Destinatarios requeridos",
        text: "Debes seleccionar al menos un cliente de la lista para realizar el envío.",
      });
      return;
    }

    const recipientsCount = isAll ? clientsList.length : clientIdsArray.length;

    if (recipientsCount === 0) {
      Swal.fire({
        icon: "warning",
        title: "Sin destinatarios",
        text: "No se encontraron clientes con correo electrónico válido.",
      });
      return;
    }

    const confirm = await Swal.fire({
      title: "¿Enviar campaña publicitaria?",
      html: `
        <div style="text-align:left;font-size:0.92rem;line-height:1.5;">
          <p style="margin-bottom:0.6rem;">Se despachará la promoción <strong>"${selectedBannerForEmail.titulo}"</strong> a <strong>${recipientsCount} cliente(s)</strong> con correo registrado.</p>
          <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:10px 12px;color:#166534;font-size:0.84rem;">
            🔒 <strong>Copia oculta (CCO) garantizada:</strong> Cada cliente recibirá un correo individual y confidencial. Nadie verá los correos ni datos de los demás destinatarios.
          </div>
        </div>
      `,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, enviar ahora",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#0284c7",
      cancelButtonColor: "#64748b",
    });

    if (!confirm.isConfirmed) return;

    setSendingEmail(true);
    try {
      const payload = {
        asunto: emailSubject.trim(),
        mensaje_adicional: emailCustomMessage.trim() || null,
        todos: isAll,
        cliente_ids: clientIdsArray,
      };

      const res = await api.post(
        `/admin/publicidades/${selectedBannerForEmail.id}/enviar-correo`,
        payload
      );

      const result = res.data || {};
      const enviados = result.enviados ?? 0;
      const fallidos = result.fallidos ?? 0;

      setIsEmailModalOpen(false);

      if (fallidos === 0) {
        Swal.fire({
          icon: "success",
          title: "¡Campaña enviada!",
          text: `Se enviaron exitosamente ${enviados} correos a los clientes seleccionados.`,
          confirmButtonColor: "#16a34a",
        });
      } else {
        Swal.fire({
          icon: "warning",
          title: "Envío completado con observaciones",
          text: `Enviados: ${enviados}. Fallidos: ${fallidos}. Revisa la configuración SMTP o los logs en Sistema.`,
          confirmButtonColor: "#eab308",
        });
      }
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail || "Ocurrió un error al despachar la campaña de correos.";
      Swal.fire({
        icon: "error",
        title: "Error en el envío",
        text: errorMsg,
        confirmButtonColor: "#dc2626",
      });
    } finally {
      setSendingEmail(false);
    }
  }

  async function handleDelete(pub) {
    const result = await Swal.fire({
      title: "¿Eliminar banner?",
      text: `¿Estás seguro de eliminar permanentemente el banner "${pub.titulo}"?`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#6c757d",
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`/admin/publicidades/${pub.id}`);
        Swal.fire({
          icon: "success",
          title: "Eliminado",
          text: "El banner publicitario fue eliminado de la base de datos.",
          timer: 1500,
          showConfirmButton: false,
        });
        loadData();
      } catch {
        Swal.fire({
          icon: "error",
          title: "Error",
          text: "No fue posible eliminar la publicidad.",
        });
      }
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!formData.producto_id) {
      Swal.fire({
        icon: "warning",
        title: "Producto requerido",
        text: "Debes seleccionar un producto existente para la promoción.",
      });
      return;
    }

    if (!formData.titulo.trim()) {
      Swal.fire({
        icon: "warning",
        title: "Título requerido",
        text: "Por favor ingresa un título para el banner.",
      });
      return;
    }

    let finalOrder = parseInt(formData.orden, 10);
    if (isNaN(finalOrder) || finalOrder <= 0) {
      finalOrder = getNextCorrelativeOrder();
    }

    // Si el orden ingresado ya está en uso por otro banner, asignar automáticamente el siguiente correlativo libre
    const isOrderTaken = publicidades.some(
      (p) => p.id !== editingId && Number(p.orden) === finalOrder
    );
    if (isOrderTaken) {
      finalOrder = getNextCorrelativeOrder();
    }

    setSaving(true);
    try {
      const payload = {
        producto_id: formData.producto_id,
        titulo: formData.titulo.trim(),
        subtitulo: formData.subtitulo?.trim() || null,
        etiqueta_1: formData.etiqueta_1?.trim() || null,
        etiqueta_roja: formData.etiqueta_roja?.trim() || "PROMOCIÓN",
        texto_boton: formData.texto_boton?.trim() || "Aprovechar Beneficio →",
        color_fondo: formData.color_fondo || "#082620",
        orden: finalOrder,
      };

      if (editingId) {
        await api.put(`/admin/publicidades/${editingId}`, payload);
        setNotice("Banner publicitario actualizado correctamente.");
      } else {
        await api.post("/admin/publicidades", payload);
        setNotice("Banner publicitario creado exitosamente.");
      }

      setIsModalOpen(false);
      loadData();
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "Error al guardar",
        text: err.response?.data?.detail || "No fue posible guardar la publicidad.",
      });
    } finally {
      setSaving(false);
    }
  }

  // Previsualización para el Live Preview
  const previewBannerObject = {
    ...formData,
    producto: selectedProduct,
  };

  const enteredOrderNum = parseInt(formData.orden, 10);
  const takenBanner = !isNaN(enteredOrderNum)
    ? publicidades.find((p) => p.id !== editingId && Number(p.orden) === enteredOrderNum)
    : null;
  const isCurrentOrderTaken = Boolean(takenBanner);
  const nextCorrelative = getNextCorrelativeOrder();

  return (
    <div className="admin-publicidad-manager">
      {/* CABECERA SUPERIOR */}
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">MARKETING & PROMOCIONES</p>
          <h1>Publicidad y Banners</h1>
        </div>
        <div className="topbar-actions">
          <button className="btn btn-primary d-flex align-items-center gap-2" onClick={handleOpenCreate}>
            <Plus size={18} />
            Nuevo banner
          </button>
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content">
        {/* RESUMEN DE MÉTRICAS */}
        <section className="admin-summary">
          <div>
            <p className="eyebrow">DESTACADOS DEL CATÁLOGO</p>
            <h2>Banners Promocionales</h2>
            <p>
              Crea anuncios atractivos para destacar ofertas, beneficios de despacho y productos estrella.
            </p>
          </div>
          <div className="d-flex gap-3">
            <div className="summary-metric">
              <span>{publicidades.length}</span>
              <small>Total Banners</small>
            </div>
          </div>
        </section>

        {/* NOTICES & ALERTS */}
        {notice && (
          <div className="alert alert-success alert-dismissible fade show mt-3 mb-0" role="alert">
            <CheckCircle2 size={18} />
            {notice}
            <button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} />
          </div>
        )}
        {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}

        {/* TABLA LISTADO */}
        <section className="content-panel mt-4">
          <div className="panel-heading">
            <div>
              <h2>Banners Registrados</h2>
              <p>Ordena y administra la visualización en el carrusel de tus clientes.</p>
            </div>
            <span className="panel-count">{publicidades.length} registros</span>
          </div>

          {loading ? (
            <p className="text-secondary p-4 mb-0">Cargando banners publicitarios...</p>
          ) : publicidades.length === 0 ? (
            <div className="text-center p-5 text-secondary">
              <Megaphone size={48} className="mb-3 opacity-50 text-emerald-500" />
              <p className="mb-2">Aún no has creado ningún banner publicitario.</p>
              <button className="btn btn-outline-primary btn-sm" onClick={handleOpenCreate}>
                <Plus size={16} />
                Crear el primer banner
              </button>
            </div>
          ) : (
            <div className="promo-table mt-4">
              <div className="promo-table-head">
                <span>Orden</span>
                <span>Banner / Producto</span>
                <span>Subtítulo</span>
                <span>Tag Superior</span>
                <span>Tag Rojo</span>
                <span>Color</span>
                <span>Acciones</span>
              </div>
              {publicidades.map((pub) => {
                const rawProdImg = pub.producto?.imagen_url;
                const prodImg = formatImageSrc(rawProdImg);
                const isImgBroken = brokenImages[pub.id] || !prodImg;
                const pubTheme = getBannerTheme(pub.color_fondo || "#082620");

                return (
                  <div className="promo-row" key={pub.id}>
                    {/* 1. Orden */}
                    <div>
                      <span className="category-order-badge">{pub.orden ?? 0}</span>
                    </div>

                    {/* 2. Banner & Producto vinculado con imagen */}
                    <div className="product-name" style={{ minWidth: 0, overflow: "hidden" }}>
                      <span className="product-thumb">
                        {prodImg && !isImgBroken ? (
                          <img
                            src={prodImg}
                            alt={pub.producto?.nombre || pub.titulo}
                            onError={() => setBrokenImages((prev) => ({ ...prev, [pub.id]: true }))}
                          />
                        ) : (
                          <Package size={18} />
                        )}
                      </span>
                      <div className="text-truncate" style={{ minWidth: 0 }}>
                        <strong className="d-block text-truncate">{pub.titulo}</strong>
                        <small className="d-block text-truncate text-muted">
                          {pub.producto ? `[${pub.producto.codigo}] ${pub.producto.nombre}` : "Sin producto vinculado"}
                        </small>
                      </div>
                    </div>

                    {/* 3. Subtítulo con puntos suspensivos para que no pase a la siguiente columna */}
                    <div style={{ minWidth: 0, overflow: "hidden" }}>
                      <span className="promo-subtitulo-cell" title={pub.subtitulo || ""}>
                        {pub.subtitulo || "-"}
                      </span>
                    </div>

                    {/* 4. Tag Superior */}
                    <div className="d-flex align-items-center" style={{ minWidth: 0, overflow: "hidden" }}>
                      {pub.etiqueta_1 ? (
                        <span
                          style={{
                            background: pubTheme.badgeBg || pubTheme.tagBg,
                            border: `1px solid ${pubTheme.badgeBorder || pubTheme.tagBorder}`,
                            color: pubTheme.badgeColor || pubTheme.tagColor,
                            borderRadius: "99px",
                            fontSize: "0.70rem",
                            fontWeight: 800,
                            height: "26px",
                            padding: "0 0.6rem",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            whiteSpace: "nowrap",
                            maxWidth: "100%",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            textTransform: "uppercase",
                            letterSpacing: "0.02em",
                            lineHeight: 1,
                            boxSizing: "border-box",
                          }}
                          title={pub.etiqueta_1}
                        >
                          {pub.etiqueta_1}
                        </span>
                      ) : (
                        <span className="text-muted" style={{ fontSize: "0.75rem" }}>-</span>
                      )}
                    </div>

                    {/* 5. Tag Rojo */}
                    <div className="d-flex align-items-center">
                      <span
                        style={{
                          background: "#fee2e2",
                          color: "#dc2626",
                          border: "1px solid #fca5a5",
                          borderRadius: "99px",
                          fontSize: "0.70rem",
                          fontWeight: 800,
                          height: "26px",
                          padding: "0 0.55rem",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          textTransform: "uppercase",
                          letterSpacing: "0.02em",
                          whiteSpace: "nowrap",
                          lineHeight: 1,
                          boxSizing: "border-box",
                        }}
                      >
                        {pub.etiqueta_roja || "PROMOCIÓN"}
                      </span>
                    </div>

                    {/* 6. Color del Banner */}
                    <div>
                      <div
                        className="promo-theme-badge"
                        style={{
                          background: `linear-gradient(135deg, ${pubTheme.bgStart} 0%, ${pubTheme.bgEnd} 100%)`,
                          borderRadius: "7px",
                          padding: "0.3rem 0.55rem",
                          border: "1px solid rgba(255, 255, 255, 0.12)",
                          boxShadow: "0 2px 5px rgba(0, 0, 0, 0.18)",
                          display: "inline-flex",
                          flexDirection: "column",
                          gap: "2px",
                          width: "100%",
                          maxWidth: "115px",
                          minHeight: "44px",
                          justifyContent: "center",
                        }}
                        title={`Tema: ${pubTheme.name || pubTheme.id} (${pub.color_fondo || "#082620"})`}
                      >
                        <div className="d-flex align-items-center justify-content-between w-100">
                          <span
                            style={{
                              fontSize: "0.62rem",
                              fontWeight: 800,
                              color: pubTheme.tagColor,
                              textTransform: "uppercase",
                              letterSpacing: "0.03em",
                              lineHeight: 1,
                            }}
                          >
                            {pubTheme.id || "TEMA"}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            color: "#ffffff",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            lineHeight: 1.15,
                          }}
                        >
                          {pubTheme.name || pubTheme.id}
                        </span>
                        <div
                          style={{
                            height: "3px",
                            borderRadius: "1.5px",
                            background: pubTheme.btnBackground,
                            width: "100%",
                            marginTop: "2px",
                          }}
                        />
                      </div>
                    </div>

                    {/* 7. Acciones */}
                    <div className="customer-actions">
                      <button
                        type="button"
                        className="icon-button category-edit text-primary"
                        onClick={() => handleOpenEmailModal(pub)}
                        aria-label={`Enviar por correo ${pub.titulo}`}
                        title="Enviar campaña por correo electrónico"
                      >
                        <Mail size={15} />
                      </button>
                      <button
                        type="button"
                        className="icon-button category-edit"
                        onClick={() => handleOpenEdit(pub)}
                        aria-label={`Editar ${pub.titulo}`}
                        title="Editar banner"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        type="button"
                        className="icon-button category-edit text-danger"
                        onClick={() => handleDelete(pub)}
                        aria-label={`Eliminar ${pub.titulo}`}
                        title="Eliminar banner"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* MODAL CREACIÓN / EDICIÓN CON LIVE PREVIEW */}
      {isModalOpen && (
        <div className="modal-backdrop-custom promo-modal-backdrop" role="presentation">
          <form
            className="category-modal promo-editor-modal"
            onSubmit={handleSubmit}
            role="dialog"
            aria-modal="true"
            aria-labelledby="promo-modal-title"
          >
            <header>
              <div>
                <p className="eyebrow">MARKETING & PROMOCIONES</p>
                <h2 id="promo-modal-title">
                  {editingId ? "Editar Banner de Promoción" : "Nuevo Banner de Promoción"}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setIsModalOpen(false)}
                aria-label="Cerrar modal"
              >
                <X size={20} />
              </button>
            </header>

            <div className="modal-body-custom">
                {/* SECCIÓN VISTA PREVIA EN VIVO (LIVE PREVIEW) */}
                <div className="promo-live-preview-box mb-4">
                  <div className="promo-live-preview-header">
                    <div className="d-flex align-items-center gap-2">
                      <Eye size={16} className="text-emerald-500" />
                      <strong>Vista Previa en Tiempo Real</strong>
                    </div>
                    <small className="text-muted">
                      Así se verá este banner en el carrusel de tus clientes
                    </small>
                  </div>
                  <div className="promo-live-preview-render">
                    <PromoBannerCarousel
                      previewBanner={previewBannerObject}
                      isPreview={true}
                    />
                  </div>
                </div>

                {/* CAMPOS DEL FORMULARIO */}
                <div className="row g-3">
                  {/* 1. Selector de Producto Existente Obligatorio */}
                  <div className="col-md-12">
                    <label className="form-label fw-bold">
                      Producto en Promoción * <small className="text-muted fw-normal">(Se utilizará la foto, código y precio del producto)</small>
                    </label>
                    <select
                      className="form-select"
                      value={formData.producto_id || ""}
                      onChange={handleProductSelect}
                      required
                    >
                      <option value="">-- Selecciona un producto del catálogo --</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          [{p.codigo}] {p.nombre} — ${Number(p.precio).toLocaleString("es-CL")}
                        </option>
                      ))}
                    </select>

                    {/* Resumen del producto seleccionado con foto */}
                    {selectedProduct && (
                      <div className="d-flex align-items-center gap-3 p-2 mt-2 bg-light rounded border">
                        <div className="pub-table-thumb" style={{ width: "48px", height: "48px" }}>
                          {formatImageSrc(selectedProduct.imagen_url) ? (
                            <img
                              src={formatImageSrc(selectedProduct.imagen_url)}
                              alt={selectedProduct.nombre}
                            />
                          ) : (
                            <div className="pub-table-thumb-fallback">
                              <Package size={20} />
                            </div>
                          )}
                        </div>
                        <div className="flex-grow-1">
                          <strong className="d-block text-dark font-medium" style={{ fontSize: "0.92rem" }}>
                            {selectedProduct.nombre}
                          </strong>
                          <div className="d-flex gap-3 text-muted" style={{ fontSize: "0.82rem" }}>
                            <span>Cód: <strong>{selectedProduct.codigo}</strong></span>
                            <span>Precio: <strong className="text-success">${Number(selectedProduct.precio).toLocaleString("es-CL")}</strong></span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 2. Título Principal (Campo Separado) */}
                  <div className="col-md-12">
                    <label className="form-label fw-bold">Título del Banner *</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Ej. BANNER TEST SUITE"
                      value={formData.titulo}
                      onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                      required
                    />
                  </div>

                  {/* 3. Subtítulo (Campo Separado) */}
                  <div className="col-md-12">
                    <label className="form-label fw-bold">Subtítulo Descriptivo</label>
                    <textarea
                      className="form-control"
                      rows="2"
                      placeholder="Ej. Subtitulo test suite o descripción comercial."
                      value={formData.subtitulo}
                      onChange={(e) => setFormData({ ...formData, subtitulo: e.target.value })}
                    />
                  </div>

                  {/* 4. Tag Superior */}
                  <div className="col-md-6">
                    <label className="form-label fw-bold d-flex justify-content-between align-items-center">
                      <span>Tag Superior (Color según banner)</span>
                      <small className="text-muted fw-normal">{formData.etiqueta_1?.length || 0}/255 car.</small>
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Ej. DESTACADO"
                      maxLength={255}
                      value={formData.etiqueta_1}
                      onChange={(e) => setFormData({ ...formData, etiqueta_1: e.target.value })}
                    />
                    <small className="text-muted">Insignia superior izquierda.</small>
                  </div>

                  {/* 5. Tag Rojo (ej. PROMOCIÓN / OFERTA) */}
                  <div className="col-md-6">
                    <label className="form-label fw-bold d-flex justify-content-between align-items-center">
                      <span className="text-danger">Tag Rojo</span>
                      <small className="text-muted fw-normal">{formData.etiqueta_roja?.length || 0}/50 car.</small>
                    </label>
                    <input
                      type="text"
                      className="form-control border-danger"
                      placeholder="Ej. PROMOCIÓN"
                      maxLength={50}
                      value={formData.etiqueta_roja}
                      onChange={(e) => setFormData({ ...formData, etiqueta_roja: e.target.value })}
                    />
                    <small className="text-muted">Insignia roja superior derecha de la tarjeta.</small>
                  </div>

                  {/* 6. Texto del Botón */}
                  <div className="col-md-6">
                    <label className="form-label fw-bold d-flex justify-content-between align-items-center">
                      <span>Texto del Botón</span>
                      <small className="text-muted fw-normal">{formData.texto_boton?.length || 0}/80 car.</small>
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Ej. Aprovechar Beneficio →"
                      maxLength={80}
                      value={formData.texto_boton}
                      onChange={(e) => setFormData({ ...formData, texto_boton: e.target.value })}
                    />
                    <small className="text-muted">El botón adopta automáticamente el tono del banner.</small>
                  </div>

                  {/* 7. Selector de Color del Banner con 6 Presets Temáticos */}
                  <div className="col-md-12">
                    <label className="form-label fw-bold d-flex align-items-center gap-1 mb-2">
                      <Palette size={16} className="text-primary" />
                      Color / Tema del Banner *
                    </label>
                    <div className="row g-2">
                      {BANNER_COLOR_PRESETS.map((preset) => {
                        const isSelected =
                          (formData.color_fondo || "").toLowerCase() ===
                          preset.value.toLowerCase();
                        return (
                          <div className="col-6 col-sm-4 col-md-2" key={preset.id}>
                            <button
                              type="button"
                              className={`btn w-100 p-2 text-start d-flex flex-column gap-1 position-relative ${
                                isSelected ? "border-primary shadow-sm" : "border"
                              }`}
                              style={{
                                background: `linear-gradient(135deg, ${preset.bgStart} 0%, ${preset.bgEnd} 100%)`,
                                borderRadius: "10px",
                                minHeight: "68px",
                                border: isSelected ? "2px solid #0d6efd" : "1px solid rgba(0,0,0,0.15)",
                                cursor: "pointer",
                              }}
                              onClick={() =>
                                setFormData({ ...formData, color_fondo: preset.value })
                              }
                            >
                              <div className="d-flex align-items-center justify-content-between w-100">
                                <span
                                  style={{
                                    fontSize: "0.72rem",
                                    fontWeight: 750,
                                    color: preset.tagColor,
                                    textTransform: "uppercase",
                                    letterSpacing: "0.02em",
                                  }}
                                >
                                  {preset.id}
                                </span>
                                {isSelected && (
                                  <span
                                    className="badge bg-primary rounded-circle p-1 d-flex align-items-center justify-content-center"
                                    style={{ width: "18px", height: "18px" }}
                                  >
                                    <CheckCircle2 size={12} className="text-white" />
                                  </span>
                                )}
                              </div>
                              <span
                                style={{
                                  fontSize: "0.76rem",
                                  fontWeight: 600,
                                  color: "#ffffff",
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                }}
                              >
                                {preset.name}
                              </span>
                              <div
                                style={{
                                  height: "4px",
                                  borderRadius: "2px",
                                  background: preset.btnBackground,
                                  width: "100%",
                                  marginTop: "auto",
                                }}
                              />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* 8. Posición / Orden */}
                  <div className="col-md-6">
                    <label className="form-label fw-bold d-flex justify-content-between align-items-center">
                      <span>Posición / Orden *</span>
                      <span className="badge bg-light text-dark border" style={{ fontSize: "0.74rem" }}>
                        Correlativo sugerido: #{nextCorrelative}
                      </span>
                    </label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      className={`form-control ${isCurrentOrderTaken ? "is-invalid border-warning" : ""}`}
                      value={formData.orden}
                      onChange={(e) => setFormData({ ...formData, orden: e.target.value })}
                      onBlur={handleOrderBlur}
                      required
                    />
                    {isCurrentOrderTaken ? (
                      <div
                        className="text-primary-emphasis bg-primary bg-opacity-10 p-2 rounded border border-primary-subtle mt-1"
                        style={{ fontSize: "0.8rem" }}
                      >
                        ℹ️ La posición <strong>#{formData.orden}</strong> está en uso por "{takenBanner?.titulo}". Al guardar se ajustará correlativamente sin problema.
                        <div className="mt-1">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary py-0 px-2"
                            style={{ fontSize: "0.75rem" }}
                            onClick={() => setFormData({ ...formData, orden: nextCorrelative })}
                          >
                            Usar libre correlativo #{nextCorrelative}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <small className="text-muted">Orden correlativo en el carrusel de inicio.</small>
                    )}
                  </div>
                </div>
              </div>

              <footer>
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary d-flex align-items-center gap-2"
                  disabled={saving}
                >
                  <Save size={18} />
                  {saving
                    ? "Guardando..."
                    : editingId
                    ? "Guardar cambios"
                    : "Crear banner"}
                </button>
              </footer>
            </form>
          </div>
        )}

      {/* MODAL CAMPAÑA DE PUBLICIDAD POR CORREO ELECTRÓNICO */}
      {isEmailModalOpen && selectedBannerForEmail && (() => {
        const emailTheme = getBannerTheme(selectedBannerForEmail.color_fondo || "#082620");
        const emailProduct = selectedBannerForEmail.producto;
        const emailProdImg = formatImageSrc(emailProduct?.imagen_url);

        const filteredClients = clientsList.filter((c) => {
          if (!clientSearch.trim()) return true;
          const term = clientSearch.toLowerCase();
          const nameMatch = (c.nombre || "").toLowerCase().includes(term);
          const rutMatch = (c.rut || "").toLowerCase().includes(term);
          const emailMatch = (c.correo || "").toLowerCase().includes(term);
          return nameMatch || rutMatch || emailMatch;
        });

        const isAll = targetMode === "all";
        const selectedCount = isAll ? clientsList.length : selectedClientIds.size;
        const allFilteredSelected =
          filteredClients.length > 0 &&
          filteredClients.every((c) => selectedClientIds.has(c.id));

        return (
          <div className="modal-backdrop-custom">
            <div className="category-modal email-campaign-modal">
              <header>
                <div>
                  <p className="eyebrow d-flex align-items-center gap-1">
                    <Mail size={14} /> CAMPAÑA PUBLICITARIA POR CORREO
                  </p>
                  <h2>Enviar Banner a Clientes</h2>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setIsEmailModalOpen(false)}
                  aria-label="Cerrar modal"
                  disabled={sendingEmail}
                >
                  <X size={19} />
                </button>
              </header>

              <div className="modal-body-custom">
                {/* 1. Selección de Destinatarios */}
                <div className="email-field-group">
                  <label className="d-flex align-items-center justify-content-between">
                    <span>
                      Destinatarios (Para):
                    </span>
                    <span className="text-muted" style={{ fontWeight: 500, fontSize: "0.78rem" }}>
                      {clientsList.length} clientes disponibles con correo
                    </span>
                  </label>

                  <div className="email-mode-selector">
                    <button
                      type="button"
                      className={`email-mode-btn ${targetMode === "all" ? "active" : ""}`}
                      onClick={() => setTargetMode("all")}
                    >
                      <Users size={16} />
                      Todos los clientes con correo ({clientsList.length})
                    </button>
                    <button
                      type="button"
                      className={`email-mode-btn ${targetMode === "individual" ? "active" : ""}`}
                      onClick={() => setTargetMode("individual")}
                    >
                      <CheckSquare size={16} />
                      Selección manual ({selectedClientIds.size})
                    </button>
                  </div>

                  {targetMode === "all" ? (
                    <div className="email-privacy-notice">
                      <ShieldCheck size={20} className="flex-shrink-0 text-success" />
                      <div>
                        <strong>Envío masivo con Copia Oculta (CCO / BCC):</strong>
                        <div style={{ marginTop: "2px" }}>
                          Se enviará a los <strong>{clientsList.length} clientes</strong> registrados con correo. Cada cliente recibirá un mensaje privado e independiente, protegiendo totalmente la identidad de los demás.
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="email-clients-picker">
                      <div className="email-clients-toolbar">
                        <div className="email-clients-search-box">
                          <Search size={15} className="email-clients-search-icon" />
                          <input
                            type="text"
                            className="form-control"
                            placeholder="Buscar cliente por nombre, razón social, RUT o correo..."
                            value={clientSearch}
                            onChange={(e) => setClientSearch(e.target.value)}
                          />
                        </div>

                        <div className="d-flex align-items-center gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-secondary py-1 px-2"
                            style={{ fontSize: "0.75rem" }}
                            onClick={() => {
                              if (allFilteredSelected) {
                                handleDeselectAllFiltered(filteredClients);
                              } else {
                                handleSelectAllFiltered(filteredClients);
                              }
                            }}
                          >
                            {allFilteredSelected ? (
                              <>
                                <Square size={13} />
                                Desmarcar ({filteredClients.length})
                              </>
                            ) : (
                              <>
                                <CheckSquare size={13} />
                                Seleccionar ({filteredClients.length})
                              </>
                            )}
                          </button>
                        </div>
                      </div>

                      {loadingClients ? (
                        <div className="text-center p-3 text-muted" style={{ fontSize: "0.82rem" }}>
                          Cargando lista de clientes...
                        </div>
                      ) : filteredClients.length === 0 ? (
                        <div className="text-center p-3 text-muted" style={{ fontSize: "0.82rem" }}>
                          No se encontraron clientes que coincidan con la búsqueda.
                        </div>
                      ) : (
                        <div className="email-clients-scroll">
                          {filteredClients.map((client) => {
                            const isSelected = selectedClientIds.has(client.id);
                            return (
                              <div
                                key={client.id}
                                className={`email-client-row ${isSelected ? "selected" : ""}`}
                                onClick={() => toggleClientSelection(client.id)}
                              >
                                <input
                                  type="checkbox"
                                  className="email-client-checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleClientSelection(client.id)}
                                  onClick={(e) => e.stopPropagation()}
                                />
                                <div className="email-client-info">
                                  <div className="email-client-name">
                                    {client.nombre || "Cliente sin nombre"}
                                  </div>
                                  <div className="email-client-meta">
                                    {client.rut && (
                                      <span className="email-client-badge-rut">RUT: {client.rut}</span>
                                    )}
                                    <span className="email-client-email-text">{client.correo}</span>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 2. Campo Asunto */}
                <div className="email-field-group">
                  <label htmlFor="email-subject-input">
                    Asunto del correo <span className="text-danger">*</span>
                  </label>
                  <input
                    id="email-subject-input"
                    type="text"
                    className="form-control"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    placeholder="Ej: Gran Oferta Mayorista: Bebidas y Abarrotes"
                    required
                  />
                </div>

                {/* 3. Mensaje adicional opcional */}
                <div className="email-field-group">
                  <label htmlFor="email-custom-message">
                    Mensaje adicional o saludo personalizado <span className="text-muted" style={{ fontWeight: 400 }}>(Opcional)</span>
                  </label>
                  <textarea
                    id="email-custom-message"
                    className="form-control"
                    rows={2}
                    value={emailCustomMessage}
                    onChange={(e) => setEmailCustomMessage(e.target.value)}
                    placeholder="Ej: Estimado socio comercial, te compartimos nuestra promoción semanal exclusiva para pedidos directos..."
                    style={{ minHeight: "65px", fontSize: "0.85rem" }}
                  />
                  <small className="text-muted">
                    Este texto aparecerá destacado al inicio del correo antes del banner publicitario.
                  </small>
                </div>

                {/* 4. Previsualización del Cuerpo del Correo */}
                <div className="email-field-group">
                  <label className="d-flex align-items-center justify-content-between">
                    <span>Previsualización del Correo (Cuerpo)</span>
                    <span className="badge bg-light text-secondary border">
                      Vista en bandeja de entrada
                    </span>
                  </label>

                  <div className="email-preview-card">
                    <div className="email-preview-frame">
                      {/* Cabecera institucional */}
                      <div className="email-preview-header">
                        <div className="email-preview-header-brand">
                          <img
                            src="https://pedidos.distribuidoratridente.cl/logo_tridente.png"
                            alt="Logo Tridente"
                            onError={(e) => { e.target.style.display = "none"; }}
                          />
                          <div>
                            <div className="email-preview-header-title">Distribuidora Tridente</div>
                            <div className="email-preview-header-subtitle">Catálogo & Promociones Exclusivas</div>
                          </div>
                        </div>
                        <span
                          style={{
                            background: "rgba(14, 165, 233, 0.2)",
                            color: "#38bdf8",
                            border: "1px solid rgba(56, 189, 248, 0.4)",
                            fontSize: "0.68rem",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "12px",
                            textTransform: "uppercase",
                          }}
                        >
                          Ir al Portal
                        </span>
                      </div>

                      {/* Cuerpo simulado */}
                      <div className="email-preview-body">
                        <div className="email-preview-greeting">
                          Hola [Nombre o Razón Social del Cliente],
                        </div>
                        <p className="email-preview-lead">
                          Te compartimos la siguiente novedad destacada y beneficio disponible en nuestro catálogo mayorista:
                        </p>

                        {emailCustomMessage.trim() && (
                          <div className="email-preview-custom-msg">
                            {emailCustomMessage.trim()}
                          </div>
                        )}

                        {/* Tarjeta del Banner Promocional idéntico al del flyer/correo */}
                        <div
                          className="email-preview-banner-box"
                          style={{
                            background: `linear-gradient(135deg, ${emailTheme.bgStart} 0%, ${emailTheme.bgEnd} 100%)`,
                            border: "1px solid rgba(255, 255, 255, 0.12)",
                          }}
                        >
                          <div className="d-flex align-items-center gap-2 mb-2">
                            {selectedBannerForEmail.etiqueta_1 && (
                              <span
                                style={{
                                  background: emailTheme.tagBg,
                                  color: emailTheme.tagColor,
                                  border: `1px solid ${emailTheme.tagBorder}`,
                                  borderRadius: "20px",
                                  fontSize: "0.65rem",
                                  fontWeight: 800,
                                  padding: "2px 8px",
                                  textTransform: "uppercase",
                                }}
                              >
                                {selectedBannerForEmail.etiqueta_1}
                              </span>
                            )}
                            <span
                              style={{
                                background: "#fee2e2",
                                color: "#dc2626",
                                border: "1px solid #fca5a5",
                                borderRadius: "20px",
                                fontSize: "0.65rem",
                                fontWeight: 800,
                                padding: "2px 8px",
                                textTransform: "uppercase",
                              }}
                            >
                              {selectedBannerForEmail.etiqueta_roja || "PROMOCIÓN"}
                            </span>
                          </div>

                          <div
                            style={{
                              fontSize: "1.1rem",
                              fontWeight: 800,
                              color: "#ffffff",
                              lineHeight: 1.25,
                              marginBottom: "4px",
                            }}
                          >
                            {selectedBannerForEmail.titulo}
                          </div>

                          {selectedBannerForEmail.subtitulo && (
                            <div
                              style={{
                                fontSize: "0.8rem",
                                color: emailTheme.subColor || "#cbd5e1",
                                lineHeight: 1.4,
                                marginBottom: "8px",
                              }}
                            >
                              {selectedBannerForEmail.subtitulo}
                            </div>
                          )}

                          {emailProduct && (
                            <div className="email-preview-product-card">
                              {emailProdImg && (
                                <img
                                  src={emailProdImg}
                                  alt={emailProduct.nombre}
                                  className="email-preview-product-img"
                                />
                              )}
                              <div>
                                <div
                                  style={{
                                    fontSize: "0.68rem",
                                    fontWeight: 700,
                                    color: "#93c5fd",
                                    textTransform: "uppercase",
                                  }}
                                >
                                  CÓDIGO: {emailProduct.codigo}
                                </div>
                                <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#ffffff" }}>
                                  {emailProduct.nombre}
                                </div>
                                <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#38bdf8" }}>
                                  Precio ref: ${Number(emailProduct.precio || 0).toLocaleString("es-CL")}
                                </div>
                              </div>
                            </div>
                          )}

                          <div style={{ marginTop: "14px" }}>
                            <span
                              style={{
                                display: "inline-block",
                                background: emailTheme.btnBackground,
                                color: "#ffffff",
                                fontSize: "0.78rem",
                                fontWeight: 800,
                                padding: "6px 14px",
                                borderRadius: "6px",
                              }}
                            >
                              {selectedBannerForEmail.texto_boton || "Aprovechar Beneficio →"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Pie del correo */}
                      <div className="email-preview-footer">
                        Distribuidora Tridente · Este correo fue enviado de manera individual a [correo del cliente] con copia oculta.
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <footer>
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setIsEmailModalOpen(false)}
                  disabled={sendingEmail}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn btn-primary d-flex align-items-center gap-2"
                  onClick={handleSendEmailCampaign}
                  disabled={sendingEmail || (!isAll && selectedClientIds.size === 0)}
                  style={{ background: "#0284c7", borderColor: "#0284c7" }}
                >
                  <Send size={16} />
                  {sendingEmail
                    ? "Enviando correos..."
                    : `Enviar Correos (${selectedCount} destinatarios)`}
                </button>
              </footer>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
