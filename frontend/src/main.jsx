import React, { Component, StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Boxes, CheckCircle2, ClipboardList, DollarSign, Eye, FileText, FolderTree, KeyRound, LayoutDashboard, LogOut, MapPin, Megaphone, Menu, Minus, Package, Pencil, Plus, RotateCcw, Save, Search, Settings, ShoppingBag, Trash2, Users, X } from "lucide-react";

import "bootstrap/dist/css/bootstrap.min.css";
import "./styles.css";
import Swal from "sweetalert2";
import { api, clearSessionStorage, getStoredSession, saveSessionStorage, setAdminToken, setCustomerToken } from "./services/api";
import SystemSettings from "./pages/admin/SystemSettings";
import NotificationLogs from "./pages/admin/NotificationLogs";
import SessionLogs from "./pages/admin/SessionLogs";
import PublicidadManager from "./pages/admin/PublicidadManager";
import PromoBannerCarousel from "./components/PromoBannerCarousel";
import { useSessionInactivity } from "./hooks/useSessionInactivity";


const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function productImageSource(imageBase64) {
  if (!imageBase64) return null;
  return imageBase64.startsWith("http") ? imageBase64 : `data:image/jpeg;base64,${imageBase64}`;
}

function BrandMark() {
  const [imageFailed, setImageFailed] = useState(false);

  return imageFailed ? (
    <span className="brand-mark brand-mark-fallback" aria-label="Distribuidora Tridente">DT</span>
  ) : (
    <span className="brand-mark"><img src="/logo_tridente.png" alt="Distribuidora Tridente" onError={() => setImageFailed(true)} /></span>
  );
}

function Access({ onCustomerLogin, onAdminLogin }) {
  const [customerAccess, setCustomerAccess] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (customerAccess) {
        const { data } = await api.post("/clientes/login", { correo: email, password });
        setCustomerToken(data.access_token);
        const profile = await api.get("/cliente/perfil");
        saveSessionStorage(data.access_token, "customer", profile.data);
        onCustomerLogin(profile.data);
      } else {
        const { data } = await api.post("/login", { correo: email, password });
        setAdminToken(data.access_token);
        saveSessionStorage(data.access_token, "admin");
        onAdminLogin();
      }
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="access-shell">
      <section className="access-brand">
        <div className="access-brand-content">
          <h1>Pedidos simples.<br />Despachos claros.</h1>
          <p>Haz tu pedido y revisa su estado desde un solo lugar.</p>
        </div>
        <div className="access-brand-footer">
          <small>
            Aplicación desarrollada por{" "}
            <a href="https://raevsi.cl/" target="_blank" rel="noopener noreferrer">
              <strong>RAEV Soluciones Informática SpA</strong>
            </a>{" "}
            | Roderick Espinoza
          </small>
        </div>
      </section>

      <div className="access-form-container">
        <form className="access-form" onSubmit={submit}>
          <div className="access-form-heading">
            <BrandMark />

            <p className="eyebrow">{customerAccess ? "PORTAL DE CLIENTES" : "ADMINISTRACIÓN"}</p>
            <h2>{customerAccess ? "Realiza tu pedido" : "Panel Administrativo"}</h2>
            <p className="access-subheading">
              {customerAccess
                ? "Ingresa con tu correo electrónico y contraseña."
                : "Ingresa con tus credenciales de administración."}
            </p>

            <div className="access-tabs" role="tablist" aria-label="Modo de acceso">
              <button
                type="button"
                role="tab"
                aria-selected={customerAccess}
                className={`access-tab ${customerAccess ? "active" : ""}`}
                onClick={() => { setCustomerAccess(true); setError(""); }}
              >
                <Users size={18} />
                <span>Acceso Cliente</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={!customerAccess}
                className={`access-tab ${!customerAccess ? "active" : ""}`}
                onClick={() => { setCustomerAccess(false); setError(""); }}
              >
                <Settings size={18} />
                <span>Administración</span>
              </button>
            </div>
          </div>

          <div className="access-fields">
            <label htmlFor="access-email" className="form-label">Correo electrónico</label>
            <input
              id="access-email"
              className="form-control"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Correo Electrónico"
              required
            />

            <label htmlFor="access-password" className="form-label mt-3">Contraseña</label>
            <input
              id="access-password"
              className="form-control"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <div className="access-error-slot">
            {error && <p className="text-danger m-0">{error}</p>}
          </div>

          <button className="btn btn-primary btn-lg w-100 mt-2" disabled={loading}>
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <footer className="access-mobile-footer">
          <small>
            Aplicación desarrollada por{" "}
            <a href="https://raevsi.cl/" target="_blank" rel="noopener noreferrer">
              <strong>RAEV Soluciones Informática SpA</strong>
            </a>{" "}
            | Roderick Espinoza
          </small>
        </footer>
      </div>
    </main>
  );
}

function AdminAccess({ onLogin, onCustomerAccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/login", { correo: email, password });
      setAdminToken(data.access_token);
      saveSessionStorage(data.access_token, "admin");
      onLogin();
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="access-shell">
      <section className="access-brand">
        <div className="access-brand-content">
          <h1>Pedidos simples.<br />Despachos claros.</h1>
          <p>Haz tu pedido y revisa su estado desde un solo lugar.</p>
        </div>
        <div className="access-brand-footer">
          <small>
            Aplicación desarrollada por{" "}
            <a href="https://raevsi.cl/" target="_blank" rel="noopener noreferrer">
              <strong>RAEV Soluciones Informática SpA</strong>
            </a>{" "}
            | Roderick Espinoza
          </small>
        </div>
      </section>

      <div className="access-form-container">
        <form className="access-form" onSubmit={submit}>
          <div className="access-form-heading">
            <BrandMark />

            <p className="eyebrow">ADMINISTRACIÓN</p>
            <h2>Panel Administrativo</h2>
            <p className="access-subheading">Ingresa con tus credenciales de administración.</p>

            <div className="access-tabs" role="tablist" aria-label="Modo de acceso">
              <button
                type="button"
                role="tab"
                aria-selected={false}
                className="access-tab"
                onClick={onCustomerAccess}
              >
                <Users size={18} />
                <span>Acceso Cliente</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={true}
                className="access-tab active"
              >
                <Settings size={18} />
                <span>Administración</span>
              </button>
            </div>
          </div>

          <div className="access-fields">
            <label htmlFor="admin-email" className="form-label">Correo electrónico</label>
            <input
              id="admin-email"
              className="form-control"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Correo Electrónico"
              required
            />

            <label htmlFor="admin-password" className="form-label mt-3">Contraseña</label>
            <input
              id="admin-password"
              className="form-control"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <div className="access-error-slot">
            {error && <p className="text-danger m-0">{error}</p>}
          </div>

          <button className="btn btn-primary btn-lg w-100 mt-2" disabled={loading}>
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <footer className="access-mobile-footer">
          <small>
            Aplicación desarrollada por{" "}
            <a href="https://raevsi.cl/" target="_blank" rel="noopener noreferrer">
              <strong>RAEV Soluciones Informática SpA</strong>
            </a>{" "}
            | Roderick Espinoza
          </small>
        </footer>
      </div>
    </main>
  );
}

