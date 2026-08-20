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
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import PromoBannerCarousel from "../../components/PromoBannerCarousel";
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
      return;
    }
    const isTaken = publicidades.some(
      (p) => p.id !== editingId && Number(p.orden) === entered
    );
    if (isTaken) {
      Swal.fire({
        icon: "warning",
        title: "Orden ya utilizado",
        html: `El número de orden <b>#${entered}</b> ya está ocupado por otro banner.<br/>No se pueden repetir órdenes entre banners.<br/>Se asignó automáticamente el siguiente correlativo libre <b>#${nextCorrelative}</b>.`,
        confirmButtonText: "Entendido",
        confirmButtonColor: "#0d6efd",
      });
      setFormData((prev) => ({ ...prev, orden: nextCorrelative }));
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

    const isOrderTaken = publicidades.some(
      (p) => p.id !== editingId && Number(p.orden) === finalOrder
    );

    if (isOrderTaken) {
      const nextSuggested = getNextCorrelativeOrder();
      Swal.fire({
        icon: "warning",
        title: "Orden ya utilizado",
        html: `El número de orden <b>#${finalOrder}</b> ya está ocupado por otro banner.<br/>No se pueden repetir números de orden.<br/>Se ha asignado automáticamente el correlativo <b>#${nextSuggested}</b>.`,
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#0d6efd",
      });
      setFormData((prev) => ({ ...prev, orden: nextSuggested }));
      return;
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
                        className="text-warning-emphasis bg-warning bg-opacity-10 p-2 rounded border border-warning mt-1"
                        style={{ fontSize: "0.8rem" }}
                      >
                        ⚠️ La posición <strong>#{formData.orden}</strong> ya está ocupada por "{takenBanner?.titulo}". No se permite repetir orden.
                        <div className="mt-1">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary py-0 px-2"
                            style={{ fontSize: "0.75rem" }}
                            onClick={() => setFormData({ ...formData, orden: nextCorrelative })}
                          >
                            Asignar correlativo #{nextCorrelative}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <small className="text-muted">Orden en el carrusel de inicio (debe ser único correlativo).</small>
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
    </div>
  );
}