function ProductManagerLegacy({ categories }) {
  const emptyProduct = { categoria_id: "", codigo: "", nombre: "", precio: "", cantidad: "0", imagen_url: "", activo: true, afecto: false, tiene_caja: false, cantidad_caja: "", precio_caja: "" };
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyProduct);
  const [editingProduct, setEditingProduct] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadProducts() {
    try {
      const { data } = await api.get("/admin/productos");
      setProducts(data);
    } catch {
      setError("No fue posible cargar los productos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadProducts(); }, []);

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function attachImage(event) {
    const [file] = event.target.files;
    if (!file) return;
    if (file.type !== "image/jpeg" || !/\.jpe?g$/i.test(file.name)) {
      setError("Adjunta solo una imagen JPG.");
      event.target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("La imagen JPG no puede superar 5 MB.");
      event.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setField("imagen_url", String(reader.result).split(",")[1]);
      setError("");
    };
    reader.readAsDataURL(file);
  }

  function openCreate() {
    setEditingProduct(null);
    setForm({ ...emptyProduct, categoria_id: categories.find((category) => category.activo)?.id ?? "" });
    setError("");
  }

  function openEdit(product) {
    setEditingProduct(product);
    setForm({ ...product, precio: String(product.precio), cantidad: String(product.cantidad), imagen_url: product.imagen_url ?? "", afecto: product.afecto ?? false, tiene_caja: product.tiene_caja ?? false, cantidad_caja: product.cantidad_caja != null ? String(product.cantidad_caja) : "", precio_caja: product.precio_caja != null ? String(product.precio_caja) : "" });
    setError("");
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (!form.categoria_id) {
      setError("Selecciona una categoría para el producto.");
      return;
    }
    if (form.tiene_caja && (!form.cantidad_caja || Number(form.cantidad_caja) <= 0)) {
      setError("Indica una cantidad válida de unidades por caja (mayor a 0).");
      return;
    }
    if (form.tiene_caja && form.precio_caja && Number(form.precio_caja) <= 0) {
      setError("Indica un precio por caja válido (mayor a 0).");
      return;
    }
    setSaving(true);
    const payload = { ...form, nombre: form.nombre.trim().toUpperCase(), precio: Number(form.precio), cantidad: Number(form.cantidad), imagen_url: form.imagen_url || null, afecto: Boolean(form.afecto), tiene_caja: Boolean(form.tiene_caja), cantidad_caja: form.tiene_caja && form.cantidad_caja ? Number(form.cantidad_caja) : null, precio_caja: form.tiene_caja && form.precio_caja ? Number(form.precio_caja) : null };
    try {
      if (editingProduct) {
        await api.put(`/productos/${editingProduct.id}`, payload);
        setNotice("Producto actualizado correctamente.");
      } else {
        await api.post("/productos", payload);
        setNotice("Producto agregado correctamente.");
      }
      setEditingProduct(null);
      setForm(emptyProduct);
      setError("");
      await loadProducts();
    } catch {
      setError("No fue posible guardar el producto. Revisa que el código no esté repetido.");
    } finally {
      setSaving(false);
    }
  }

  const categoryName = (id) => categories.find((category) => category.id === id)?.nombre ?? "Sin categoría";
  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Productos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de inventario</span><button className="btn btn-primary" onClick={openCreate}><Plus size={18} />Nuevo producto</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Controla tu Productos</h2><p>Gestiona precios, disponibilidad y stock para los pedidos de clientes.</p></div><div className="summary-metric"><span>{products.length}</span><small>Productos registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de productos</h2><p>Productos activos e inactivos del catálogo.</p></div><span className="panel-count">{products.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 mb-0 category-notice" role="alert"><CheckCircle2 size={18} /><span className="ms-2">{notice}</span><button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando productos...</p> : <div className="product-table mt-4"><div className="product-table-head"><span>Producto</span><span className="d-none d-md-block">Categoría</span><span>Precio</span><span>Stock</span><span>IVA</span><span>Estado</span><span>Acciones</span></div>{products.length ? products.map((product) => <div className="product-row" key={product.id}><div className="product-name"><span className="product-thumb">{product.imagen_url ? <img src={product.imagen_url} alt="" /> : <Package size={18} />}</span><div><strong>{product.nombre}</strong><small>{product.codigo}{product.tiene_caja && product.cantidad_caja ? ` · Caja x${product.cantidad_caja}` : ""}</small></div></div><span className="d-none d-md-block product-category">{categoryName(product.categoria_id)}</span><strong>{money.format(product.precio)}</strong><span>{product.cantidad}</span><span className={product.afecto ? "status-active" : "status-inactive"}>{product.afecto ? "Afecto" : "Exento"}</span><span className={product.activo ? "status-active" : "status-inactive"}>{product.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openEdit(product)} aria-label={`Editar ${product.nombre}`}><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay productos. Agrega el primero para comenzar.</p>}</div>}</section></div>{(editingProduct || form.categoria_id) && <div className="modal-backdrop-custom" role="presentation"><form className="category-modal product-modal" onSubmit={saveProduct} role="dialog" aria-modal="true" aria-labelledby="product-form-title"><header><div><p className="eyebrow">CATALOGO</p><h2 id="product-form-title">{editingProduct ? "Editar producto" : "Nuevo producto"}</h2></div><button type="button" className="icon-button" onClick={() => { setEditingProduct(null); setForm(emptyProduct); }} aria-label="Cerrar formulario"><X size={19} /></button></header><div className="modal-body-custom"><div className="product-form-grid"><div className="product-form-wide"><label htmlFor="product-category" className="form-label">Categoría</label><select id="product-category" className="form-select" value={form.categoria_id} onChange={(event) => setField("categoria_id", event.target.value)} required><option value="">Selecciona una categoría</option>{categories.filter((category) => category.activo || category.id === form.categoria_id).map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}</select></div><div><label htmlFor="product-code" className="form-label">Código</label><input id="product-code" className="form-control" value={form.codigo} onChange={(event) => setField("codigo", event.target.value)} maxLength="50" required /></div><div><label htmlFor="product-stock" className="form-label">Stock</label><input id="product-stock" className="form-control" type="number" min="0" value={form.cantidad} onChange={(event) => setField("cantidad", event.target.value)} required /></div><div className="product-form-wide"><label htmlFor="product-name" className="form-label">Nombre</label><input id="product-name" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value)} maxLength="180" required autoFocus /></div><div><label htmlFor="product-price" className="form-label">Precio base</label><input id="product-price" className="form-control" type="number" min="1" step="1" value={form.precio} onChange={(event) => setField("precio", event.target.value)} required /></div><div><label htmlFor="product-image" className="form-label">URL imagen</label><input id="product-image" className="form-control" type="url" placeholder="https://..." value={form.imagen_url} onChange={(event) => setField("imagen_url", event.target.value)} /></div></div><div className="status-toggle"><div><strong>¿Tiene caja?</strong><small>{form.tiene_caja ? "El producto se comercializa o empaqueta por caja." : "El producto se comercializa por unidad individual."}</small></div><label className="switch"><input type="checkbox" checked={form.tiene_caja} onChange={(event) => setField("tiene_caja", event.target.checked)} /><span /></label></div>{form.tiene_caja && <div className="product-form-grid mt-2"><div><label htmlFor="product-box-qty" className="form-label">Cantidad por caja (unidades)</label><input id="product-box-qty" className="form-control" type="number" min="1" placeholder="Ej: 12, 24, 50..." value={form.cantidad_caja} onChange={(event) => setField("cantidad_caja", event.target.value)} required={form.tiene_caja} /></div><div><label htmlFor="product-box-price" className="form-label">Precio por caja</label><input id="product-box-price" className="form-control" type="number" min="1" step="1" placeholder="Ej: 15000" value={form.precio_caja} onChange={(event) => setField("precio_caja", event.target.value)} /></div></div>}<div className="status-toggle"><div><strong>Producto disponible</strong><small>Los productos inactivos no aparecen a los clientes.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div><div className="status-toggle"><div><strong>{form.afecto ? "Producto Afecto a IVA" : "Producto Exento de IVA"}</strong><small>{form.afecto ? "Marcado como afecto a impuestos (afecto = true)." : "Marcado como exento de impuestos (afecto = false)."}</small></div><label className="switch"><input type="checkbox" checked={form.afecto} onChange={(event) => setField("afecto", event.target.checked)} /><span /></label></div></div><footer><button type="button" className="btn btn-light" onClick={() => { setEditingProduct(null); setForm(emptyProduct); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar producto</>}</button></footer></form></div>}</>;
}

function ProductManager({ categories }) {
  const blankProduct = { categoria_id: "", codigo: "", nombre: "", precio: "", cantidad: "0", imagen_url: "", activo: true, afecto: false, tiene_caja: false, cantidad_caja: "", precio_caja: "" };
  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [stockThreshold, setStockThreshold] = useState("");
  const [page, setPage] = useState(1);
  const [product, setProduct] = useState(null);
  const [form, setForm] = useState(blankProduct);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const imageSource = (value) => value ? `data:image/jpeg;base64,${value}` : null;
  const categoryName = (id) => categories.find((category) => category.id === id)?.nombre ?? "Sin categoría";

  async function loadProducts() {
    try {
      const { data } = await api.get("/admin/productos", { params: { category_id: selectedCategory || undefined, search: productSearch.trim() || undefined, stock_lt: stockThreshold === "" ? undefined : Number(stockThreshold), page, page_size: 10 } });
      setProducts(data.items);
      setTotalProducts(data.total);
    } catch {
      setError("No fue posible cargar los productos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(loadProducts, 200);
    return () => clearTimeout(timer);
  }, [selectedCategory, productSearch, stockThreshold, page]);

  const downloadFullCatalog = () => {
    Swal.fire({
      title: "Generando full catálogo...",
      html: '<div style="background:#e5e9f0;border-radius:999px;height:10px;overflow:hidden;margin-top:6px"><div id="catalog-progress-bar" style="background:#146cce;height:100%;width:0%;transition:width .15s"></div></div><p id="catalog-progress-text" style="margin:10px 0 0;font-weight:700;color:#146cce">0%</p>',
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      animation: false,
    });
    api
      .get("/admin/catalogo/pdf", {
        responseType: "blob",
        onDownloadProgress: (event) => {
          const percent = event.total ? Math.round((event.loaded / event.total) * 100) : 0;
          const bar = document.getElementById("catalog-progress-bar");
          const text = document.getElementById("catalog-progress-text");
          if (bar) bar.style.width = `${percent}%`;
          if (text) text.textContent = `${percent}%`;
        },
      })
      .then(({ data }) => {
        const objectUrl = URL.createObjectURL(data);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = `full-catalogo-tridente-${new Date().toISOString().slice(0, 10)}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
        Swal.close();
      })
      .catch(() => {
        Swal.fire({ icon: "error", title: "No fue posible generar el catálogo", text: "Intenta nuevamente en unos minutos." });
      });
  };

  useEffect(() => {
    const table = document.querySelector(".product-table");
    if (!table) return undefined;
    const filters = document.createElement("div");
    filters.className = "product-filters mt-4";
    const categorySelect = document.createElement("select");
    categorySelect.className = "form-select";
    categorySelect.setAttribute("aria-label", "Filtrar por categoría");
    categorySelect.append(new Option("Todas las categorías", ""));
    categories.forEach((category) => categorySelect.append(new Option(category.nombre, category.id)));
    const searchField = document.createElement("div");
    searchField.className = "product-search";
    const searchInput = document.createElement("input");
    searchInput.className = "form-control";
    searchInput.placeholder = "Buscar por nombre";
    searchInput.setAttribute("aria-label", "Buscar producto por nombre");
    searchField.append(searchInput);
    const stockField = document.createElement("div");
    stockField.className = "product-stock-filter";
    const stockLabel = document.createElement("label");
    stockLabel.htmlFor = "product-stock-threshold";
    stockLabel.textContent = "Stock <";
    const stockInput = document.createElement("input");
    stockInput.id = "product-stock-threshold";
    stockInput.className = "form-control";
    stockInput.type = "number";
    stockInput.placeholder = "Sin límite";
    stockInput.setAttribute("aria-label", "Filtrar productos con stock menor a");
    stockField.append(stockLabel, stockInput);
    const catalogBtn = document.createElement("button");
    catalogBtn.type = "button";
    catalogBtn.className = "btn btn-outline-primary btn-full-catalog";
    catalogBtn.setAttribute("aria-label", "Descargar Full Catálogo en PDF");
    catalogBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg><span>Full Catálogo</span>';
    catalogBtn.addEventListener("click", downloadFullCatalog);
    filters.append(categorySelect, searchField, stockField, catalogBtn);
    table.before(filters);
    function filterProducts() {
      setSelectedCategory(categorySelect.value);
      setProductSearch(searchInput.value);
      setStockThreshold(stockInput.value);
      setPage(1);
    }
    categorySelect.addEventListener("change", filterProducts);
    searchInput.addEventListener("input", filterProducts);
    stockInput.addEventListener("input", filterProducts);
    return () => {
      categorySelect.removeEventListener("change", filterProducts);
      searchInput.removeEventListener("input", filterProducts);
      stockInput.removeEventListener("input", filterProducts);
      catalogBtn.removeEventListener("click", downloadFullCatalog);
      filters.remove();
    };
  }, [categories, loading]);

  useEffect(() => {
    document.querySelectorAll(".product-table .product-row").forEach((row) => {
      row.children[3]?.classList.toggle("stock-critical", Number(row.children[3]?.textContent) <= 0);
    });
  }, [products]);

  useEffect(() => {
    const table = document.querySelector(".product-table");
    if (!table || totalProducts <= 10) return undefined;
    const totalPages = Math.ceil(totalProducts / 10);
    const pager = document.createElement("nav");
    pager.className = "product-pagination";
    pager.setAttribute("aria-label", "Paginación de productos");
    const summary = document.createElement("small");
    summary.textContent = `Página ${page} de ${totalPages} · ${totalProducts} productos`;
    const previous = document.createElement("button");
    previous.className = "btn btn-outline-primary btn-sm";
    previous.type = "button";
    previous.textContent = "Anterior";
    previous.disabled = page === 1;
    const next = document.createElement("button");
    next.className = "btn btn-primary btn-sm";
    next.type = "button";
    next.textContent = "Siguiente";
    next.disabled = page === totalPages;
    const goPrevious = () => setPage((current) => Math.max(1, current - 1));
    const goNext = () => setPage((current) => Math.min(totalPages, current + 1));
    previous.addEventListener("click", goPrevious);
    next.addEventListener("click", goNext);
    pager.append(summary, previous, next);
    table.after(pager);
    return () => {
      previous.removeEventListener("click", goPrevious);
      next.removeEventListener("click", goNext);
      pager.remove();
    };
  }, [page, totalProducts]);

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function openProduct(current = null) {
    setProduct(current);
    setForm(current ? { ...current, precio: String(current.precio), cantidad: String(current.cantidad), imagen_url: current.imagen_url ?? "", afecto: current.afecto ?? false, tiene_caja: current.tiene_caja ?? false, cantidad_caja: current.cantidad_caja != null ? String(current.cantidad_caja) : "", precio_caja: current.precio_caja != null ? String(current.precio_caja) : "" } : { ...blankProduct, categoria_id: categories.find((category) => category.activo)?.id ?? "" });
    setError("");
  }

  function attachImage(event) {
    const [file] = event.target.files;
    if (!file) return;
    if (file.type !== "image/jpeg" || !/\.jpe?g$/i.test(file.name)) {
      setError("Adjunta solo una imagen JPG.");
      event.target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("La imagen JPG no puede superar 5 MB.");
      event.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setField("imagen_url", String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (!form.categoria_id) {
      setError("Selecciona una categoría.");
      return;
    }
    if (form.tiene_caja && (!form.cantidad_caja || Number(form.cantidad_caja) <= 0)) {
      setError("Indica una cantidad válida de unidades por caja (mayor a 0).");
      return;
    }
    if (form.tiene_caja && form.precio_caja && Number(form.precio_caja) <= 0) {
      setError("Indica un precio por caja válido (mayor a 0).");
      return;
    }
    const payload = { ...form, nombre: form.nombre.trim().toUpperCase(), precio: Number(form.precio), cantidad: Number(form.cantidad), imagen_url: form.imagen_url || null, afecto: Boolean(form.afecto), tiene_caja: Boolean(form.tiene_caja), cantidad_caja: form.tiene_caja && form.cantidad_caja ? Number(form.cantidad_caja) : null, precio_caja: form.tiene_caja && form.precio_caja ? Number(form.precio_caja) : null };
    setSaving(true);
    try {
      if (product) {
        await api.put(`/productos/${product.id}`, payload);
        setNotice("Producto actualizado correctamente.");
      } else {
        await api.post("/productos", payload);
        setNotice("Producto agregado correctamente.");
      }
      setProduct(null);
      setForm(blankProduct);
      setError("");
      await loadProducts();
    } catch {
      setError("No fue posible guardar el producto. Revisa sus datos y el código.");
    } finally {
      setSaving(false);
    }
  }

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Productos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de Productos</span><button className="btn btn-primary" onClick={() => openProduct()}><Plus size={18} />Nuevo producto</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Controla tus Productos</h2><p>Gestiona precios, disponibilidad y stock para los pedidos de clientes.</p></div><div className="summary-metric"><span>{products.length}</span><small>Productos registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de productos</h2><p>Productos activos e inactivos del catálogo.</p></div><span className="panel-count">{products.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando productos...</p> : <div className="product-table mt-4"><div className="product-table-head"><span>Producto</span><span>Categoría</span><span>Precio</span><span>Stock</span><span>IVA</span><span>Estado</span><span>Acciones</span></div>{products.map((item) => <div className="product-row" key={item.id}>        <div className="product-name">
          <span className="product-thumb">
            {imageSource(item.imagen_url) ? <img src={imageSource(item.imagen_url)} alt="" /> : <Package size={18} />}
          </span>
          <div>
            <strong>{item.nombre}</strong>
            <small>
              {item.codigo}
              {item.tiene_caja && item.cantidad_caja ? ` · Caja x${item.cantidad_caja}${item.precio_caja ? ` (${money.format(item.precio_caja)})` : ""}` : ""}
            </small>
          </div>
        </div><span className="product-category">{categoryName(item.categoria_id)}</span><strong>{money.format(item.precio)}</strong><span>{item.cantidad}</span><span className={item.afecto ? "status-active" : "status-inactive"}>{item.afecto ? "Afecto" : "Exento"}</span><span className={item.activo ? "status-active" : "status-inactive"}>{item.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openProduct(item)} aria-label={`Editar ${item.nombre}`}><Pencil size={16} /></button></div>)}</div>}</section></div>{(product || form.categoria_id) && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveProduct}><header><div><p className="eyebrow">CATALOGO</p><h2>{product ? "Editar producto" : "Nuevo producto"}</h2></div><button type="button" className="icon-button" onClick={() => { setProduct(null); setForm(blankProduct); }}><X size={19} /></button></header><div className="modal-body-custom"><div className="product-form-grid"><div className="product-form-wide"><label className="form-label" htmlFor="product-category-base64">Categoría</label><select id="product-category-base64" className="form-select" value={form.categoria_id} onChange={(event) => setField("categoria_id", event.target.value)} required><option value="">Selecciona una categoría</option>{categories.filter((category) => category.activo || category.id === form.categoria_id).map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}</select></div><div><label className="form-label" htmlFor="product-code-base64">Código</label><input id="product-code-base64" className="form-control" value={form.codigo} onChange={(event) => setField("codigo", event.target.value)} required /></div><div><label className="form-label" htmlFor="product-stock-base64">Stock</label><input id="product-stock-base64" className="form-control" type="number" min="0" value={form.cantidad} onChange={(event) => setField("cantidad", event.target.value)} required /></div><div className="product-form-wide"><label className="form-label" htmlFor="product-name-base64">Nombre</label><input id="product-name-base64" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value.toUpperCase())} required /></div><div><label className="form-label" htmlFor="product-price-base64">Precio base</label><input id="product-price-base64" className="form-control" type="number" min="1" value={form.precio} onChange={(event) => setField("precio", event.target.value)} required /></div><div><label className="form-label" htmlFor="product-image-base64">Imagen JPG</label><input id="product-image-base64" className="form-control" type="file" accept=".jpg,.jpeg,image/jpeg" onChange={attachImage} /><small className="form-text">Solo JPG, máximo 5 MB. Se guarda en Base64.</small></div></div>{imageSource(form.imagen_url) && <div className="image-preview"><img src={imageSource(form.imagen_url)} alt="Vista previa" /><button className="btn btn-link btn-sm" type="button" onClick={() => setField("imagen_url", "")}>Quitar imagen</button></div>}<div className="status-toggle"><div><strong>¿Tiene caja?</strong><small>{form.tiene_caja ? "El producto se comercializa o empaqueta por caja." : "El producto se comercializa por unidad individual."}</small></div><label className="switch"><input type="checkbox" checked={form.tiene_caja} onChange={(event) => setField("tiene_caja", event.target.checked)} /><span /></label></div>{form.tiene_caja && <div className="product-form-grid mt-2"><div><label className="form-label" htmlFor="product-box-qty-base64">Cantidad por caja (unidades)</label><input id="product-box-qty-base64" className="form-control" type="number" min="1" placeholder="Ej: 12, 24, 50..." value={form.cantidad_caja} onChange={(event) => setField("cantidad_caja", event.target.value)} required={form.tiene_caja} /></div><div><label className="form-label" htmlFor="product-box-price-base64">Precio por caja</label><input id="product-box-price-base64" className="form-control" type="number" min="1" step="1" placeholder="Ej: 15000" value={form.precio_caja} onChange={(event) => setField("precio_caja", event.target.value)} /></div></div>}<div className="status-toggle"><div><strong>Producto disponible</strong><small>Los productos inactivos no aparecen a los clientes.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div><div className="status-toggle"><div><strong>{form.afecto ? "Producto Afecto a IVA" : "Producto Exento de IVA"}</strong><small>{form.afecto ? "Marcado como afecto a impuestos (afecto = true)." : "Marcado como exento de impuestos (afecto = false)."}</small></div><label className="switch"><input type="checkbox" checked={form.afecto} onChange={(event) => setField("afecto", event.target.checked)} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => { setProduct(null); setForm(blankProduct); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar producto</>}</button></footer></form></div>}</>;
}

function UserManager() {
  const blankUser = { nombre: "", correo: "", celular: "", recibe_pedido: false, password: "", rol_id: "", activo: true };
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [user, setUser] = useState(null);
  const [form, setForm] = useState(blankUser);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadUsers() {
    try {
      const [{ data: userData }, { data: roleData }] = await Promise.all([api.get("/usuarios"), api.get("/roles")]);
      setUsers(userData);
      setRoles(roleData);
    } catch {
      setError("No fue posible cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadUsers(); }, []);

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function openUser(current = null) {
    setUser(current);
    setForm(current ? { nombre: current.nombre, correo: current.correo, celular: current.celular ?? "", recibe_pedido: current.recibe_pedido ?? false, password: "", rol_id: current.rol_id, activo: current.activo } : { ...blankUser, rol_id: roles[0]?.id ?? "" });
    setError("");
  }

  async function saveUser(event) {
    event.preventDefault();
    if (!user && form.password.length < 8) {
      setError("La clave debe tener al menos 8 caracteres.");
      return;
    }
    setSaving(true);
    const payload = { ...form, nombre: form.nombre.trim(), correo: form.correo.trim(), celular: form.celular?.trim() || null, recibe_pedido: Boolean(form.recibe_pedido) };
    if (user && !payload.password) delete payload.password;
    try {
      if (user) {
        await api.put(`/usuarios/${user.id}`, payload);
        setNotice("Usuario actualizado correctamente.");
      } else {
        await api.post("/usuarios", payload);
        setNotice("Usuario agregado correctamente.");
      }
      setUser(null);
      setForm(blankUser);
      setError("");
      await loadUsers();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible guardar el usuario. Revisa el correo y los datos ingresados.");
    } finally {
      setSaving(false);
    }
  }

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CONFIGURACION</p><h1>Usuarios</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de usuarios</span><button className="btn btn-primary" onClick={() => openUser()}><Plus size={18} />Nuevo usuario</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">ACCESOS</p><h2>Administra tus usuarios</h2><p>Controla los accesos, roles y estado de cada cuenta.</p></div><div className="summary-metric"><span>{users.length}</span><small>Usuarios registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de usuarios</h2><p>Usuarios activos e inactivos de la plataforma.</p></div><span className="panel-count">{users.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando usuarios...</p> : <div className="user-table mt-4"><div className="user-table-head"><span>Usuario</span><span>Celular</span><span>Rol</span><span>Recibe pedidos</span><span>Estado</span><span>Acciones</span></div>{users.length ? users.map((item) => <div className="user-row" key={item.id}><div className="user-name"><span className="user-avatar">{item.nombre.slice(0, 2).toUpperCase()}</span><div><strong>{item.nombre}</strong><small>{item.correo}</small></div></div><span className="user-phone">{item.celular || "-"}</span><span className="user-role">{item.rol.nombre}</span><span className={item.recibe_pedido ? "status-active" : "status-inactive"}>{item.recibe_pedido ? "Sí" : "No"}</span><span className={item.activo ? "status-active" : "status-inactive"}>{item.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openUser(item)} aria-label={`Editar ${item.nombre}`}><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay usuarios registrados.</p>}</div>}</section></div>{(user || form.rol_id) && <div className="modal-backdrop-custom"><form className="category-modal" onSubmit={saveUser}><header><div><p className="eyebrow">CONFIGURACION</p><h2>{user ? "Editar usuario" : "Nuevo usuario"}</h2></div><button type="button" className="icon-button" onClick={() => { setUser(null); setForm(blankUser); }} aria-label="Cerrar formulario"><X size={19} /></button></header><div className="modal-body-custom"><label className="form-label" htmlFor="user-name">Nombre</label><input id="user-name" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value)} maxLength="150" required autoFocus /><label className="form-label mt-3" htmlFor="user-email">Correo</label><input id="user-email" className="form-control" type="email" value={form.correo} onChange={(event) => setField("correo", event.target.value)} required /><label className="form-label mt-3" htmlFor="user-phone">Celular</label><input id="user-phone" className="form-control" value={form.celular} onChange={(event) => setField("celular", event.target.value)} placeholder="+56 9 1234 5678" maxLength="30" /><label className="form-label mt-3" htmlFor="user-password">{user ? "Nueva clave" : "Clave"}</label><input id="user-password" className="form-control" type="password" value={form.password} onChange={(event) => setField("password", event.target.value)} minLength="8" required={!user} />{user && <small className="form-text">Déjala vacía para mantener la clave actual.</small>}<label className="form-label mt-3" htmlFor="user-role">Rol</label><select id="user-role" className="form-select" value={form.rol_id} onChange={(event) => setField("rol_id", event.target.value)} required><option value="">Selecciona un rol</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.nombre}</option>)}</select><div className="status-toggle"><div className="status-toggle-info"><strong>Usuario activo</strong><small>Los usuarios inactivos no pueden iniciar sesión.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div><div className="status-toggle"><div className="status-toggle-info"><strong>Recibe pedidos</strong><small>Recibe notificaciones por correo de nuevos pedidos.</small></div><label className="switch"><input type="checkbox" checked={form.recibe_pedido} onChange={(event) => setField("recibe_pedido", event.target.checked)} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => { setUser(null); setForm(blankUser); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar usuario</>}</button></footer></form></div>}</>;
}

function CustomerManagerLegacy() {
  const blankCustomer = { rut: "", nombre: "", celular: "", correo: "", porcentaje: "0", activo: true };
  const blankAddress = { direccion: "", comuna: "", principal: false, activo: true };
  const [customers, setCustomers] = useState([]);
  const [customer, setCustomer] = useState(null);
  const [customerFormOpen, setCustomerFormOpen] = useState(false);
  const [form, setForm] = useState(blankCustomer);
  const [addressForm, setAddressForm] = useState(blankAddress);
  const [addressCustomer, setAddressCustomer] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadCustomers() {
    try {
      const { data } = await api.get("/clientes");
      setCustomers(data);
    } catch {
      setError("No fue posible cargar los clientes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadCustomers(); }, []);

  useEffect(() => {
    if (!customerFormOpen) return undefined;
    const modal = document.querySelector(".category-modal");
    const submitButton = modal?.querySelector('button[type="submit"]');
    if (!modal || !submitButton || modal.querySelector("#customer-password")) return undefined;
    const label = document.createElement("label");
    label.className = "form-label mt-3";
    label.htmlFor = "customer-password";
    label.textContent = selectedCustomer ? "Nueva contraseña (opcional)" : "Contraseña";
    const input = document.createElement("input");
    input.id = "customer-password";
    input.className = "form-control";
    input.type = "password";
    input.minLength = 8;
    input.required = !selectedCustomer;
    input.autocomplete = "new-password";
    submitButton.before(label, input);
    return () => {
      label.remove();
      input.remove();
    };
  }, [customerFormOpen, selectedCustomer]);
  useEffect(() => {
    const table = document.querySelector(".customer-row")?.parentElement;
    function handleCustomerClick(event) {
      if (event.target.closest("button")) return;
      const row = event.target.closest(".customer-row");
      if (!row) return;
      const rowIndex = [...table.querySelectorAll(".customer-row")].indexOf(row);
      if (customers[rowIndex]) openAddresses(customers[rowIndex]);
    }
    table?.addEventListener("click", handleCustomerClick);
    return () => table?.removeEventListener("click", handleCustomerClick);
  }, [customers]);
  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  function openCustomer(current = null) {
    setCustomer(current);
    setCustomerFormOpen(true);
    setForm(current ? { rut: current.rut ?? "", nombre: current.nombre ?? "", celular: current.celular ?? "", correo: current.correo ?? "", porcentaje: String(current.porcentaje), activo: current.activo } : blankCustomer);
    setError("");
  }

  async function saveCustomer(event) {
    event.preventDefault();
    if (![form.rut, form.nombre, form.celular].some((value) => value.trim())) return setError("Indica al menos RUT, nombre o celular.");
    setSaving(true);
    const payload = { ...form, rut: form.rut.trim() || null, nombre: form.nombre.trim() || null, celular: form.celular.trim() || null, correo: form.correo.trim() || null, porcentaje: Number(form.porcentaje) };
    try {
      if (customer) { await api.put(`/clientes/${customer.id}`, payload); setNotice("Cliente actualizado correctamente."); } else { await api.post("/clientes", payload); setNotice("Cliente agregado correctamente."); }
      setCustomer(null); setCustomerFormOpen(false); setForm(blankCustomer); setError(""); await loadCustomers();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible guardar el cliente. Revisa que RUT y celular no estén repetidos.");
    } finally { setSaving(false); }
  }

  function openAddresses(current) { setAddressCustomer(current); setAddressForm(blankAddress); setError(""); }
  async function saveAddress(event) {
    event.preventDefault();
    if (!addressCustomer) return;
    setSaving(true);
    try {
      await api.post(`/clientes/${addressCustomer.id}/direcciones`, addressForm);
      setAddressForm(blankAddress); setNotice("Dirección agregada correctamente.");
      const { data } = await api.get("/clientes");
      setCustomers(data); setAddressCustomer(data.find((item) => item.id === addressCustomer.id) ?? null);
    } catch (requestError) { setError(requestError.response?.data?.detail ?? "No fue posible guardar la dirección."); } finally { setSaving(false); }
  }

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CONFIGURACION</p><h1>Clientes</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de clientes</span><button className="btn btn-primary" onClick={() => openCustomer()}><Plus size={18} />Nuevo cliente</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">CLIENTES</p><h2>Administra tus clientes</h2><p>Gestiona sus datos, descuento y direcciones de despacho.</p></div><div className="summary-metric"><span>{customers.length}</span><small>Clientes registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de clientes</h2><p>Clientes activos e inactivos registrados en la plataforma.</p></div><span className="panel-count">{customers.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando clientes...</p> : <div className="user-table mt-4"><div className="user-table-head customer-table-head"><span>RUT</span><span>Nombre</span><span>Celular</span><span className="customer-email">Correo</span><span>%</span><span>Activo</span><span>Acciones</span></div>{customers.length ? customers.map((item) => <div className="user-row customer-row" key={item.id}><span>{item.rut || "-"}</span><strong>{item.nombre || "-"}</strong><span>{item.celular || "-"}</span><span className="customer-email">{item.correo || "-"}</span><span>{Number(item.porcentaje)}%</span><span className={item.activo ? "status-active" : "status-inactive"}>{item.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openCustomer(item)} aria-label="Editar cliente"><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay clientes registrados.</p>}</div>}</section></div>{customerFormOpen && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveCustomer}><header><div><p className="eyebrow">CONFIGURACION</p><h2>{customer ? "Editar cliente" : "Nuevo cliente"}</h2></div><button type="button" className="icon-button" onClick={() => { setCustomer(null); setCustomerFormOpen(false); setForm(blankCustomer); }} aria-label="Cerrar formulario"><X size={19} /></button></header><div className="modal-body-custom"><p className="form-text mt-0">Completa al menos uno: RUT, nombre o celular.</p><div className="product-form-grid"><div><label className="form-label" htmlFor="customer-rut">RUT</label><input id="customer-rut" className="form-control" value={form.rut} onChange={(event) => setField("rut", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-name">Nombre</label><input id="customer-name" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value)} autoFocus /></div><div><label className="form-label" htmlFor="customer-phone">Celular</label><input id="customer-phone" className="form-control" value={form.celular} onChange={(event) => setField("celular", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-email">Correo</label><input id="customer-email" className="form-control" type="email" value={form.correo} onChange={(event) => setField("correo", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-percentage">Porcentaje</label><input id="customer-percentage" className="form-control" type="number" min="0" max="100" step="0.01" value={form.porcentaje} onChange={(event) => setField("porcentaje", event.target.value)} required /></div></div><div className="status-toggle"><div><strong>Cliente activo</strong><small>Los clientes inactivos no pueden acceder al portal.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => { setCustomer(null); setCustomerFormOpen(false); setForm(blankCustomer); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar cliente</>}</button></footer></form></div>}{addressCustomer && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveAddress}><header><div><p className="eyebrow">DIRECCIONES</p><h2>{addressCustomer.nombre || addressCustomer.rut || "Cliente"}</h2></div><button type="button" className="icon-button" onClick={() => setAddressCustomer(null)} aria-label="Cerrar direcciones"><X size={19} /></button></header><div className="modal-body-custom"><div className="address-list">{addressCustomer.direcciones?.length ? addressCustomer.direcciones.map((address) => <div className="address-item" key={address.id}><div><strong>{address.direccion}</strong><small>{address.comuna || "Sin comuna"}</small></div>{address.principal && <span className="status-active">Principal</span>}</div>) : <p className="text-secondary mb-3">Aún no hay direcciones. La primera se asignará como principal.</p>}</div><div className="product-form-grid"><div className="product-form-wide"><label className="form-label" htmlFor="address-value">Dirección</label><input id="address-value" className="form-control" value={addressForm.direccion} onChange={(event) => setAddressForm((current) => ({ ...current, direccion: event.target.value }))} required /></div><div><label className="form-label" htmlFor="address-district">Comuna</label><input id="address-district" className="form-control" value={addressForm.comuna} onChange={(event) => setAddressForm((current) => ({ ...current, comuna: event.target.value }))} /></div></div><div className="status-toggle"><div><strong>Dirección principal</strong><small>Se usará por defecto para los despachos.</small></div><label className="switch"><input type="checkbox" checked={addressForm.principal} onChange={(event) => setAddressForm((current) => ({ ...current, principal: event.target.checked }))} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => setAddressCustomer(null)}>Cerrar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Agregar dirección</>}</button></footer></form></div>}</>;
}

function CustomerManager() {
  const blankCustomer = { rut: "", nombre: "", celular: "", correo: "", password: "", porcentaje: "0", activo: true };
  const blankAddress = { direccion: "", comuna: "", principal: false, activo: true };
  const [customers, setCustomers] = useState([]);
  const [customerFormOpen, setCustomerFormOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [addressCustomer, setAddressCustomer] = useState(null);
  const [form, setForm] = useState(blankCustomer);
  const [addressForm, setAddressForm] = useState(blankAddress);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [addressNotice, setAddressNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadCustomers() {
    try {
      const { data } = await api.get("/clientes");
      setCustomers(data);
      return data;
    } catch {
      setError("No fue posible cargar los clientes.");
      return [];
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadCustomers(); }, []);

  useEffect(() => {
    if (!customerFormOpen) return undefined;
    const emailInput = document.getElementById("customer-email-new");
    const emailField = emailInput?.closest("div");
    if (!emailField || emailField.parentElement?.querySelector("#customer-password")) return undefined;
    const passwordField = document.createElement("div");
    const label = document.createElement("label");
    label.className = "form-label";
    label.htmlFor = "customer-password";
    label.textContent = selectedCustomer ? "Nueva contraseña (opcional)" : "Contraseña";
    const input = document.createElement("input");
    input.id = "customer-password";
    input.className = "form-control";
    input.type = "password";
    input.minLength = 8;
    input.required = !selectedCustomer;
    input.autocomplete = "new-password";
    const updatePassword = (event) => setField("password", event.target.value);
    input.addEventListener("input", updatePassword);
    passwordField.append(label, input);
    emailField.after(passwordField);
    return () => {
      input.removeEventListener("input", updatePassword);
      passwordField.remove();
    };
  }, [customerFormOpen, selectedCustomer]);

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function openCustomer(customer = null) {
    setSelectedCustomer(customer);
    setForm(customer ? { rut: customer.rut ?? "", nombre: customer.nombre ?? "", celular: customer.celular ?? "", correo: customer.correo ?? "", password: "", porcentaje: String(customer.porcentaje), activo: customer.activo } : blankCustomer);
    setError("");
    setCustomerFormOpen(true);
  }

  async function saveCustomer(event) {
    event.preventDefault();
    if (!form.correo.trim()) {
      setError("El correo electrónico es obligatorio.");
      return;
    }
    if (!selectedCustomer && form.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    setSaving(true);
    const payload = { ...form, rut: form.rut.trim() || null, nombre: form.nombre.trim() || null, celular: form.celular.trim() || null, correo: form.correo.trim(), porcentaje: Number(form.porcentaje) };
    if (selectedCustomer && !payload.password) delete payload.password;
    try {
      if (selectedCustomer) await api.put(`/clientes/${selectedCustomer.id}`, payload);
      else await api.post("/clientes", payload);
      setNotice(selectedCustomer ? "Cliente actualizado correctamente." : "Cliente agregado correctamente.");
      setCustomerFormOpen(false);
      setSelectedCustomer(null);
      setForm(blankCustomer);
      setError("");
      await loadCustomers();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible guardar el cliente.");
    } finally {
      setSaving(false);
    }
  }

  function openAddresses(customer) {
    setAddressCustomer(customer);
    setAddressForm(blankAddress);
    setAddressNotice("");
    setError("");
  }

  async function refreshAddressCustomer() {
    const data = await loadCustomers();
    setAddressCustomer(data.find((item) => item.id === addressCustomer.id) ?? null);
  }

  async function saveAddress(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post(`/clientes/${addressCustomer.id}/direcciones`, addressForm);
      setAddressForm(blankAddress);
      setAddressNotice("Dirección agregada correctamente.");
      setNotice("Dirección agregada correctamente.");
      setError("");
      await refreshAddressCustomer();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible agregar la dirección.");
    } finally {
      setSaving(false);
    }
  }

  async function updateAddress(address, updates) {
    setSaving(true);
    try {
      await api.put(`/clientes/${addressCustomer.id}/direcciones/${address.id}`, { ...address, ...updates });
      setError("");
      await refreshAddressCustomer();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar la dirección.");
    } finally {
      setSaving(false);
    }
  }

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CONFIGURACION</p><h1>Clientes</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de clientes</span><button className="btn btn-primary" onClick={() => openCustomer()}><Plus size={18} />Nuevo cliente</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">CLIENTES</p><h2>Administra tus clientes</h2><p>Gestiona sus datos, descuento y direcciones de despacho.</p></div><div className="summary-metric"><span>{customers.length}</span><small>Clientes registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de clientes</h2><p>Clientes activos e inactivos registrados en la plataforma.</p></div><span className="panel-count">{customers.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && !customerFormOpen && !addressCustomer && <div className="alert alert-danger mt-3">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando clientes...</p> : <div className="customer-table mt-4"><div className="customer-table-head"><span>RUT</span><span>Nombre</span><span>Celular</span><span className="customer-email">Correo</span><span>%</span><span>Activo</span><span>Acciones</span></div>{customers.length ? customers.map((customer) => <div className="customer-row" key={customer.id}><span>{customer.rut || "-"}</span><strong>{customer.nombre || "-"}</strong><span>{customer.celular || "-"}</span><span className="customer-email">{customer.correo || "-"}</span><span>{Number(customer.porcentaje)}%</span><span className={customer.activo ? "status-active" : "status-inactive"}>{customer.activo ? "Activo" : "Inactivo"}</span><div className="customer-actions"><button className="icon-button category-edit" type="button" onClick={() => openAddresses(customer)} aria-label="Gestionar direcciones"><MapPin size={16} /></button><button className="icon-button category-edit" type="button" onClick={() => openCustomer(customer)} aria-label="Editar cliente"><Pencil size={16} /></button></div></div>) : <p className="text-secondary p-4 mb-0">Aún no hay clientes registrados.</p>}</div>}</section></div>{customerFormOpen && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveCustomer}><header><div><p className="eyebrow">CONFIGURACION</p><h2>{selectedCustomer ? "Editar cliente" : "Nuevo cliente"}</h2></div><button type="button" className="icon-button" onClick={() => { setCustomerFormOpen(false); setSelectedCustomer(null); setForm(blankCustomer); }} aria-label="Cerrar formulario"><X size={19} /></button></header><div className="modal-body-custom">{error && <div className="alert alert-danger mb-3">{error}</div>}<p className="form-text mt-0">Completa al menos uno: RUT, nombre o celular.</p><div className="product-form-grid"><div><label className="form-label" htmlFor="customer-rut-new">RUT</label><input id="customer-rut-new" className="form-control" value={form.rut} onChange={(event) => setField("rut", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-name-new">Nombre</label><input id="customer-name-new" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-phone-new">Celular</label><input id="customer-phone-new" className="form-control" value={form.celular} onChange={(event) => setField("celular", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-email-new">Correo</label><input id="customer-email-new" className="form-control" type="email" value={form.correo} onChange={(event) => setField("correo", event.target.value)} /></div><div><label className="form-label" htmlFor="customer-percentage-new">Porcentaje</label><input id="customer-percentage-new" className="form-control" type="number" min="0" max="100" step="0.01" value={form.porcentaje} onChange={(event) => setField("porcentaje", event.target.value)} required /></div></div><div className="status-toggle"><div><strong>Cliente activo</strong><small>Los clientes inactivos no pueden acceder al portal.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => { setCustomerFormOpen(false); setSelectedCustomer(null); setForm(blankCustomer); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar cliente</>}</button></footer></form></div>}{addressCustomer && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveAddress}><header><div><p className="eyebrow">DIRECCIONES</p><h2>{addressCustomer.nombre || addressCustomer.rut || "Cliente"}</h2></div><button type="button" className="icon-button" onClick={() => setAddressCustomer(null)} aria-label="Cerrar direcciones"><X size={19} /></button></header><div className="modal-body-custom">{error && <div className="alert alert-danger mb-3">{error}</div>}<div className="address-table"><div className="address-table-head"><span>Dirección</span><span>Comuna</span><span>Principal</span><span>Activo</span></div>{addressCustomer.direcciones?.map((address) => <div className="address-row" key={address.id}><span>{address.direccion}</span><span>{address.comuna || "-"}</span><label className="switch"><input type="checkbox" checked={address.principal} disabled={saving} onChange={(event) => updateAddress(address, { principal: event.target.checked })} /><span /></label><label className="switch"><input type="checkbox" checked={address.activo} disabled={saving || address.principal} onChange={(event) => updateAddress(address, { activo: event.target.checked })} /><span /></label></div>)}{!addressCustomer.direcciones?.length && <p className="text-secondary py-3 mb-0">Aún no hay direcciones.</p>}</div><div className="address-form"><div><label className="form-label" htmlFor="new-address">Dirección</label><input id="new-address" className="form-control" value={addressForm.direccion} onChange={(event) => setAddressForm((current) => ({ ...current, direccion: event.target.value }))} required /></div><div><label className="form-label" htmlFor="new-district">Comuna</label><input id="new-district" className="form-control" value={addressForm.comuna} onChange={(event) => setAddressForm((current) => ({ ...current, comuna: event.target.value }))} /></div><label className="switch address-principal"><input type="checkbox" checked={addressForm.principal} onChange={(event) => setAddressForm((current) => ({ ...current, principal: event.target.checked }))} /><span /></label><label className="switch address-active"><input type="checkbox" checked={addressForm.activo} onChange={(event) => setAddressForm((current) => ({ ...current, activo: event.target.checked }))} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => setAddressCustomer(null)}>Cerrar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Plus size={17} />Agregar dirección</>}</button></footer></form></div>}</>;
}

function AdminOrderManager() {
  const [orders, setOrders] = useState([]);
  const [states, setStates] = useState([]);
  const [filters, setFilters] = useState({ estado: "Pedido", codigo: "", desde: "", hasta: "" });
  const [orderPage, setOrderPage] = useState(1);
  const pageSize = 10;
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderLogs, setOrderLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [retryingLogs, setRetryingLogs] = useState(false);
  const [confirmation, setConfirmation] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatingState, setUpdatingState] = useState(false);
  const [deliveryPayment, setDeliveryPayment] = useState(null);
  const [creditDays, setCreditDays] = useState("");

  async function loadOrders() {
    try {
      const [{ data: ordersData }, { data: statesData }] = await Promise.all([api.get("/pedidos"), api.get("/estados")]);
      setOrders(ordersData);
      setStates(statesData);
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible cargar los pedidos.");
    } finally {
      setLoading(false);
    }
  }

  async function loadOrderLogs(orderId) {
    if (!orderId) return;
    setLoadingLogs(true);
    try {
      const { data } = await api.get(`/admin/pedidos/${orderId}/logs`);
      setOrderLogs(data);
    } catch {
      setOrderLogs([]);
    } finally {
      setLoadingLogs(false);
    }
  }

  async function retryOrderNotifications(orderId) {
    if (!orderId || retryingLogs) return;

    const confirmResult = await Swal.fire({
      title: "¿Reenviar notificaciones?",
      text: "Se generará nuevamente el PDF y se reenviarán los avisos por WhatsApp y correo. Evita hacer reenvíos seguidos para prevenir que WhatsApp o el servidor de correos bloqueen los mensajes por spam.",
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#0f766e",
      cancelButtonColor: "#64748b",
      confirmButtonText: "Sí, reenviar ahora",
      cancelButtonText: "Cancelar",
    });

    if (!confirmResult.isConfirmed) return;

    setRetryingLogs(true);
    try {
      await api.post(`/admin/pedidos/${orderId}/reintentar-notificaciones`);
      Swal.fire({
        icon: "success",
        title: "Reintento solicitado",
        text: "Las notificaciones se están procesando en segundo plano.",
        timer: 2500,
        showConfirmButton: false,
      });
      setTimeout(() => {
        loadOrderLogs(orderId);
      }, 2000);
    } catch (err) {
      const isRateLimit = err.response?.status === 429;
      Swal.fire({
        icon: isRateLimit ? "warning" : "error",
        title: isRateLimit ? "Límite de reenvío" : "Error al reintentar",
        text: err.response?.data?.detail ?? "No fue posible reintentar las notificaciones.",
      });
    } finally {
      setTimeout(() => setRetryingLogs(false), 3000);
    }
  }

  useEffect(() => { loadOrders(); }, []);

  useEffect(() => {
    if (selectedOrder) {
      loadOrderLogs(selectedOrder.id);
    } else {
      setOrderLogs([]);
    }
  }, [selectedOrder]);

  function getOrderStateName(order) {
    if (!order) return "";
    if (typeof order.estado === "string") return order.estado;
    return order.estado?.nombre || "";
  }

  function availableTransitions(order) {
    if (!order) return [];
    const stateName = getOrderStateName(order)?.trim();
    const transitions = {
      Pedido: ["Despachado", "Cancelado"],
      Pendiente: ["Despachado", "Cancelado"],
      Nuevo: ["Despachado", "Cancelado"],
      Despachado: ["Entregado", "Cancelado"],
    };
    return transitions[stateName] ?? [];
  }

  async function changeOrderStatus() {
    if (!confirmation) return;
    const targetState = confirmation.nextState?.trim().toLowerCase();
    let nextState = states.find((state) => state.nombre?.trim().toLowerCase() === targetState);
    if (!nextState) {
      try {
        const { data: freshStates } = await api.get("/estados");
        setStates(freshStates);
        nextState = freshStates.find((state) => state.nombre?.trim().toLowerCase() === targetState);
      } catch {
        // ignore
      }
    }
    if (!nextState) {
      Swal.fire({
        icon: "error",
        title: "Estado no disponible",
        text: `No fue posible encontrar el estado "${confirmation.nextState}" en el sistema.`,
      });
      setConfirmation(null);
      return;
    }
    if (confirmation.nextState === "Entregado" && deliveryPayment === null) {
      Swal.fire({
        icon: "warning",
        title: "Pago requerido",
        text: "Indica si el cliente pagó el pedido.",
      });
      return;
    }
    if (confirmation.nextState === "Entregado" && !deliveryPayment && (!Number.isInteger(Number(creditDays)) || Number(creditDays) < 1)) {
      Swal.fire({
        icon: "warning",
        title: "Días de crédito requeridos",
        text: "Indica una cantidad válida de días de crédito (al menos 1 día).",
      });
      return;
    }
    setUpdatingState(true);
    try {
      const payload = { estado_id: nextState.id };
      if (confirmation.nextState === "Entregado") {
        payload.pagado = deliveryPayment;
        if (!deliveryPayment) payload.dias_credito = Number(creditDays);
      }
      const { data } = await api.patch(`/pedidos/${confirmation.order.id}/estado`, payload);
      setOrders((current) => current.map((order) => order.id === data.id ? data : order));
      setSelectedOrder(data);
      Swal.fire({
        icon: "success",
        title: "Estado actualizado",
        text: `Pedido ${data.id?.slice(0, 8).toUpperCase()} actualizado a ${getOrderStateName(data)}.`,
        timer: 2000,
        showConfirmButton: false,
      });
      setError("");
      setNotice("");
      setConfirmation(null);
      setDeliveryPayment(null);
      setCreditDays("");
    } catch (requestError) {
      Swal.fire({
        icon: "error",
        title: "Error al actualizar",
        text: requestError.response?.data?.detail ?? "No fue posible actualizar el estado del pedido.",
      });
      setConfirmation(null);
    } finally {
      setUpdatingState(false);
    }
  }

  async function exportOrderPdf(order) {
    if (!order) return;
    const code = order.id?.slice(0, 8).toUpperCase() || "ORDEN";
    try {
      const { data } = await api.get(`/pedidos/${order.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pedido-${code}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      Swal.fire({
        icon: "error",
        title: "Error al exportar PDF",
        text: "No fue posible descargar el comprobante en PDF.",
      });
    }
  }

  useEffect(() => {
    setOrderPage(1);
  }, [filters.estado, filters.codigo, filters.desde, filters.hasta]);

  const visibleOrders = orders.filter((order) => {
    const code = filters.codigo.trim().toUpperCase();
    const createdAt = order.created_at ? new Date(order.created_at) : null;
    const from = filters.desde ? new Date(`${filters.desde}T00:00:00`) : null;
    const to = filters.hasta ? new Date(`${filters.hasta}T23:59:59.999`) : null;
    const stateName = getOrderStateName(order);
    return stateName.toLowerCase() === filters.estado.toLowerCase()
      && (!code || order.id?.slice(0, 8).toUpperCase().includes(code))
      && (!from || (createdAt && createdAt >= from))
      && (!to || (createdAt && createdAt <= to));
  });

  const totalPages = Math.ceil(visibleOrders.length / pageSize) || 1;
  const paginatedOrders = visibleOrders.slice((orderPage - 1) * pageSize, orderPage * pageSize);

  const dateFormatter = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">OPERACION</p><h1>Pedidos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Seguimiento de pedidos</span></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">PEDIDOS</p><h2>Controla todos los pedidos</h2><p>Consulta solicitudes de todos tus clientes y revisa su detalle.</p></div><div className="summary-metric"><span>{visibleOrders.length}</span><small>Pedidos visibles</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de pedidos</h2><p>Filtra por estado, código de pedido o rango de fechas.</p></div><span className="panel-count">{visibleOrders.length} pedidos</span></div><div className="order-history-filters"><label>Estado<select className="form-select" value={filters.estado} onChange={(event) => setFilters((current) => ({ ...current, estado: event.target.value }))}><option>Pedido</option><option>Despachado</option><option>Entregado</option><option>Cancelado</option></select></label><label>Pedido<input className="form-control" type="search" placeholder="Ej. 4CB969B1" value={filters.codigo} onChange={(event) => setFilters((current) => ({ ...current, codigo: event.target.value }))} /></label><label>Desde<input className="form-control" type="date" value={filters.desde} onChange={(event) => setFilters((current) => ({ ...current, desde: event.target.value }))} /></label><label>Hasta<input className="form-control" type="date" value={filters.hasta} onChange={(event) => setFilters((current) => ({ ...current, hasta: event.target.value }))} /></label></div>{notice && <div className="alert alert-success mt-3 mb-0 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando pedidos...</p> : <><div className="admin-order-table mt-4"><div className="admin-order-head"><span>Pedido</span><span>Cliente</span><span>Fecha</span><span>Estado</span><span>Total</span><span>Acciones</span></div>{paginatedOrders.map((order) => {
    const stateName = getOrderStateName(order);
    const customerName = order.cliente?.nombre || order.cliente?.rut || order.cliente?.celular || "Cliente";
    const customerSub = order.cliente?.rut || order.cliente?.celular || "Sin identificador";
    return <article className="admin-order-row" key={order.id}><div><strong>Pedido {order.id?.slice(0, 8).toUpperCase()}</strong><small>{order.detalles?.length ?? 0} productos</small></div><div><strong>{customerName}</strong><small>{customerSub}</small></div><span>{order.created_at ? dateFormatter.format(new Date(order.created_at)) : "-"}</span><span className={`order-status order-${stateName.toLowerCase()}`}>{stateName || "-"}</span><strong>{money.format(order.total ?? 0)}</strong><button className="icon-button category-edit" type="button" onClick={() => setSelectedOrder(order)} aria-label={`Ver detalle del pedido ${order.id?.slice(0, 8).toUpperCase()}`}><Eye size={16} /></button></article>;
  })}{!visibleOrders.length && <p className="history-filter-empty">No hay pedidos que coincidan con los filtros.</p>}</div>{visibleOrders.length > pageSize && <nav className="product-pagination mt-4" aria-label="Paginación de pedidos"><small>Página {orderPage} de {totalPages} · {visibleOrders.length} pedidos</small><button className="btn btn-outline-primary btn-sm" type="button" disabled={orderPage === 1} onClick={() => setOrderPage((current) => Math.max(1, current - 1))}>Anterior</button><button className="btn btn-primary btn-sm" type="button" disabled={orderPage === totalPages} onClick={() => setOrderPage((current) => Math.min(totalPages, current + 1))}>Siguiente</button></nav>}</>}</section></div>{selectedOrder && <div className="modal-backdrop-custom"><section className="category-modal product-modal order-detail-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">PEDIDO</p><h2>Detalle del pedido</h2></div><button className="icon-button" type="button" onClick={() => setSelectedOrder(null)} aria-label="Cerrar detalle"><X size={19} /></button></header><div className="modal-body-custom"><div className="order-detail-meta"><span>Pedido {selectedOrder.id?.slice(0, 8).toUpperCase()}</span><span>{selectedOrder.cliente?.nombre || selectedOrder.cliente?.rut || selectedOrder.cliente?.celular || "Cliente"}</span><span>{selectedOrder.created_at ? dateFormatter.format(new Date(selectedOrder.created_at)) : ""}</span></div><div className="order-detail-lines"><div><span>Producto</span><span>Cantidad</span><span>IVA</span><span>Precio</span><span>Subtotal</span></div>{(selectedOrder.detalles || []).map((line) => <div key={line.producto_id || line.id || Math.random()}><span>{line.nombre_producto}{line.tipo_empaque === "caja" ? <span className="badge bg-secondary ms-1" style={{ fontSize: "0.75rem" }}>Caja{line.cantidad_caja ? ` x${line.cantidad_caja}` : ""}</span> : null}</span><span>{line.cantidad} {line.tipo_empaque === "caja" ? (line.cantidad === 1 ? "cj." : "cjs.") : "un."}</span><span className={line.afecto ? "status-active" : "status-inactive"}>{line.afecto ? "Afecto" : "Exento"}</span><span>{money.format(line.precio_unitario ?? 0)}</span><strong>{money.format(line.subtotal ?? 0)}</strong></div>)}</div><div className="order-detail-total"><strong>Total</strong><strong>{money.format(selectedOrder.total ?? 0)}</strong></div>

<div className="order-notifications-section mt-4 pt-3 border-top">
  <div className="d-flex justify-content-between align-items-center mb-2">
    <h6 className="mb-0 fw-bold d-flex align-items-center gap-2">
      <Activity size={16} className="text-primary" />
      Estado de Notificaciones
    </h6>
    <button
      className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
      type="button"
      disabled={retryingLogs}
      onClick={() => retryOrderNotifications(selectedOrder.id)}
    >
      <RotateCcw size={14} className={retryingLogs ? "animate-spin" : ""} />
      {retryingLogs ? "Reenviando..." : "Reenviar avisos"}
    </button>
  </div>
  {loadingLogs ? (
    <p className="small text-secondary mb-0">Cargando estado de envíos...</p>
  ) : orderLogs.length ? (
    <div className="order-logs-mini-list">
      {orderLogs.map((log) => (
        <div key={log.id} className="order-log-mini-item">
          <div className="d-flex align-items-center gap-2">
            <span className={`badge-channel badge-${log.canal.toLowerCase().replace('_', '-')}`}>
              {log.canal === "WHATSAPP" ? "WhatsApp" : log.canal === "EMAIL_ADMIN" ? "Correo Admin" : log.canal === "EMAIL_CLIENTE" ? "Correo Cliente" : "Sistema"}
            </span>
            <span className={`badge-status-pill status-${log.estado === "ENVIADO" ? "success" : log.estado === "FALLIDO" ? "failed" : "skipped"}`}>
              {log.estado}
            </span>
            <small className="text-muted text-truncate" style={{ maxWidth: "200px" }}>{log.destinatario}</small>
          </div>
          {log.error ? (
            <small className="text-danger fw-semibold d-block mt-1">{log.mensaje || log.error}</small>
          ) : (
            <small className="text-secondary d-block mt-1">{log.mensaje}</small>
          )}
        </div>
      ))}
    </div>
  ) : (
    <p className="small text-muted mb-0">Sin registros de notificación para este pedido.</p>
  )}
</div>

</div><footer><div className="order-state-actions"><button className="btn btn-outline-primary export-order-pdf" type="button" onClick={() => exportOrderPdf(selectedOrder)}>Exportar PDF</button>{availableTransitions(selectedOrder).map((nextState) => <button className={nextState === "Cancelado" ? "btn btn-outline-danger" : "btn btn-primary"} type="button" key={nextState} onClick={() => { setDeliveryPayment(null); setCreditDays(""); setConfirmation({ order: selectedOrder, nextState }); }}>{nextState === "Despachado" ? "Despachar" : nextState === "Entregado" ? "Entregar" : "Cancelar pedido"}</button>)}</div><button className="btn btn-light" type="button" onClick={() => setSelectedOrder(null)}>Cerrar</button></footer></section></div>}{confirmation && <div className="modal-backdrop-custom"><section className="category-modal confirmation-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">CONFIRMAR ACCION</p><h2>{confirmation.nextState === "Entregado" ? "¿Cliente pagó su pedido?" : "¿Cambiar estado del pedido?"}</h2></div><button className="icon-button" type="button" onClick={() => setConfirmation(null)} aria-label="Cerrar confirmación"><X size={19} /></button></header><div className="modal-body-custom"><p>El pedido <strong>{confirmation.order?.id?.slice(0, 8).toUpperCase()}</strong> cambiará de <strong>{getOrderStateName(confirmation.order)}</strong> a <strong>{confirmation.nextState}</strong>.</p>{confirmation.nextState === "Entregado" ? <><div className="payment-choice"><button type="button" className={deliveryPayment === true ? "btn btn-primary" : "btn btn-outline-primary"} onClick={() => { setDeliveryPayment(true); setCreditDays(""); }}>Sí, pagó</button><button type="button" className={deliveryPayment === false ? "btn btn-primary" : "btn btn-outline-primary"} onClick={() => setDeliveryPayment(false)}>No, queda a crédito</button></div>{deliveryPayment === false && <div className="mt-3"><label className="form-label" htmlFor="credit-days">Días de crédito</label><input id="credit-days" className="form-control" type="number" min="1" step="1" value={creditDays} onChange={(event) => setCreditDays(event.target.value)} required autoFocus /><small className="form-text">El vencimiento se calcula desde la fecha de entrega.</small></div>}</> : <p className="mb-0">Esta acción actualizará el estado visible para el cliente.</p>}</div><footer><button className="btn btn-light" type="button" disabled={updatingState} onClick={() => setConfirmation(null)}>Volver</button><button className={confirmation.nextState === "Cancelado" ? "btn btn-danger" : "btn btn-primary"} type="button" disabled={updatingState} onClick={changeOrderStatus}>{updatingState ? "Actualizando..." : confirmation.nextState === "Entregado" ? "Finalizar entrega" : "Confirmar cambio"}</button></footer></section></div>}</>;
}

function CreditManager() {
  const [credits, setCredits] = useState([]);
  const [paidFilter, setPaidFilter] = useState("pending");
  const [selectedCredit, setSelectedCredit] = useState(null);
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadCredits() {
    setLoading(true);
    try {
      const { data } = await api.get("/creditos", { params: { pagado: paidFilter === "paid" } });
      setCredits(data);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible cargar los créditos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadCredits(); }, [paidFilter]);

  async function confirmPayment() {
    if (!selectedCredit || !paymentDate) return;
    setSaving(true);
    try {
      await api.patch(`/creditos/${selectedCredit.id}/pago`, { fecha_pago: paymentDate });
      setNotice(`Crédito del pedido ${selectedCredit.pedido.id.slice(0, 8).toUpperCase()} marcado como pagado.`);
      setSelectedCredit(null);
      await loadCredits();
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible registrar el pago.");
      setSelectedCredit(null);
    } finally {
      setSaving(false);
    }
  }

  const dateFormatter = new Intl.DateTimeFormat("es-CL", { dateStyle: "short" });
  const customerName = (credit) => credit.cliente?.nombre || credit.cliente?.rut || credit.cliente?.celular || "Cliente";
  const dueDays = (credit) => Math.max(0, Math.ceil((new Date(credit.fecha_vencimiento) - new Date()) / 86_400_000));

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">COBRANZAS</p><h1>Créditos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Seguimiento de cuentas por cobrar</span></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">CRÉDITOS</p><h2>{paidFilter === "pending" ? "Créditos pendientes" : "Historial de créditos pagados"}</h2><p>Controla los plazos de pago registrados al entregar los pedidos.</p></div><div className="summary-metric"><span>{credits.length}</span><small>{paidFilter === "pending" ? "Pendientes de pago" : "Pagados"}</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de créditos</h2><p>Consulta vencimientos y registra pagos recibidos.</p></div><span className="panel-count">{credits.length} registros</span></div><div className="credit-filters"><label htmlFor="credit-status">Vista</label><select id="credit-status" className="form-select" value={paidFilter} onChange={(event) => setPaidFilter(event.target.value)}><option value="pending">Pendientes</option><option value="paid">Historial pagados</option></select></div>{notice && <div className="alert alert-success mt-3 mb-0 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando créditos...</p> : <div className="credit-table mt-4"><div className="credit-table-head"><span>Cliente</span><span>Pedido</span><span>Días crédito</span><span>Entrega</span><span>Días al vencimiento</span><span>Vencimiento</span><span>{paidFilter === "paid" ? "Fecha pago" : "Acciones"}</span></div>{credits.length ? credits.map((credit) => <article className="credit-row" key={credit.id}><div><strong>{customerName(credit)}</strong><small>{credit.cliente?.rut || credit.cliente?.celular || "Sin identificador"}</small></div><strong>#{credit.pedido?.id?.slice(0, 8).toUpperCase()}</strong><span>{credit.dias_credito}</span><span>{dateFormatter.format(new Date(credit.fecha_entrega))}</span><span>{paidFilter === "pending" ? dueDays(credit) : "-"}</span><span>{dateFormatter.format(new Date(credit.fecha_vencimiento))}</span>{paidFilter === "paid" ? <span>{credit.fecha_pago ? dateFormatter.format(new Date(credit.fecha_pago)) : "-"}</span> : <button className="btn btn-outline-primary btn-sm" type="button" onClick={() => { setPaymentDate(new Date().toISOString().slice(0, 10)); setSelectedCredit(credit); }}>Marcar pagado</button>}</article>) : <p className="history-filter-empty">No hay créditos {paidFilter === "pending" ? "pendientes" : "pagados"}.</p>}</div>}</section></div>{selectedCredit && <div className="modal-backdrop-custom"><section className="category-modal confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="credit-payment-title"><header><div><p className="eyebrow">REGISTRAR PAGO</p><h2 id="credit-payment-title">¿Confirmar pago del crédito?</h2></div><button className="icon-button" type="button" onClick={() => setSelectedCredit(null)} aria-label="Cerrar confirmación"><X size={19} /></button></header><div className="modal-body-custom"><p>El crédito del pedido <strong>#{selectedCredit.pedido?.id?.slice(0, 8).toUpperCase()}</strong> quedará marcado como pagado.</p><label className="form-label" htmlFor="credit-payment-date">Fecha de pago</label><input id="credit-payment-date" className="form-control" type="date" value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} required /></div><footer><button className="btn btn-light" type="button" disabled={saving} onClick={() => setSelectedCredit(null)}>No</button><button className="btn btn-primary" type="button" disabled={saving || !paymentDate} onClick={confirmPayment}>{saving ? "Guardando..." : "Sí, marcar pagado"}</button></footer></section></div>}</>;
}

function AdminSalesDashboard() {
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = `${today.slice(0, 7)}-01`;
  const [orders, setOrders] = useState([]);
  const [filters, setFilters] = useState({ desde: monthStart, hasta: today });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/pedidos").then(({ data }) => setOrders(data)).catch((requestError) => setError(requestError.response?.data?.detail ?? "No fue posible cargar los indicadores.")).finally(() => setLoading(false));
  }, []);

  const getOrderState = (order) => (typeof order.estado === "string" ? order.estado : order.estado?.nombre || "");

  const salesOrders = orders.filter((order) => {
    const createdAt = order.created_at ? new Date(order.created_at) : null;
    const from = filters.desde ? new Date(`${filters.desde}T00:00:00`) : null;
    const to = filters.hasta ? new Date(`${filters.hasta}T23:59:59.999`) : null;
    return getOrderState(order) !== "Cancelado" && (!from || (createdAt && createdAt >= from)) && (!to || (createdAt && createdAt <= to));
  });
  const totalSales = salesOrders.reduce((total, order) => total + Number(order.total || 0), 0);
  const totalUnits = salesOrders.reduce((total, order) => total + (order.detalles || []).reduce((sum, line) => sum + (line.cantidad || 0), 0), 0);
  const customerRanking = Object.values(salesOrders.reduce((ranking, order) => {
    const id = order.cliente?.id || order.cliente_id || "unknown";
    const name = order.cliente?.nombre || order.cliente?.rut || order.cliente?.celular || "Cliente";
    ranking[id] ??= { id, name, orders: 0, total: 0 };
    ranking[id].orders += 1;
    ranking[id].total += Number(order.total || 0);
    return ranking;
  }, {})).sort((first, second) => second.total - first.total).slice(0, 10);
  const productRanking = Object.values(salesOrders.reduce((ranking, order) => {
    (order.detalles || []).forEach((line) => {
      ranking[line.producto_id] ??= { id: line.producto_id, name: line.nombre_producto, units: 0, total: 0 };
      ranking[line.producto_id].units += (line.cantidad || 0);
      ranking[line.producto_id].total += Number(line.subtotal || 0);
    });
    return ranking;
  }, {})).sort((first, second) => second.units - first.units || second.total - first.total).slice(0, 10);
  const maxCustomerTotal = customerRanking[0]?.total ?? 1;
  const maxProductUnits = productRanking[0]?.units ?? 1;

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">ANALÍTICA</p><h1>Dashboard</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Resumen comercial</span></div></header><div className="admin-content dashboard-content"><section className="dashboard-hero"><div><p className="eyebrow">VENTAS</p><h2>Visión comercial</h2><p>Ventas y comportamiento de compra durante el periodo seleccionado.</p></div><div className="dashboard-date-filters"><label>Desde<input className="form-control" type="date" value={filters.desde} max={filters.hasta || undefined} onChange={(event) => setFilters((current) => ({ ...current, desde: event.target.value }))} /></label><label>Hasta<input className="form-control" type="date" value={filters.hasta} min={filters.desde || undefined} max={today} onChange={(event) => setFilters((current) => ({ ...current, hasta: event.target.value }))} /></label></div></section>{error && <div className="alert alert-danger">{error}</div>}{loading ? <p className="text-secondary">Cargando indicadores...</p> : <><section className="dashboard-metrics"><article><span>VENTAS TOTALES</span><strong>{money.format(totalSales)}</strong><small>{salesOrders.length} pedidos no cancelados</small></article><article><span>CLIENTE PRINCIPAL</span><strong>{customerRanking[0]?.name || "Sin compras"}</strong><small>{customerRanking[0] ? money.format(customerRanking[0].total) : "-"}</small></article><article><span>PRODUCTO LÍDER</span><strong>{productRanking[0]?.name || "Sin ventas"}</strong><small>{productRanking[0] ? `${productRanking[0].units} unidades vendidas` : "-"}</small></article><article><span>UNIDADES VENDIDAS</span><strong>{totalUnits}</strong><small>En el periodo seleccionado</small></article></section><section className="dashboard-grid"><section className="content-panel dashboard-ranking"><div className="panel-heading"><div><h2>Clientes con más compras</h2><p>Ordenados de mayor a menor monto comprado.</p></div><span className="panel-count">{customerRanking.length} clientes</span></div>{customerRanking.length ? <ol className="ranking-list">{customerRanking.map((customer, index) => <li key={customer.id}><span className="ranking-position">{index + 1}</span><div className="ranking-main"><strong>{customer.name}</strong><small>{customer.orders} pedido{customer.orders === 1 ? "" : "s"}</small><i><b style={{ width: `${(customer.total / maxCustomerTotal) * 100}%` }} /></i></div><strong className="ranking-value">{money.format(customer.total)}</strong></li>)}</ol> : <p className="history-filter-empty">No hay compras en el periodo seleccionado.</p>}</section><section className="content-panel dashboard-ranking"><div className="panel-heading"><div><h2>Productos más vendidos</h2><p>Ordenados por cantidad de unidades vendidas.</p></div><span className="panel-count">{productRanking.length} productos</span></div>{productRanking.length ? <ol className="ranking-list">{productRanking.map((product, index) => <li key={product.id}><span className="ranking-position">{index + 1}</span><div className="ranking-main"><strong>{product.name}</strong><small>{product.units} unidades · {money.format(product.total)}</small><i><b style={{ width: `${(product.units / maxProductUnits) * 100}%` }} /></i></div><strong className="ranking-value">{product.units}</strong></li>)}</ol> : <p className="history-filter-empty">No hay ventas de productos en el periodo seleccionado.</p>}</section></section></>}</div></>;
}

function AdminDashboard({ onLogout }) {
  const [categories, setCategories] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editName, setEditName] = useState("");
  const [editOrden, setEditOrden] = useState(0);
  const [editActive, setEditActive] = useState(true);
  const [editUsesCustomerPercentage, setEditUsesCustomerPercentage] = useState(true);
  const [editPercentage, setEditPercentage] = useState("0");
  const [editEnCatalogoPublico, setEditEnCatalogoPublico] = useState(true);
  const [saving, setSaving] = useState(false);
  const [section, setSection] = useState("summary");
  const [configurationOpen, setConfigurationOpen] = useState(false);

  async function loadCategories() {
    try {
      const { data } = await api.get("/categorias", { params: { active_only: false } });
      setCategories(data);
    } catch {
      setError("No fue posible cargar las categorías.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadCategories(); }, []);

  async function createCategory(event) {
    event.preventDefault();
    if (!name.trim()) return;
    try {
      await api.post("/categorias", {
        nombre: name.trim(),
        activo: true,
        en_catalogo_publico: true,
      });
      setName("");
      setError("");
      await loadCategories();
      setNotice("Categoría agregada correctamente.");
    } catch {
      setError("No fue posible crear la categoría. Revisa que el nombre no esté repetido.");
    }
  }

  function openEdit(category) {
    setEditingCategory(category);
    setEditName(category.nombre);
    setEditOrden(category.orden ?? 0);
    setEditActive(category.activo);
    setEditUsesCustomerPercentage(category.usa_porcentaje_cliente);
    setEditPercentage(String(category.porcentaje ?? 0));
    setEditEnCatalogoPublico(category.en_catalogo_publico ?? true);
    setError("");
  }

  async function updateCategory(event) {
    event.preventDefault();
    if (!editingCategory || !editName.trim()) return;
    setSaving(true);
    try {
      await api.put(`/categorias/${editingCategory.id}`, {
        nombre: editName.trim(),
        orden: Number(editOrden) || 0,
        usa_porcentaje_cliente: editUsesCustomerPercentage,
        porcentaje: editUsesCustomerPercentage ? 0 : Number(editPercentage),
        activo: editActive,
        en_catalogo_publico: editEnCatalogoPublico,
      });
      setEditingCategory(null);
      setError("");
      await loadCategories();
      setNotice("Categoría actualizada correctamente.");
    } catch {
      setError("No fue posible actualizar la categoría. Revisa que el nombre no esté repetido.");
    } finally {
      setSaving(false);
    }
  }

  function logout() {
    setAdminToken(null);
    onLogout();
  }

  const navigation = [
    [LayoutDashboard, "Dashboard", "summary", true],
    [FolderTree, "Categorías", "categories", true],
    [Package, "Productos", "products", true],
    [ClipboardList, "Pedidos", "orders", true],
    [DollarSign, "Créditos", "credits", true],
    [Megaphone, "Publicidad", "publicidad", true],
  ];

  return <main className="admin-app"><aside className={`admin-sidebar ${menuOpen ? "is-open" : ""}`}><div className="sidebar-brand"><BrandMark /><span>Distribuidora Tridente</span><button className="sidebar-close d-lg-none" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú"><X size={20} /></button></div><p className="sidebar-label">OPERACION</p><nav className="sidebar-nav">{navigation.map(([Icon, label, key, enabled]) => <button key={label} className={section === key ? "active" : ""} disabled={!enabled} onClick={() => { setSection(key); setConfigurationOpen(false); setMenuOpen(false); }}><Icon size={19} /><span>{label}</span>{!enabled && <small>Pronto</small>}</button>)}<div className="sidebar-configuration"><button className={configurationOpen || section === "users" || section === "customers" || section === "settings" || section === "notification_logs" || section === "session_logs" ? "active" : ""} onClick={() => setConfigurationOpen((current) => !current)}><Settings size={19} /><span>Configuración</span></button>{configurationOpen && <div className="sidebar-submenu"><button className={section === "users" ? "active" : ""} onClick={() => { setSection("users"); setMenuOpen(false); }}><Users size={17} /><span>Usuarios</span></button><button className={section === "customers" ? "active" : ""} onClick={() => { setSection("customers"); setMenuOpen(false); }}><Users size={17} /><span>Clientes</span></button><button className={section === "settings" ? "active" : ""} onClick={() => { setSection("settings"); setMenuOpen(false); }}><Settings size={17} /><span>Ajustes</span></button><button className={section === "notification_logs" ? "active" : ""} onClick={() => { setSection("notification_logs"); setMenuOpen(false); }}><Activity size={17} /><span>Logs Envíos</span></button><button className={section === "session_logs" ? "active" : ""} onClick={() => { setSection("session_logs"); setMenuOpen(false); }}><KeyRound size={17} /><span>Logs Sesiones</span></button></div>}</div></nav><div className="sidebar-bottom"><div className="sidebar-user"><span>RE</span><div><strong>Administrador</strong><small>Sesión activa</small></div></div><button className="logout-button" onClick={logout}><LogOut size={18} />Cerrar sesión</button></div></aside><div className="sidebar-backdrop d-lg-none" hidden={!menuOpen} onClick={() => setMenuOpen(false)} /><button className="icon-button admin-mobile-menu d-lg-none" type="button" onClick={() => setMenuOpen(true)} aria-label="Abrir menú"><Menu size={21} /></button>
    {section === "summary" ? <section className="admin-workspace"><AdminSalesDashboard /></section> : section === "products" ? <section className="admin-workspace"><ProductManager categories={categories} /></section> : section === "orders" ? <section className="admin-workspace"><AdminOrderManager /></section> : section === "credits" ? <section className="admin-workspace"><CreditManager /></section> : section === "publicidad" ? <section className="admin-workspace"><PublicidadManager /></section> : section === "notification_logs" ? <section className="admin-workspace"><NotificationLogs /></section> : section === "session_logs" ? <section className="admin-workspace"><SessionLogs /></section> : section === "users" ? <section className="admin-workspace"><UserManager /></section> : section === "customers" ? <section className="admin-workspace"><CustomerManager /></section> : section === "settings" ? <section className="admin-workspace"><SystemSettings /></section> : <>

    <section className="admin-workspace"><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Categorías</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de Categoría</span><button className="btn btn-primary" onClick={() => document.getElementById("category-name")?.focus()}><Plus size={18} />Nueva categoría</button></div></header>
      <div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Organiza tu Categoría</h2><p>Las categorías agrupan los productos visibles para tus clientes.</p></div><div className="summary-metric"><span>{categories.length}</span><small>Categorías registradas</small></div></section>
        <section className="content-panel"><div className="panel-heading"><div><h2>Listado de categorías</h2><p>Administra la clasificación de tu catálogo.</p></div><span className="panel-count">{categories.length} registros</span></div><form className="category-form" onSubmit={createCategory}><div><label htmlFor="category-name" className="visually-hidden">Nombre de categoría</label><input id="category-name" className="form-control" placeholder="Escribe una nueva categoría" value={name} onChange={(event) => setName(event.target.value)} maxLength="120" required /></div><button className="btn btn-primary"><Plus size={18} />Agregar</button></form>
          {notice && <div className="alert alert-success alert-dismissible fade show mt-3 mb-0 category-notice" role="alert"><CheckCircle2 size={18} />{notice}<button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} /></div>}
          {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}
          {loading ? <p className="mt-4 text-secondary">Cargando categorías...</p> : <div className="category-table mt-4"><div className="category-table-head"><span>Orden</span><span>Categoría</span><span>Porcentaje</span><span>Catálogo Público</span><span>Estado</span><span>Acciones</span></div>{categories.length ? categories.map((category) => <div className="category-row" key={category.id}><span className="category-order-badge">{category.orden ?? 0}</span><div className="category-name"><span className="category-icon"><Boxes size={18} /></span><strong>{category.nombre}</strong></div><span className="category-percentage">{category.usa_porcentaje_cliente ? "Cliente" : `${Number(category.porcentaje)}%`}</span><span className={category.en_catalogo_publico ? "status-active" : "status-inactive"}>{category.en_catalogo_publico ? "Sí" : "No"}</span><span className={category.activo ? "status-active" : "status-inactive"}>{category.activo ? "Activa" : "Inactiva"}</span><button className="icon-button category-edit" onClick={() => openEdit(category)} aria-label={`Editar ${category.nombre}`}><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay categorías. Agrega la primera para comenzar.</p>}</div>}
        </section></div></section>{editingCategory && <div className="modal-backdrop-custom" role="presentation"><form className="category-modal" onSubmit={updateCategory} role="dialog" aria-modal="true" aria-labelledby="edit-category-title"><header><div><p className="eyebrow">CATEGORIA</p><h2 id="edit-category-title">Editar categoría</h2></div><button type="button" className="icon-button" onClick={() => setEditingCategory(null)} aria-label="Cerrar edición"><X size={19} /></button></header><div className="modal-body-custom"><label htmlFor="edit-category-name" className="form-label">Nombre</label><input id="edit-category-name" className="form-control" value={editName} onChange={(event) => setEditName(event.target.value)} maxLength="120" required autoFocus /><div className="mt-3"><label htmlFor="edit-category-order" className="form-label">Orden</label><input id="edit-category-order" className="form-control" type="number" step="1" value={editOrden} onChange={(event) => setEditOrden(event.target.value)} required /><small className="form-text">Número para definir la posición de la categoría en los listados y catálogo.</small></div><div className="status-toggle"><div><strong>Usar porcentaje del cliente</strong><small>Aplica el porcentaje configurado para el cliente.</small></div><label className="switch"><input type="checkbox" checked={editUsesCustomerPercentage} onChange={(event) => setEditUsesCustomerPercentage(event.target.checked)} /><span /></label></div>{!editUsesCustomerPercentage && <div className="mt-3"><label htmlFor="edit-category-percentage" className="form-label">Porcentaje de la categoría</label><input id="edit-category-percentage" className="form-control" type="number" min="0" max="100" step="0.01" value={editPercentage} onChange={(event) => setEditPercentage(event.target.value)} required /><small className="form-text">Se suma al precio base de los productos de esta categoría.</small></div>}<div className="status-toggle"><div><strong>Mostrar en catálogo público</strong><small>Determina si la categoría es visible para los clientes.</small></div><label className="switch"><input type="checkbox" checked={editEnCatalogoPublico} onChange={(event) => setEditEnCatalogoPublico(event.target.checked)} /><span /></label></div><div className="status-toggle"><div><strong>Estado de la categoría</strong><small>Las categorías inactivas no aparecen al cliente.</small></div><label className="switch"><input type="checkbox" checked={editActive} onChange={(event) => setEditActive(event.target.checked)} /><span /></label></div></div><footer><button type="button" className="btn btn-light" onClick={() => setEditingCategory(null)}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar cambios</>}</button></footer></form></div>}</>}</main>;
}

function ShopLegacy({ customer }) {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [view, setView] = useState("shop");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const timer = setTimeout(async () => {
      const { data } = await api.get("/productos", { params: { search: query || undefined, customer_id: customer.id } });
      setProducts(data);
    }, 200);
    return () => clearTimeout(timer);
  }, [query, customer.id]);

  async function loadOrders() {
    const { data } = await api.get(`/clientes/${customer.id}/pedidos`);
    setOrders(data);
    setView("orders");
  }

  function add(product) {
    setCart((current) => {
      const previous = current.find((item) => item.id === product.id);
      return previous ? current.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item) : [...current, { ...product, quantity: 1 }];
    });
    setNotice("Producto agregado al carrito.");
  }

  const total = cart.reduce((sum, item) => sum + Number(item.precio_cliente ?? item.precio) * item.quantity, 0);
  return <main className="customer-app"><header className="customer-topbar"><div className="container d-flex align-items-center justify-content-between"><div className="customer-brand"><span className="brand-mark">DT</span><strong>Distribuidora Tridente</strong></div><button className="btn btn-light btn-sm" onClick={loadOrders}><ClipboardList size={17} />Mis pedidos</button></div></header><div className="container py-4 py-lg-5"><header className="customer-heading"><p className="eyebrow">PORTAL DE PEDIDOS</p><h1>Hola, {customer.nombre}</h1><p>Selecciona los productos que necesitas para tu próximo despacho.</p></header>
    {view === "orders" ? <section className="content-panel"><button className="btn btn-link px-0 mb-3" onClick={() => setView("shop")}>Volver al catálogo</button><h2>Pedidos pendientes</h2>{orders.length ? orders.map((order) => <article className="order-row" key={order.id}><strong>{order.estado}</strong><span>{money.format(order.total)}</span><span>{order.detalles.length} productos</span></article>) : <p className="text-secondary mb-0">No hay pedidos pendientes.</p>}</section> : <div className="row g-4"><section className="col-lg-8"><div className="search-field"><Search size={20} /><label htmlFor="search" className="visually-hidden">Buscar producto</label><input id="search" className="form-control form-control-lg" placeholder="Busca por nombre de producto" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      {notice && <div className="alert alert-success mt-3">{notice}</div>}<div className="product-grid mt-4">{products.map((product) => <article className="product" key={product.id}><div className="product-image">{product.imagen_url ? <img src={product.imagen_url} alt="" /> : <Package size={30} />}</div><small>{product.codigo}</small><h2>{product.nombre}</h2><strong>{money.format(product.precio_cliente ?? product.precio)}</strong><button className="btn btn-outline-primary mt-3" onClick={() => add(product)}><Plus size={17} />Agregar</button></article>)}</div></section>
      <aside className="col-lg-4">
        <div className="cart">
          <div className="cart-title">
            <ShoppingBag size={20} />
            <h2>Tu carrito</h2>
          </div>
          {cart.length === 0 ? (
            <p className="text-secondary mb-0">Aún no agregas productos.</p>
          ) : (
            <>
              <div className="cart-items">
                {cart.map((item) => {
                  const itemPrice = Number(item.precio_cliente ?? item.precio);
                  const itemSubtotal = itemPrice * item.quantity;
                  return (
                    <div className="cart-line" key={item.id}>
                      <div className="cart-item-info">
                        <span className="cart-item-name" title={item.nombre}>{item.nombre}</span>
                        <small className="cart-item-price">
                          {money.format(itemPrice)} c/u · <strong className="text-primary">{money.format(itemSubtotal)}</strong>
                        </small>
                      </div>
                      <div className="cart-stepper">
                        <button
                          type="button"
                          className={`cart-stepper-btn minus ${item.quantity === 1 ? "is-trash" : ""}`}
                          onClick={() =>
                            setCart((current) =>
                              current
                                .map((line) => (line.id === item.id ? { ...line, quantity: line.quantity - 1 } : line))
                                .filter((line) => line.quantity > 0)
                            )
                          }
                          title={item.quantity === 1 ? "Eliminar del pedido" : "Restar 1"}
                          aria-label="Restar unidad"
                        >
                          {item.quantity === 1 ? <Trash2 size={14} strokeWidth={2.2} /> : <Minus size={14} strokeWidth={2.5} />}
                        </button>
                        <span className="cart-stepper-val">{item.quantity}</span>
                        <button
                          type="button"
                          className="cart-stepper-btn plus"
                          onClick={() =>
                            setCart((current) =>
                              current.map((line) => (line.id === item.id ? { ...line, quantity: line.quantity + 1 } : line))
                            )
                          }
                          title="Sumar 1"
                          aria-label="Sumar unidad"
                        >
                          <Plus size={14} strokeWidth={2.5} />
                        </button>

                      </div>
                    </div>
                  );
                })}
              </div>
              <hr />
              <div className="d-flex justify-content-between">
                <strong>Total</strong>
                <strong>{money.format(total)}</strong>
              </div>
              <button className="btn btn-primary w-100 mt-3" disabled>
                Selecciona dirección para finalizar
              </button>
            </>
          )}
        </div>
      </aside>
    </div>
    }
  </div>
</main>;
}



function CustomerProfile({ customer, onProfileUpdated, onBack, onOrders, onLogout }) {
  const [profile, setProfile] = useState(customer);
  const [form, setForm] = useState({ nombre: customer.nombre ?? "", celular: customer.celular ?? "" });
  const [address, setAddress] = useState({ direccion: "", comuna: "", principal: false, activo: true });
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function refreshProfile() {
    const { data } = await api.get("/cliente/perfil");
    setProfile(data);
    onProfileUpdated(data);
  }

  async function saveProfile(event) {
    event.preventDefault();
    try {
      const { data } = await api.put("/cliente/perfil", form);
      setProfile(data);
      onProfileUpdated(data);
      setNotice("Tus datos fueron actualizados.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar tus datos.");
    }
  }

  async function saveAddress(event) {
    event.preventDefault();
    try {
      await api.post("/cliente/perfil/direcciones", address);
      await refreshProfile();
      setAddress({ direccion: "", comuna: "", principal: false, activo: true });
      setNotice("Dirección agregada correctamente.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible guardar la dirección.");
    }
  }

  async function updateAddress(item, updates) {
    try {
      await api.put(`/cliente/perfil/direcciones/${item.id}`, { ...item, ...updates });
      await refreshProfile();
      setNotice("Dirección actualizada correctamente.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar la dirección.");
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await api.put("/cliente/perfil/clave", password);
      setPassword({ current_password: "", new_password: "" });
      setNotice("Contraseña actualizada correctamente.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible cambiar la contraseña.");
    }
  }


  useEffect(() => {
    const portal = document.querySelector(".customer-portal");
    if (!portal || portal.querySelector("[data-customer-profile-nav]")) return undefined;
    const sidebar = document.createElement("aside");
    sidebar.className = "customer-sidebar";
    sidebar.dataset.customerProfileNav = "true";
    sidebar.innerHTML = '<div class="customer-brand"><strong>Distribuidora Tridente</strong></div><p class="sidebar-label">MENU PRINCIPAL</p><nav class="customer-nav"><button type="button" class="profile-nav-order"><svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>Realizar pedido</button><button type="button" class="profile-nav-history"><svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M8 12h8M8 16h8"/></svg>Pedidos</button><button type="button" class="active customer-account-button">Mis datos</button></nav><div class="customer-profile"><span></span><div><strong></strong><small>Sesión activa</small></div></div><button type="button" class="logout-button profile-nav-logout"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><path d="M21 19v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2"/></svg>Cerrar sesión</button>';
    sidebar.querySelector(".customer-profile > span").textContent = (customer.nombre || customer.rut || customer.celular || "CL").slice(0, 2).toUpperCase();
    sidebar.querySelector(".customer-profile strong").textContent = customer.nombre || "Cliente";
    sidebar.querySelector(".profile-nav-order")?.addEventListener("click", onBack);
    sidebar.querySelector(".profile-nav-history")?.addEventListener("click", onOrders);
    sidebar.querySelector(".profile-nav-logout")?.addEventListener("click", onLogout);
    portal.prepend(sidebar);
    return () => sidebar.remove();
  }, [customer, onBack, onOrders, onLogout]);
  return <main className="customer-portal"><section className="customer-workspace"><header className="customer-portal-header"><div><p className="eyebrow">CUENTA</p><h1>Mis datos</h1></div><button className="btn btn-light" type="button" onClick={onBack}>Volver a pedidos</button></header><div className="customer-content">{notice && <div className="alert alert-success">{notice}</div>}{error && <div className="alert alert-danger">{error}</div>}<div className="row g-4"><section className="col-xl-7"><form className="content-panel" onSubmit={saveProfile}><div className="panel-heading"><div><h2>Datos personales</h2><p>El RUT y correo no se pueden modificar.</p></div></div><div className="row g-3"><label className="col-md-6">RUT<input className="form-control" value={profile.rut ?? ""} disabled /></label><label className="col-md-6">Correo electrónico<input className="form-control" value={profile.correo ?? ""} disabled /></label><label className="col-md-6">Nombre<input className="form-control" value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} /></label><label className="col-md-6">Celular<input className="form-control" value={form.celular} onChange={(event) => setForm({ ...form, celular: event.target.value })} /></label></div><button className="btn btn-primary mt-4">Guardar datos</button></form><form className="content-panel mt-4" onSubmit={changePassword}><div className="panel-heading"><div><h2>Cambiar contraseña</h2><p>Usa al menos 8 caracteres.</p></div></div><label className="form-label">Contraseña actual</label><input className="form-control" type="password" value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} required /><label className="form-label mt-3">Nueva contraseña</label><input className="form-control" type="password" minLength="8" value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} required /><button className="btn btn-primary mt-4">Cambiar contraseña</button></form></section><section className="col-xl-5"><div className="content-panel"><div className="panel-heading"><div><h2>Direcciones</h2><p>Debe existir una dirección principal activa.</p></div></div>{profile.direcciones?.map((item) => <div className="border rounded p-3 mb-2" key={item.id}><strong>{item.direccion}</strong><small className="d-block text-secondary">{item.comuna || "Sin comuna"}</small><button className="btn btn-outline-primary btn-sm mt-2 me-2" type="button" disabled={item.principal} onClick={() => updateAddress(item, { principal: true })}>{item.principal ? "Principal" : "Marcar principal"}</button><button className="btn btn-outline-secondary btn-sm mt-2" type="button" disabled={item.principal && item.activo} onClick={() => updateAddress(item, { activo: !item.activo })}>{item.activo ? "Desactivar" : "Activar"}</button></div>)}<hr /><form onSubmit={saveAddress}><label className="form-label">Nueva dirección</label><input className="form-control" value={address.direccion} onChange={(event) => setAddress({ ...address, direccion: event.target.value })} required /><label className="form-label mt-3">Comuna</label><input className="form-control" value={address.comuna} onChange={(event) => setAddress({ ...address, comuna: event.target.value })} /><label className="form-check mt-3"><input className="form-check-input" type="checkbox" checked={address.principal} onChange={(event) => setAddress({ ...address, principal: event.target.checked })} /><span className="ms-2">Usar como principal</span></label><button className="btn btn-primary mt-3">Agregar dirección</button></form></div></section></div></div></section></main>;
}

function CustomerAccount({ customer, tab, onTabChange, onProfileUpdated, onLogout }) {
  const [profile, setProfile] = useState(customer);
  const [form, setForm] = useState({ nombre: customer.nombre ?? "", celular: customer.celular ?? "" });
  const [address, setAddress] = useState({ direccion: "", comuna: "", principal: false, activo: true });
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function refreshProfile() {
    const { data } = await api.get("/cliente/perfil");
    setProfile(data);
    setForm({ nombre: data.nombre ?? "", celular: data.celular ?? "" });
    onProfileUpdated(data);
  }

  async function savePersonal(event) {
    event.preventDefault();
    try {
      const { data } = await api.put("/cliente/perfil", form);
      setProfile(data);
      onProfileUpdated(data);
      setNotice("Tus datos personales fueron actualizados.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar tus datos.");
    }
  }

  async function saveAddress(event) {
    event.preventDefault();
    try {
      await api.post("/cliente/perfil/direcciones", address);
      await refreshProfile();
      setAddress({ direccion: "", comuna: "", principal: false, activo: true });
      setNotice("Dirección agregada correctamente.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible guardar la dirección.");
    }
  }

  async function updateAddress(item, updates) {
    try {
      await api.put(`/cliente/perfil/direcciones/${item.id}`, { ...item, ...updates });
      await refreshProfile();
      setNotice("Dirección actualizada correctamente.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar la dirección.");
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await api.put("/cliente/perfil/clave", password);
      setPassword({ current_password: "", new_password: "" });
      setNotice("Contraseña actualizada. Enviamos un acuse a tu correo electrónico.");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible cambiar la contraseña.");
    }
  }

  const content = tab === "personal" ? <form className="content-panel account-panel" onSubmit={savePersonal}><div className="panel-heading"><div><h2>Datos personales</h2><p>El RUT y correo electrónico son datos de acceso y no se pueden modificar.</p></div></div><div className="row g-3"><label className="col-md-6">RUT<input className="form-control" value={profile.rut ?? ""} disabled /></label><label className="col-md-6">Correo electrónico<input className="form-control" value={profile.correo ?? ""} disabled /></label><label className="col-md-6">Nombre<input className="form-control" value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} /></label><label className="col-md-6">Celular<input className="form-control" value={form.celular} onChange={(event) => setForm({ ...form, celular: event.target.value })} /></label></div><button className="btn btn-primary mt-4">Guardar datos</button></form> : tab === "addresses" ? <section className="content-panel account-panel"><div className="panel-heading"><div><h2>Direcciones</h2><p>Mantén una dirección principal activa para realizar pedidos.</p></div></div><div className="account-addresses">{profile.direcciones?.length ? profile.direcciones.map((item) => <article className="account-address" key={item.id}><div><strong>{item.direccion}</strong><small>{item.comuna || "Sin comuna"}</small></div><div className="account-address-actions"><button className="btn btn-outline-primary btn-sm" type="button" disabled={item.principal} onClick={() => updateAddress(item, { principal: true })}>{item.principal ? "Principal" : "Marcar principal"}</button><button className="btn btn-outline-secondary btn-sm" type="button" disabled={item.principal && item.activo} onClick={() => updateAddress(item, { activo: !item.activo })}>{item.activo ? "Desactivar" : "Activar"}</button></div></article>) : <p className="text-secondary mb-4">Aún no tienes direcciones registradas.</p>}</div><form className="account-address-form" onSubmit={saveAddress}><h3>Agregar dirección</h3><div className="row g-3"><label className="col-md-7">Dirección<input className="form-control" value={address.direccion} onChange={(event) => setAddress({ ...address, direccion: event.target.value })} required /></label><label className="col-md-5">Comuna<input className="form-control" value={address.comuna} onChange={(event) => setAddress({ ...address, comuna: event.target.value })} /></label></div><label className="form-check mt-3"><input className="form-check-input" type="checkbox" checked={address.principal} onChange={(event) => setAddress({ ...address, principal: event.target.checked })} /><span className="ms-2">Usar como dirección principal</span></label><button className="btn btn-primary mt-3">Agregar dirección</button></form></section> : <form className="content-panel account-panel account-password-panel" onSubmit={changePassword}><div className="panel-heading"><div><h2>Cambiar contraseña</h2><p>Al confirmar el cambio se enviará un acuse a {profile.correo}.</p></div></div><label className="form-label">Contraseña actual</label><input className="form-control" type="password" value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} required /><label className="form-label mt-3">Nueva contraseña</label><input className="form-control" type="password" minLength="8" value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} required /><button className="btn btn-primary mt-4">Cambiar contraseña</button></form>;

  return <main className="customer-portal"><aside className="customer-sidebar"><div className="customer-brand"><BrandMark /><strong>Distribuidora Tridente</strong></div><p className="sidebar-label">MENU PRINCIPAL</p><nav className="customer-nav"><span className="customer-nav-title"><ClipboardList size={19} />Pedidos</span><button type="button" onClick={() => onTabChange("orders")}><ShoppingBag size={17} />Volver a pedidos</button><span className="customer-nav-title account-nav-title"><Users size={19} />Mis datos</span><div className="customer-submenu"><button className={tab === "personal" ? "active" : ""} type="button" onClick={() => onTabChange("personal")}><Users size={16} />Personal</button><button className={tab === "addresses" ? "active" : ""} type="button" onClick={() => onTabChange("addresses")}><MapPin size={16} />Direcciones</button><button className={tab === "password" ? "active" : ""} type="button" onClick={() => onTabChange("password")}><Settings size={16} />Cambiar contraseña</button></div></nav><div className="customer-profile"><span>{(profile.nombre || profile.rut || "CL").slice(0, 2).toUpperCase()}</span><div><strong>{profile.nombre || "Cliente"}</strong><small>Sesión activa</small></div></div><button className="logout-button" onClick={onLogout}><LogOut size={18} />Cerrar sesión</button></aside><section className="customer-workspace"><header className="customer-portal-header"><div><p className="eyebrow">MIS DATOS</p><h1>{tab === "personal" ? "Personal" : tab === "addresses" ? "Direcciones" : "Cambiar contraseña"}</h1></div></header><div className="customer-content">{notice && <div className="alert alert-success">{notice}</div>}{error && <div className="alert alert-danger">{error}</div>}{content}</div></section></main>;
}

function Shop({ customer, onLogout, onProfileUpdated }) {
  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [publicidades, setPublicidades] = useState([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [cart, setCart] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState(() => customer.direcciones?.find((address) => address.principal && address.activo)?.id ?? customer.direcciones?.find((address) => address.activo)?.id ?? "");
  const [section, setSection] = useState("create");
  const [orders, setOrders] = useState([]);
  const [historyFilters, setHistoryFilters] = useState({ estado: "Pedido", codigo: "", desde: "", hasta: "" });
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadPublicidades() {
    try {
      const { data } = await api.get("/publicidades", { params: { customer_id: customer.id } });
      setPublicidades(data);
    } catch {
      // Ignorar si falla la publicidad
    }
  }

  const PAGE_SIZE = 15;

  async function loadProducts() {
    try {
      const { data } = await api.get("/productos", { params: { category_id: selectedCategory || undefined, search: query || undefined, customer_id: customer.id, page, page_size: PAGE_SIZE } });
      setProducts(data.items);
      setTotalProducts(data.total);
    } catch {
      setError("No fue posible cargar los productos.");
    }
  }

  useEffect(() => { setPage(1); }, [query, selectedCategory]);

  useEffect(() => {
    const timer = setTimeout(loadProducts, 200);
    return () => clearTimeout(timer);
  }, [query, selectedCategory, customer.id, page]);

  useEffect(() => {
    loadPublicidades();
  }, [customer.id]);

  useEffect(() => {
    api.get("/categorias").then(({ data }) => setCategories(data)).catch(() => setError("No fue posible cargar las categorías."));
  }, []);

  useEffect(() => {
    const activeAddressId = customer.direcciones?.find((address) => address.principal && address.activo)?.id ?? customer.direcciones?.find((address) => address.activo)?.id ?? "";
    setSelectedAddress((current) => (current && customer.direcciones?.some((address) => address.id === current && address.activo)) ? current : activeAddressId);
  }, [customer.direcciones]);



  async function loadHistory() {
    try {
      const { data } = await api.get(`/clientes/${customer.id}/pedidos/historicos`);
      setOrders(data.map((order) => ({ ...order, estado: order.estado.nombre })));
    } catch {
      setError("No fue posible cargar el historial de pedidos.");
    }
  }

  useEffect(() => {
    if (section !== "history" || !orders.length) return undefined;
    const history = document.querySelector(".customer-workspace .order-history");
    if (!history) return undefined;
    history.querySelector(".order-history-head")?.remove();
    history.querySelectorAll(".order-date, .order-history-action").forEach((element) => element.remove());
    const header = document.createElement("div");
    header.className = "order-history-head";
    header.innerHTML = "<span>Pedido</span><span>Fecha</span><span>Estado</span><span>Total</span><span>Acciones</span>";
    history.prepend(header);
    const formatter = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
    const cleanup = [];
    [...history.querySelectorAll(".order-history-row")].forEach((row, index) => {
      const order = orders[index];
      const date = document.createElement("span");
      date.className = "order-date";
      date.textContent = order.created_at ? formatter.format(new Date(order.created_at)) : "-";
      const action = document.createElement("button");
      action.className = "btn btn-outline-primary btn-sm order-history-action";
      action.type = "button";
      action.setAttribute("aria-label", "Ver detalle del pedido");
      action.textContent = "Ver";
      const showDetail = () => setSelectedOrder(order);
      action.addEventListener("click", showDetail);
      row.children[1]?.before(date);
      row.append(action);
      cleanup.push(() => action.removeEventListener("click", showDetail));
    });
    return () => {
      cleanup.forEach((dispose) => dispose());
      header.remove();
      history.querySelectorAll(".order-date, .order-history-action").forEach((element) => element.remove());
    };
  }, [section, orders]);

  useEffect(() => {
    if (section !== "history") return undefined;
    const history = document.querySelector(".customer-workspace .order-history");
    if (!history || history.querySelector(".order-history-filters")) return undefined;
    const filters = document.createElement("div");
    filters.className = "order-history-filters";
    filters.innerHTML = '<label>Estado<select class="form-select"><option value="Pedido">Pedido</option><option value="Despachado">Despachado</option><option value="Entregado">Entregado</option><option value="Cancelado">Cancelado</option></select></label><label>Pedido<input class="form-control" type="search" placeholder="Ej. 4CB969B1" /></label><label>Desde<input class="form-control" type="date" /></label><label>Hasta<input class="form-control" type="date" /></label>';
    const [stateSelect, orderInput, fromInput, toInput] = filters.querySelectorAll("select, input");
    stateSelect.value = historyFilters.estado;
    orderInput.value = historyFilters.codigo;
    fromInput.value = historyFilters.desde;
    toInput.value = historyFilters.hasta;
    const updateFilters = () => setHistoryFilters({ estado: stateSelect.value, codigo: orderInput.value, desde: fromInput.value, hasta: toInput.value });
    [stateSelect, orderInput, fromInput, toInput].forEach((input) => input.addEventListener("input", updateFilters));
    history.before(filters);
    return () => {
      [stateSelect, orderInput, fromInput, toInput].forEach((input) => input.removeEventListener("input", updateFilters));
      filters.remove();
    };
  }, [section]);

  useEffect(() => {
    if (section !== "history") return;
    const history = document.querySelector(".customer-workspace .order-history");
    if (!history) return;
    const code = historyFilters.codigo.trim().toUpperCase();
    const from = historyFilters.desde ? new Date(`${historyFilters.desde}T00:00:00`) : null;
    const to = historyFilters.hasta ? new Date(`${historyFilters.hasta}T23:59:59.999`) : null;
    const visible = orders.map((order) => {
      const createdAt = order.created_at ? new Date(order.created_at) : null;
      return (!historyFilters.estado || order.estado === historyFilters.estado)
        && (!code || order.id.slice(0, 8).toUpperCase().includes(code))
        && (!from || (createdAt && createdAt >= from))
        && (!to || (createdAt && createdAt <= to));
    });
    [...history.querySelectorAll(".order-history-row")].forEach((row, index) => { row.hidden = !visible[index]; });
    const count = document.querySelector(".customer-workspace .panel-count");
    if (count) count.textContent = `${visible.filter(Boolean).length} pedidos`;
    let empty = history.parentElement?.querySelector(".history-filter-empty");
    if (!visible.some(Boolean)) {
      if (!empty) {
        empty = document.createElement("p");
        empty.className = "history-filter-empty";
        history.after(empty);
      }
      empty.textContent = "No hay pedidos que coincidan con los filtros.";
    } else {
      empty?.remove();
    }
  }, [section, orders, historyFilters]);

  useEffect(() => {
    if (!selectedOrder) return undefined;
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    root.render(<div className="modal-backdrop-custom"><section className="category-modal product-modal order-detail-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">PEDIDO</p><h2>Detalle del pedido</h2></div><button className="icon-button" type="button" onClick={() => setSelectedOrder(null)} aria-label="Cerrar detalle"><X size={19} /></button></header><div className="modal-body-custom"><div className="order-detail-meta"><span>Pedido {selectedOrder.id.slice(0, 8).toUpperCase()}</span><span>{selectedOrder.created_at ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(selectedOrder.created_at)) : ""}</span></div><div className="order-detail-lines"><div><span>Producto</span><span>Cantidad</span><span>IVA</span><span>Precio</span><span>Subtotal</span></div>{(selectedOrder.detalles || []).map((line) => <div key={line.producto_id || line.id || Math.random()}><span>{line.nombre_producto}{line.tipo_empaque === "caja" ? <span className="badge bg-secondary ms-1" style={{ fontSize: "0.75rem" }}>Caja{line.cantidad_caja ? ` x${line.cantidad_caja}` : ""}</span> : null}</span><span>{line.cantidad} {line.tipo_empaque === "caja" ? (line.cantidad === 1 ? "cj." : "cjs.") : "un."}</span><span className={line.afecto ? "status-active" : "status-inactive"}>{line.afecto ? "Afecto" : "Exento"}</span><span>{money.format(line.precio_unitario)}</span><strong>{money.format(line.subtotal)}</strong></div>)}</div><div className="order-detail-total"><strong>Total</strong><strong>{money.format(selectedOrder.total)}</strong></div></div><footer><button className="btn btn-light" type="button" onClick={() => setSelectedOrder(null)}>Cerrar</button></footer></section></div>);
    return () => { root.unmount(); container.remove(); };
  }, [selectedOrder]);

  function openHistory() {
    setHistoryFilters({ estado: "Pedido", codigo: "", desde: "", hasta: "" });
    setSection("history");
    setError("");
    loadHistory();
  }

  async function promptProductPackaging(product) {
    const hasBox = Boolean(product.tiene_caja && Number(product.cantidad_caja) >= 1);
    const unitPrice = Number(product.precio_cliente ?? product.precio);
    const boxPrice = hasBox
      ? Number(product.precio_caja_cliente ?? product.precio_caja ?? (unitPrice * Number(product.cantidad_caja)))
      : null;

    let selectedType = "unidad";

    // Paso 1: Si tiene opción de caja, preguntar primero si desea Unidad o Caja
    if (hasBox) {
      let resolveChoice;
      const choicePromise = new Promise((resolve) => {
        resolveChoice = resolve;
      });

      const choiceModal = await Swal.fire({
        title: `<span style="font-size: 1.25rem;">Agregar al Pedido</span>`,
        html: `
          <div style="text-align: center; font-family: inherit;">
            <p style="margin-bottom: 16px; color: #475569; font-size: 1rem;">
              ¿Quieres agregar <strong>${product.nombre}</strong> por <strong>Caja</strong> o por <strong>Unidad</strong>?
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">
              <button type="button" id="btn-choose-unidad" style="border: 2px solid #0d6efd; background: #f0f7ff; border-radius: 10px; padding: 16px 8px; cursor: pointer; text-align: center; transition: all 0.2s;">
                <div style="font-weight: 700; color: #0d6efd; font-size: 1.05rem; margin-bottom: 4px;">Por Unidad</div>
                <div style="font-size: 1.2rem; color: #1e293b; font-weight: 700;">${money.format(unitPrice)}</div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">c/u individual</div>
              </button>

              <button type="button" id="btn-choose-caja" style="border: 2px solid #198754; background: #f0fdf4; border-radius: 10px; padding: 16px 8px; cursor: pointer; text-align: center; transition: all 0.2s;">
                <div style="font-weight: 700; color: #198754; font-size: 1.05rem; margin-bottom: 4px;">Por Caja</div>
                <div style="font-size: 1.2rem; color: #1e293b; font-weight: 700;">${money.format(boxPrice)}</div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">Caja x${product.cantidad_caja} un.</div>
              </button>
            </div>
          </div>
        `,
        showCancelButton: true,
        showConfirmButton: false,
        cancelButtonText: "Cancelar",
        cancelButtonColor: "#6c757d",
        didOpen: () => {
          document.getElementById("btn-choose-unidad")?.addEventListener("click", () => {
            resolveChoice("unidad");
            Swal.close();
          });
          document.getElementById("btn-choose-caja")?.addEventListener("click", () => {
            resolveChoice("caja");
            Swal.close();
          });
        },
      });

      const choice = await Promise.race([
        choicePromise,
        Promise.resolve(choiceModal.isDismissed ? null : null),
      ]);

      if (!choice) {
        return null;
      }
      selectedType = choice;
    }

    // Paso 2: Preguntar la cantidad según el tipo seleccionado (Unidad o Caja)
    const isCaja = selectedType === "caja";
    const appliedPrice = isCaja ? boxPrice : unitPrice;

    const htmlContent = isCaja
      ? `
        <div style="text-align: left; font-family: inherit;">
          <p style="margin-bottom: 12px; color: #475569; font-size: 0.95rem;">
            Ingresa la cantidad de <strong>cajas</strong> para <strong>${product.nombre}</strong>:
          </p>

          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span style="font-weight: 600; color: #166534; font-size: 0.9rem; display: block;">Precio por caja:</span>
              <span style="font-size: 0.75rem; color: #4ade80;">(Contiene ${product.cantidad_caja} un. c/u)</span>
            </div>
            <span style="font-size: 1.2rem; font-weight: 700; color: #15803d;">${money.format(boxPrice)}</span>
          </div>

          <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
            <label style="display: block; font-weight: 600; font-size: 0.85rem; color: #334155; margin-bottom: 6px; text-align: center;">
              Cantidad de cajas:
            </label>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
              <button type="button" id="swal-qty-minus" style="width: 38px; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; font-size: 1.2rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center;">-</button>
              <input id="swal-qty-input" type="number" min="1" max="999" value="1" style="width: 70px; height: 38px; text-align: center; font-size: 1.1rem; font-weight: bold; border: 1px solid #cbd5e1; border-radius: 6px;" />
              <button type="button" id="swal-qty-plus" style="width: 38px; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; font-size: 1.2rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center;">+</button>
            </div>
          </div>

          <div id="swal-subtotal-preview" style="text-align: right; font-weight: 700; color: #1e293b; font-size: 1.05rem; margin-top: 8px;">
            Subtotal: ${money.format(boxPrice)}
          </div>
        </div>
      `
      : `
        <div style="text-align: left; font-family: inherit;">
          <p style="margin-bottom: 12px; color: #475569; font-size: 0.95rem;">
            Ingresa la cantidad de <strong>unidades</strong> para <strong>${product.nombre}</strong>:
          </p>

          <div style="background: #f0f7ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; color: #0369a1; font-size: 0.9rem;">Precio por unidad:</span>
            <span style="font-size: 1.2rem; font-weight: 700; color: #0284c7;">${money.format(unitPrice)}</span>
          </div>

          <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
            <label style="display: block; font-weight: 600; font-size: 0.85rem; color: #334155; margin-bottom: 6px; text-align: center;">
              Cantidad de unidades:
            </label>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
              <button type="button" id="swal-qty-minus" style="width: 38px; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; font-size: 1.2rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center;">-</button>
              <input id="swal-qty-input" type="number" min="1" max="999" value="1" style="width: 70px; height: 38px; text-align: center; font-size: 1.1rem; font-weight: bold; border: 1px solid #cbd5e1; border-radius: 6px;" />
              <button type="button" id="swal-qty-plus" style="width: 38px; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; font-size: 1.2rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center;">+</button>
            </div>
          </div>

          <div id="swal-subtotal-preview" style="text-align: right; font-weight: 700; color: #1e293b; font-size: 1.05rem; margin-top: 8px;">
            Subtotal: ${money.format(unitPrice)}
          </div>
        </div>
      `;

    const qtyResult = await Swal.fire({
      title: `<span style="font-size: 1.2rem;">${isCaja ? "Agregar Cajas" : "Agregar Unidades"}</span>`,
      html: htmlContent,
      showCancelButton: true,
      confirmButtonText: "Agregar al pedido",
      cancelButtonText: "Cancelar",
      confirmButtonColor: isCaja ? "#198754" : "#0d6efd",
      cancelButtonColor: "#6c757d",
      focusConfirm: false,
      didOpen: () => {
        const qtyInput = document.getElementById("swal-qty-input");
        const minusBtn = document.getElementById("swal-qty-minus");
        const plusBtn = document.getElementById("swal-qty-plus");
        const preview = document.getElementById("swal-subtotal-preview");

        const updateUI = () => {
          const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);
          qtyInput.value = qty;
          const subtotal = appliedPrice * qty;
          preview.textContent = `Subtotal: ${money.format(subtotal)}`;
        };

        minusBtn?.addEventListener("click", () => {
          qtyInput.value = Math.max(1, (parseInt(qtyInput.value, 10) || 1) - 1);
          updateUI();
        });

        plusBtn?.addEventListener("click", () => {
          qtyInput.value = (parseInt(qtyInput.value, 10) || 1) + 1;
          updateUI();
        });

        qtyInput?.addEventListener("input", updateUI);
      },
      preConfirm: () => {
        const qty = Math.max(1, parseInt(document.getElementById("swal-qty-input")?.value, 10) || 1);
        return {
          tipo_empaque: selectedType,
          cantidad: qty,
          applied_price: appliedPrice,
        };
      },
    });

    if (!qtyResult.isConfirmed || !qtyResult.value) {
      return null;
    }

    return qtyResult.value;
  }

  async function add(product) {
    const selection = await promptProductPackaging(product);
    if (!selection) return;

    const { tipo_empaque, cantidad, applied_price } = selection;
    const isCaja = tipo_empaque === "caja";
    const cartKey = `${product.id}_${tipo_empaque}`;

    setCart((current) => {
      const line = current.find((item) => (item.cart_key || item.id) === cartKey);
      return line
        ? current.map((item) =>
            (item.cart_key || item.id) === cartKey ? { ...item, quantity: item.quantity + cantidad } : item
          )
        : [
            ...current,
            {
              ...product,
              cart_key: cartKey,
              tipo_empaque,
              cantidad_caja: isCaja ? product.cantidad_caja : null,
              unit_price: applied_price,
              quantity: cantidad,
            },
          ];
    });

    const msg = `${cantidad} ${isCaja ? (cantidad === 1 ? "caja" : "cajas") : (cantidad === 1 ? "unidad" : "unidades")} de ${product.nombre} agregada(s) al pedido.`;

    Swal.fire({
      icon: "success",
      title: "¡Agregado al pedido!",
      text: msg,
      timer: 1800,
      showConfirmButton: false,
      position: "center",
    });
  }

  async function handleAddFromBanner(product, qty = 1) {
    await add(product);
  }

  function updateQuantity(cartKey, quantity) {
    setCart((current) =>
      quantity < 1
        ? current.filter((item) => (item.cart_key || item.id) !== cartKey)
        : current.map((item) =>
            (item.cart_key || item.id) === cartKey ? { ...item, quantity } : item
          )
    );
  }

  async function createOrder() {
    if (!selectedAddress) {
      setError("Selecciona una dirección de despacho activa.");
      return;
    }
    if (!cart.length) return;

    const confirmation = await Swal.fire({
      title: "¿Estás seguro de enviar el pedido?",
      text: "Una vez enviado, se registrará y podrás verlo en tus pedidos.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, enviar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#0d6efd",
      cancelButtonColor: "#6c757d",
    });

    if (!confirmation.isConfirmed) {
      setSection("create");
      return;
    }

    setSubmitting(true);
    Swal.fire({
      title: "Estamos procesando su pedido",
      text: "Por favor espere un momento mientras lo registramos.",
      icon: "info",
      allowOutsideClick: false,
      showConfirmButton: false,
      didOpen: () => Swal.showLoading(),
    });
    try {
      const response = await api.post(`/clientes/${customer.id}/pedidos`, {
        direccion_id: selectedAddress,
        productos: cart.map((item) => ({
          producto_id: item.id,
          cantidad: item.quantity,
          tipo_empaque: item.tipo_empaque || "unidad",
          cantidad_caja: item.tipo_empaque === "caja" ? item.cantidad_caja : null,
        })),
      });
      const orderCode = response?.data?.id?.slice(0, 8).toUpperCase() ?? "N/D";
      setCart([]);
      setError("");
      setSection("history");
      await Promise.all([loadHistory(), loadProducts()]);
      Swal.close();
      Swal.fire({
        icon: "success",
        title: "Pedido enviado",
        text: `Tu pedido fue registrado correctamente. Código: ${orderCode}`,
        confirmButtonText: "Aceptar",
      });
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible enviar el pedido.");
      Swal.close();
      Swal.fire({
        icon: "error",
        title: "No se pudo enviar",
        text: requestError.response?.data?.detail ?? "No fue posible enviar el pedido.",
        confirmButtonText: "Aceptar",
      });
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    const navigation = document.querySelector(".customer-sidebar .customer-nav");
    if (!navigation || navigation.querySelector("[data-customer-account]")) return undefined;
    const ordersTitle = navigation.querySelector(".customer-nav-title");
    ordersTitle?.remove();
    const orderButtons = navigation.querySelectorAll(":scope > button");
    if (orderButtons[1]) orderButtons[1].lastChild.textContent = "Pedidos";
    const profileButton = document.createElement("button");
    profileButton.type = "button";
    profileButton.className = "customer-account-button";
    profileButton.dataset.customerAccount = "true";
    profileButton.textContent = "Mis datos";
    profileButton.addEventListener("click", () => setSection("profile"));
    navigation.append(profileButton);
    return () => {
      if (ordersTitle) navigation.prepend(ordersTitle);
      profileButton.remove();
    };
  }, [section]);

  if (section === "profile") {
    return <CustomerProfile customer={customer} onProfileUpdated={onProfileUpdated} onBack={() => setSection("create")} onOrders={() => setSection("history")} onLogout={onLogout} />;
  }

  const total = cart.reduce((sum, item) => sum + Number(item.unit_price ?? item.precio_cliente ?? item.precio) * item.quantity, 0);
  const activeAddresses = customer.direcciones?.filter((address) => address.activo) ?? [];
  return (
    <main className="customer-portal">
      <aside className="customer-sidebar">
        <div className="customer-brand">
          <span className="brand-mark">DT</span>
          <strong>Distribuidora Tridente</strong>
        </div>
        <p className="sidebar-label">MENU PRINCIPAL</p>
        <nav className="customer-nav">
          <span className="customer-nav-title">
            <ClipboardList size={19} />
            Pedidos
          </span>
          <button
            className={section === "create" ? "active" : ""}
            onClick={() => {
              setSection("create");
              setError("");
            }}
          >
            <ShoppingBag size={17} />
            Realizar pedido
          </button>
          <button className={section === "history" ? "active" : ""} onClick={openHistory}>
            <ClipboardList size={17} />
            Pedidos históricos
          </button>
        </nav>
        <div className="customer-profile">
          <span>{(customer.nombre || customer.rut || customer.celular || "CL").slice(0, 2).toUpperCase()}</span>
          <div>
            <strong>{customer.nombre || "Cliente"}</strong>
            <small>Sesión activa</small>
          </div>
        </div>
        <button className="logout-button" onClick={onLogout}>
          <LogOut size={18} />
          Cerrar sesión
        </button>
      </aside>
      <section className="customer-workspace">
        <header className="customer-portal-header">
          <div>
            <p className="eyebrow">PEDIDOS</p>
            <h1>{section === "create" ? "Realizar pedido" : "Pedidos históricos"}</h1>
          </div>
          <span className="customer-welcome">Hola, {customer.nombre || customer.rut || customer.celular}</span>
        </header>
        <div className="customer-content">
          {error && <div className="alert alert-danger">{error}</div>}
          {section === "create" ? (
            <>
              {publicidades.length > 0 && (
                <div className="mb-4">
                  <PromoBannerCarousel
                    banners={publicidades}
                    onAddToCart={handleAddFromBanner}
                  />
                </div>
              )}
              <div className="row g-4">
                <section className="col-xl-8">
                  <div className="row g-2 align-items-center mb-3">
                    <div className="col-12 col-md-5 col-lg-4">
                      <select
                        className="form-select"
                        aria-label="Filtrar productos por categoría"
                        value={selectedCategory}
                        onChange={(event) => {
                          setSelectedCategory(event.target.value);
                          setPage(1);
                        }}
                      >
                        <option value="">Todas las categorías</option>
                        {categories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.nombre}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-12 col-md-7 col-lg-8">
                      <div className="search-field">
                        <Search size={18} />
                        <input
                          className="form-control"
                          placeholder="Busca por nombre de producto..."
                          value={query}
                          onChange={(event) => setQuery(event.target.value)}
                        />
                        {query && (
                          <button
                            type="button"
                            className="btn btn-sm btn-link text-muted pe-2 py-0 border-0"
                            onClick={() => setQuery("")}
                            title="Limpiar búsqueda"
                          >
                            <X size={16} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="product-grid">
                    {products.map((product) => (
                      <article className="product" key={product.id}>
                        <div className="product-image">
                          {productImageSource(product.imagen_url) ? (
                            <img src={productImageSource(product.imagen_url)} alt={product.nombre} />
                          ) : (
                            <Package size={30} />
                          )}
                        </div>
                        <div className="product-meta">
                          {product.categoria?.nombre ? (
                            <span className="product-category-badge" title={product.categoria.nombre}>
                              {product.categoria.nombre}
                            </span>
                          ) : (
                            <span />
                          )}
                          <small className="product-code">
                            {product.codigo}
                            {product.tiene_caja && product.cantidad_caja ? ` · Caja x${product.cantidad_caja}` : ""}
                          </small>
                        </div>
                        <h2>{product.nombre}</h2>
                        <div className="mt-auto d-flex flex-column">
                          <strong>{money.format(product.precio_cliente ?? product.precio)} <span style={{ fontSize: "0.8rem", fontWeight: "normal", color: "#64748b" }}>/ un.</span></strong>
                          {product.tiene_caja && product.cantidad_caja ? (
                            <small style={{ color: "#0d6efd", fontWeight: 600, marginTop: "2px" }}>
                              Caja x{product.cantidad_caja}: {money.format(product.precio_caja_cliente ?? product.precio_caja ?? ((product.precio_cliente ?? product.precio) * product.cantidad_caja))}
                            </small>
                          ) : null}
                        </div>
                        <button className="btn btn-outline-primary mt-3" onClick={() => add(product)}>
                          <Plus size={17} />
                          Agregar
                        </button>
                      </article>
                    ))}
                  </div>

                  {totalProducts > PAGE_SIZE && (
                    <nav className="product-pagination customer-product-pagination mt-4" aria-label="Paginación del catálogo">
                      <small>
                        Página {page} de {Math.ceil(totalProducts / PAGE_SIZE)} · {totalProducts} productos
                      </small>
                      <button
                        className="btn btn-outline-primary btn-sm"
                        type="button"
                        disabled={page === 1}
                        onClick={() => setPage((current) => Math.max(1, current - 1))}
                      >
                        Anterior
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        disabled={page === Math.ceil(totalProducts / PAGE_SIZE)}
                        onClick={() => setPage((current) => Math.min(Math.ceil(totalProducts / PAGE_SIZE), current + 1))}
                      >
                        Siguiente
                      </button>
                    </nav>
                  )}

                  {!products.length && <p className="text-secondary mt-4">No se encontraron productos.</p>}
                </section>
              <aside className="col-xl-4">
                <div className="cart">
                  <div className="cart-title">
                    <ShoppingBag size={20} />
                    <h2>Tu pedido</h2>
                  </div>
                  <label className="form-label" htmlFor="delivery-address">
                    Dirección de despacho
                  </label>
                  <select
                    id="delivery-address"
                    className="form-select"
                    value={selectedAddress}
                    onChange={(event) => setSelectedAddress(event.target.value)}
                  >
                    <option value="">Selecciona una dirección</option>
                    {activeAddresses.map((address) => (
                      <option value={address.id} key={address.id}>
                        {address.direccion}
                        {address.comuna ? `, ${address.comuna}` : ""}
                        {address.principal ? " (Principal)" : ""}
                      </option>
                    ))}
                  </select>
                  {!activeAddresses.length && (
                    <small className="form-text">No tienes direcciones activas registradas.</small>
                  )}
                  {cart.length ? (
                    <>
                      <div className="cart-items">
                        {cart.map((item) => {
                          const itemPrice = Number(item.unit_price ?? item.precio_cliente ?? item.precio);
                          const itemSubtotal = itemPrice * item.quantity;
                          const key = item.cart_key || item.id;
                          const isCaja = item.tipo_empaque === "caja";
                          return (
                            <div className="cart-line" key={key}>
                              <div className="cart-item-info">
                                <span className="cart-item-name" title={item.nombre}>
                                  {item.nombre}
                                  {isCaja ? (
                                    <span className="badge bg-secondary ms-1" style={{ fontSize: "0.75rem" }}>
                                      Caja{item.cantidad_caja ? ` x${item.cantidad_caja}` : ""}
                                    </span>
                                  ) : null}
                                </span>
                                <small className="cart-item-price">
                                  {money.format(itemPrice)} {isCaja ? "c/caja" : "c/u"} · <strong className="text-primary">{money.format(itemSubtotal)}</strong>
                                </small>
                              </div>
                              <div className="cart-stepper">
                                <button
                                  type="button"
                                  className={`cart-stepper-btn minus ${item.quantity === 1 ? "is-trash" : ""}`}
                                  onClick={() => updateQuantity(key, item.quantity - 1)}
                                  title={item.quantity === 1 ? "Eliminar del pedido" : "Restar 1"}
                                  aria-label="Quitar unidad"
                                >
                                  {item.quantity === 1 ? <Trash2 size={14} strokeWidth={2.2} /> : <Minus size={14} strokeWidth={2.5} />}
                                </button>
                                <span className="cart-stepper-val">{item.quantity}</span>
                                <button
                                  type="button"
                                  className="cart-stepper-btn plus"
                                  onClick={() => updateQuantity(key, item.quantity + 1)}
                                  title="Sumar 1"
                                  aria-label="Agregar unidad"
                                >
                                  <Plus size={14} strokeWidth={2.5} />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <hr />
                      <div className="d-flex justify-content-between">
                        <strong>Total</strong>
                        <strong>{money.format(total)}</strong>
                      </div>
                      <button
                        className="btn btn-primary w-100 mt-3"
                        onClick={createOrder}
                        disabled={submitting || !selectedAddress}
                      >
                        {submitting ? "Enviando..." : "Enviar pedido"}
                      </button>
                    </>
                  ) : (
                    <p className="text-secondary mt-3 mb-0">Agrega productos para comenzar.</p>
                  )}
                </div>
              </aside>
            </div>
            </>
          ) : (
            <section className="content-panel">
              <div className="panel-heading">
                <div>
                  <h2>Todos tus pedidos</h2>
                  <p>Revisa el estado e importe de cada solicitud.</p>
                </div>
                <span className="panel-count">{orders.length} pedidos</span>
              </div>
              <div className="order-history mt-4">
                {orders.length ? (
                  orders.map((order) => (
                    <article className="order-history-row" key={order.id}>
                      <div>
                        <strong>Pedido {order.id.slice(0, 8).toUpperCase()}</strong>
                        <small>{order.detalles.length} productos</small>
                      </div>
                      <span className={`order-status order-${order.estado.toLowerCase()}`}>
                        {order.estado.replace("_", " ")}
                      </span>
                      <strong>{money.format(order.total)}</strong>
                    </article>
                  ))
                ) : (
                  <p className="text-secondary mb-0">Aún no registras pedidos.</p>
                )}
              </div>
            </section>
          )}
        </div>
      </section>
    </main>
  );

}

function PublicCatalog() {
  const [pdfObjectUrl, setPdfObjectUrl] = useState(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return undefined;
    startedRef.current = true;
    let objectUrl;
    Swal.fire({
      title: "Generando catálogo...",
      html: '<div style="background:#e5e9f0;border-radius:999px;height:10px;overflow:hidden;margin-top:6px"><div id="catalog-progress-bar" style="background:#146cce;height:100%;width:0%;transition:width .15s"></div></div><p id="catalog-progress-text" style="margin:10px 0 0;font-weight:700;color:#146cce">0%</p>',
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      animation: false,
    });
    api
      .get("/catalogo-publico", {
        responseType: "blob",
        onDownloadProgress: (event) => {
          const percent = event.total ? Math.round((event.loaded / event.total) * 100) : 0;
          const bar = document.getElementById("catalog-progress-bar");
          const text = document.getElementById("catalog-progress-text");
          if (bar) bar.style.width = `${percent}%`;
          if (text) text.textContent = `${percent}%`;
        },
      })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        setPdfObjectUrl(objectUrl);
        Swal.close();
      })
      .catch(() => {
        Swal.fire({ icon: "error", title: "No fue posible generar el catálogo", text: "Intenta nuevamente en unos minutos." });
      });
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, []);

  if (!pdfObjectUrl) return null;

  return <iframe title="Catálogo Público Distribuidora Tridente" src={pdfObjectUrl} style={{ position: "fixed", inset: 0, width: "100%", height: "100%", border: "none" }} />;
}

function App() {
  const initialSession = getStoredSession();
  const [customer, setCustomer] = useState(
    initialSession?.role === "customer" ? initialSession.customer : null
  );
  const [view, setView] = useState(
    initialSession?.role === "admin" ? "admin-dashboard" : "customer-access"
  );

  useEffect(() => {
    if (initialSession?.role === "customer" && initialSession.token) {
      api.get("/cliente/perfil")
        .then(({ data }) => {
          setCustomer(data);
          saveSessionStorage(initialSession.token, "customer", data);
        })
        .catch(() => {
          // Si el token es inválido, el interceptor 401 limpiará la sesión
        });
    }
  }, []);

  const handleInactivityLogout = useCallback(() => {
    clearSessionStorage();
    setAdminToken(null);
    setCustomerToken(null);
    setCustomer(null);
    setView("customer-access");
  }, []);

  useSessionInactivity({
    active: Boolean(customer) || view === "admin-dashboard",
    onLogout: handleInactivityLogout,
  });

  const isPublicCatalogRoute = window.location.pathname.replace(/\/$/, "").toLowerCase() === "/public/catalogo";

  if (isPublicCatalogRoute) return <PublicCatalog />;
  if (customer) return <Shop customer={customer} onProfileUpdated={setCustomer} onLogout={() => { clearSessionStorage(); setCustomerToken(null); setCustomer(null); }} />;
  if (view === "admin-dashboard") return <AdminDashboard onLogout={() => { clearSessionStorage(); setAdminToken(null); setView("customer-access"); }} />;
  if (view === "admin-access") return <AdminAccess onLogin={() => setView("admin-dashboard")} onCustomerAccess={() => setView("customer-access")} />;
  return <Access onCustomerLogin={setCustomer} onAdminLogin={() => setView("admin-dashboard")} />;
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="d-flex flex-column align-items-center justify-content-center min-vh-100 p-4 text-center">
          <h2 className="mb-2 text-danger fw-bold">Ocurrió un problema inesperado</h2>
          <p className="text-secondary mb-4">
            {this.state.error?.message || "La aplicación encontró un error al procesar la vista."}
          </p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
          >
            Recargar aplicación
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
);
