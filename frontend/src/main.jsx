import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Boxes, CheckCircle2, ClipboardList, DollarSign, Eye, FileText, FolderTree, LayoutDashboard, LogOut, MapPin, Menu, Minus, Package, Pencil, Plus, RotateCcw, Save, Search, Settings, ShoppingBag, Trash2, Users, X } from "lucide-react";

import "bootstrap/dist/css/bootstrap.min.css";
import "./styles.css";
import Swal from "sweetalert2";
import { api, setAdminToken, setCustomerToken } from "./services/api";
import SystemSettings from "./pages/admin/SystemSettings";
import NotificationLogs from "./pages/admin/NotificationLogs";


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
        onCustomerLogin(profile.data);
      } else {
        const { data } = await api.post("/login", { correo: email, password });
        setAdminToken(data.access_token);
        onAdminLogin();
      }
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return <main className="access-shell"><section className="access-brand"><h1>Pedidos simples.<br />Despachos claros.</h1><p>Haz tu pedido y revisa su estado desde un solo lugar.</p></section><form className="access-form" onSubmit={submit}>
    <div className="access-form-heading"><BrandMark /><p className="eyebrow">{customerAccess ? "PORTAL DE CLIENTES" : "ADMINISTRACION"}</p><h2>{customerAccess ? "Realiza tu pedido" : "Bienvenido"}</h2><p>Ingresa con tu correo electrónico y contraseña.</p></div>
    <label className="form-check mb-3"><input className="form-check-input" type="checkbox" checked={customerAccess} onChange={(event) => setCustomerAccess(event.target.checked)} /><span className="ms-2">Acceder como cliente</span></label>
    <label htmlFor="access-email" className="form-label">Correo electrónico</label>
    <input id="access-email" className="form-control form-control-lg" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
    <label htmlFor="access-password" className="form-label mt-3">Contraseña</label>
    <input id="access-password" className="form-control form-control-lg" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
    {error && <p className="text-danger mt-3 mb-0">{error}</p>}
    <button className="btn btn-primary btn-lg w-100 mt-4" disabled={loading}>{loading ? "Ingresando..." : "Ingresar"}</button>
  </form></main>;
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
      onLogin();
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return <main className="access-shell"><section className="access-brand"><h1>Gestiona cada pedido con control.</h1><p>Catálogo, clientes y despachos en una vista operativa.</p></section><form className="access-form" onSubmit={submit}>
    <div className="access-form-heading"><BrandMark /><p className="eyebrow">ADMINISTRACION</p><h2>Bienvenido</h2><p>Ingresa con tus credenciales para continuar.</p></div>
    <label htmlFor="admin-email" className="form-label">Correo</label>
    <input id="admin-email" className="form-control form-control-lg" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
    <label htmlFor="admin-password" className="form-label mt-3">Contraseña</label>
    <input id="admin-password" className="form-control form-control-lg" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
    {error && <p className="text-danger mt-3 mb-0">{error}</p>}
    <button className="btn btn-primary btn-lg w-100 mt-4" disabled={loading}>{loading ? "Ingresando..." : "Ingresar"}</button>
    <button className="btn btn-link w-100 mt-3" type="button" onClick={onCustomerAccess}>Volver a pedidos</button>
  </form></main>;
}

function ProductManagerLegacy({ categories }) {
  const emptyProduct = { categoria_id: "", codigo: "", nombre: "", precio: "", cantidad: "0", imagen_url: "", activo: true };
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
    setForm({ ...product, precio: String(product.precio), cantidad: String(product.cantidad), imagen_url: product.imagen_url ?? "" });
    setError("");
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (!form.categoria_id) {
      setError("Selecciona una categoría para el producto.");
      return;
    }
    setSaving(true);
    const payload = { ...form, nombre: form.nombre.trim().toUpperCase(), precio: Number(form.precio), cantidad: Number(form.cantidad), imagen_url: form.imagen_url || null };
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
  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Productos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de inventario</span><button className="btn btn-primary" onClick={openCreate}><Plus size={18} />Nuevo producto</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Controla tu Productos</h2><p>Gestiona precios, disponibilidad y stock para los pedidos de clientes.</p></div><div className="summary-metric"><span>{products.length}</span><small>Productos registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de productos</h2><p>Productos activos e inactivos del catálogo.</p></div><span className="panel-count">{products.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 mb-0 category-notice" role="alert"><CheckCircle2 size={18} />{notice}<button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando productos...</p> : <div className="product-table mt-4"><div className="product-table-head"><span>Producto</span><span className="d-none d-md-block">Categoría</span><span>Precio</span><span>Stock</span><span>Estado</span><span>Acciones</span></div>{products.length ? products.map((product) => <div className="product-row" key={product.id}><div className="product-name"><span className="product-thumb">{product.imagen_url ? <img src={product.imagen_url} alt="" /> : <Package size={18} />}</span><div><strong>{product.nombre}</strong><small>{product.codigo}</small></div></div><span className="d-none d-md-block product-category">{categoryName(product.categoria_id)}</span><strong>{money.format(product.precio)}</strong><span>{product.cantidad}</span><span className={product.activo ? "status-active" : "status-inactive"}>{product.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openEdit(product)} aria-label={`Editar ${product.nombre}`}><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay productos. Agrega el primero para comenzar.</p>}</div>}</section></div>{(editingProduct || form.categoria_id) && <div className="modal-backdrop-custom" role="presentation"><form className="category-modal product-modal" onSubmit={saveProduct} role="dialog" aria-modal="true" aria-labelledby="product-form-title"><header><div><p className="eyebrow">CATALOGO</p><h2 id="product-form-title">{editingProduct ? "Editar producto" : "Nuevo producto"}</h2></div><button type="button" className="icon-button" onClick={() => { setEditingProduct(null); setForm(emptyProduct); }} aria-label="Cerrar formulario"><X size={19} /></button></header><div className="modal-body-custom"><div className="product-form-grid"><div className="product-form-wide"><label htmlFor="product-category" className="form-label">Categoría</label><select id="product-category" className="form-select" value={form.categoria_id} onChange={(event) => setField("categoria_id", event.target.value)} required><option value="">Selecciona una categoría</option>{categories.filter((category) => category.activo || category.id === form.categoria_id).map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}</select></div><div><label htmlFor="product-code" className="form-label">Código</label><input id="product-code" className="form-control" value={form.codigo} onChange={(event) => setField("codigo", event.target.value)} maxLength="50" required /></div><div><label htmlFor="product-stock" className="form-label">Stock</label><input id="product-stock" className="form-control" type="number" min="0" value={form.cantidad} onChange={(event) => setField("cantidad", event.target.value)} required /></div><div className="product-form-wide"><label htmlFor="product-name" className="form-label">Nombre</label><input id="product-name" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value)} maxLength="180" required autoFocus /></div><div><label htmlFor="product-price" className="form-label">Precio base</label><input id="product-price" className="form-control" type="number" min="1" step="1" value={form.precio} onChange={(event) => setField("precio", event.target.value)} required /></div><div><label htmlFor="product-image" className="form-label">URL imagen</label><input id="product-image" className="form-control" type="url" placeholder="https://..." value={form.imagen_url} onChange={(event) => setField("imagen_url", event.target.value)} /></div></div><div className="status-toggle"><div><strong>Producto disponible</strong><small>Los productos inactivos no aparecen a los clientes.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div></div><footer><button type="button" className="btn btn-light" onClick={() => { setEditingProduct(null); setForm(emptyProduct); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar producto</>}</button></footer></form></div>}</>;
}

function ProductManager({ categories }) {
  const blankProduct = { categoria_id: "", codigo: "", nombre: "", precio: "", cantidad: "0", imagen_url: "", activo: true };
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
    setForm(current ? { ...current, precio: String(current.precio), cantidad: String(current.cantidad), imagen_url: current.imagen_url ?? "" } : { ...blankProduct, categoria_id: categories.find((category) => category.activo)?.id ?? "" });
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
    const payload = { ...form, nombre: form.nombre.trim().toUpperCase(), precio: Number(form.precio), cantidad: Number(form.cantidad), imagen_url: form.imagen_url || null };
    if (!payload.categoria_id) {
      setError("Selecciona una categoría.");
      return;
    }
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

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Productos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de Productos</span><button className="btn btn-primary" onClick={() => openProduct()}><Plus size={18} />Nuevo producto</button></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Controla tus Productos</h2><p>Gestiona precios, disponibilidad y stock para los pedidos de clientes.</p></div><div className="summary-metric"><span>{products.length}</span><small>Productos registrados</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de productos</h2><p>Productos activos e inactivos del catálogo.</p></div><span className="panel-count">{products.length} registros</span></div>{notice && <div className="alert alert-success alert-dismissible fade show mt-3 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando productos...</p> : <div className="product-table mt-4"><div className="product-table-head"><span>Producto</span><span>Categoría</span><span>Precio</span><span>Stock</span><span>Estado</span><span>Acciones</span></div>{products.map((item) => <div className="product-row" key={item.id}><div className="product-name"><span className="product-thumb">{imageSource(item.imagen_url) ? <img src={imageSource(item.imagen_url)} alt="" /> : <Package size={18} />}</span><div><strong>{item.nombre}</strong><small>{item.codigo}</small></div></div><span className="product-category">{categoryName(item.categoria_id)}</span><strong>{money.format(item.precio)}</strong><span>{item.cantidad}</span><span className={item.activo ? "status-active" : "status-inactive"}>{item.activo ? "Activo" : "Inactivo"}</span><button className="icon-button category-edit" onClick={() => openProduct(item)} aria-label={`Editar ${item.nombre}`}><Pencil size={16} /></button></div>)}</div>}</section></div>{(product || form.categoria_id) && <div className="modal-backdrop-custom"><form className="category-modal product-modal" onSubmit={saveProduct}><header><div><p className="eyebrow">CATALOGO</p><h2>{product ? "Editar producto" : "Nuevo producto"}</h2></div><button type="button" className="icon-button" onClick={() => { setProduct(null); setForm(blankProduct); }}><X size={19} /></button></header><div className="modal-body-custom"><div className="product-form-grid"><div className="product-form-wide"><label className="form-label" htmlFor="product-category-base64">Categoría</label><select id="product-category-base64" className="form-select" value={form.categoria_id} onChange={(event) => setField("categoria_id", event.target.value)} required><option value="">Selecciona una categoría</option>{categories.filter((category) => category.activo || category.id === form.categoria_id).map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}</select></div><div><label className="form-label" htmlFor="product-code-base64">Código</label><input id="product-code-base64" className="form-control" value={form.codigo} onChange={(event) => setField("codigo", event.target.value)} required /></div><div><label className="form-label" htmlFor="product-stock-base64">Stock</label><input id="product-stock-base64" className="form-control" type="number" min="0" value={form.cantidad} onChange={(event) => setField("cantidad", event.target.value)} required /></div><div className="product-form-wide"><label className="form-label" htmlFor="product-name-base64">Nombre</label><input id="product-name-base64" className="form-control" value={form.nombre} onChange={(event) => setField("nombre", event.target.value.toUpperCase())} required /></div><div><label className="form-label" htmlFor="product-price-base64">Precio base</label><input id="product-price-base64" className="form-control" type="number" min="1" value={form.precio} onChange={(event) => setField("precio", event.target.value)} required /></div><div><label className="form-label" htmlFor="product-image-base64">Imagen JPG</label><input id="product-image-base64" className="form-control" type="file" accept=".jpg,.jpeg,image/jpeg" onChange={attachImage} /><small className="form-text">Solo JPG, máximo 5 MB. Se guarda en Base64.</small></div></div>{imageSource(form.imagen_url) && <div className="image-preview"><img src={imageSource(form.imagen_url)} alt="Vista previa" /><button className="btn btn-link btn-sm" type="button" onClick={() => setField("imagen_url", "")}>Quitar imagen</button></div>}<div className="status-toggle"><div><strong>Producto disponible</strong><small>Los productos inactivos no aparecen a los clientes.</small></div><label className="switch"><input type="checkbox" checked={form.activo} onChange={(event) => setField("activo", event.target.checked)} /><span /></label></div></div><footer><button className="btn btn-light" type="button" onClick={() => { setProduct(null); setForm(blankProduct); }}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar producto</>}</button></footer></form></div>}</>;
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

  function availableTransitions(order) {
    const transitions = { Pedido: ["Despachado", "Cancelado"], Despachado: ["Entregado", "Cancelado"] };
    return transitions[order.estado.nombre] ?? [];
  }

  async function changeOrderStatus() {
    if (!confirmation) return;
    const nextState = states.find((state) => state.nombre === confirmation.nextState);
    if (!nextState) {
      setError("No fue posible identificar el estado seleccionado.");
      setConfirmation(null);
      return;
    }
    if (confirmation.nextState === "Entregado" && deliveryPayment === null) {
      setError("Indica si el cliente pagó el pedido.");
      return;
    }
    if (confirmation.nextState === "Entregado" && !deliveryPayment && (!Number.isInteger(Number(creditDays)) || Number(creditDays) < 1)) {
      setError("Indica una cantidad válida de días de crédito.");
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
      setNotice(`Pedido ${data.id.slice(0, 8).toUpperCase()} actualizado a ${data.estado.nombre}.`);
      setError("");
      setConfirmation(null);
      setDeliveryPayment(null);
      setCreditDays("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "No fue posible actualizar el estado del pedido.");
      setConfirmation(null);
    } finally {
      setUpdatingState(false);
    }
  }

  async function exportOrderPdf(order) {
    const code = order.id.slice(0, 8).toUpperCase();
    const { data } = await api.get(`/pedidos/${order.id}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `pedido-${code}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    if (!selectedOrder) return undefined;
    const actions = document.querySelector(".admin-app .order-detail-modal .order-state-actions");
    if (!actions || actions.querySelector(".export-order-pdf")) return undefined;
    const button = document.createElement("button");
    button.className = "btn btn-outline-primary export-order-pdf";
    button.type = "button";
    button.textContent = "Exportar PDF";
    const exportPdf = () => exportOrderPdf(selectedOrder);
    button.addEventListener("click", exportPdf);
    actions.prepend(button);
    return () => {
      button.removeEventListener("click", exportPdf);
      button.remove();
    };
  }, [selectedOrder]);

  useEffect(() => {
    const messageText = notice || error;
    if (!selectedOrder || !messageText) return undefined;
    const body = document.querySelector(".admin-app .order-detail-modal .modal-body-custom");
    if (!body || body.querySelector(".order-detail-notice")) return undefined;
    const alert = document.createElement("div");
    alert.className = `alert alert-${notice ? "success" : "danger"} order-detail-notice`;
    alert.setAttribute("role", notice ? "status" : "alert");
    const message = document.createElement("span");
    message.textContent = messageText;
    const dismiss = document.createElement("button");
    dismiss.className = "btn-close";
    dismiss.type = "button";
    dismiss.setAttribute("aria-label", "Cerrar mensaje");
    const dismissMessage = () => {
      setNotice("");
      setError("");
    };
    dismiss.addEventListener("click", dismissMessage);
    alert.append(message, dismiss);
    body.prepend(alert);
    return () => {
      dismiss.removeEventListener("click", dismissMessage);
      alert.remove();
    };
  }, [selectedOrder, notice, error]);

  useEffect(() => {
    setOrderPage(1);
  }, [filters.estado, filters.codigo, filters.desde, filters.hasta]);

  const visibleOrders = orders.filter((order) => {
    const code = filters.codigo.trim().toUpperCase();
    const createdAt = order.created_at ? new Date(order.created_at) : null;
    const from = filters.desde ? new Date(`${filters.desde}T00:00:00`) : null;
    const to = filters.hasta ? new Date(`${filters.hasta}T23:59:59.999`) : null;
    return order.estado.nombre === filters.estado
      && (!code || order.id.slice(0, 8).toUpperCase().includes(code))
      && (!from || (createdAt && createdAt >= from))
      && (!to || (createdAt && createdAt <= to));
  });

  const totalPages = Math.ceil(visibleOrders.length / pageSize) || 1;
  const paginatedOrders = visibleOrders.slice((orderPage - 1) * pageSize, orderPage * pageSize);

  const dateFormatter = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">OPERACION</p><h1>Pedidos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Seguimiento de pedidos</span></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">PEDIDOS</p><h2>Controla todos los pedidos</h2><p>Consulta solicitudes de todos tus clientes y revisa su detalle.</p></div><div className="summary-metric"><span>{visibleOrders.length}</span><small>Pedidos visibles</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de pedidos</h2><p>Filtra por estado, código de pedido o rango de fechas.</p></div><span className="panel-count">{visibleOrders.length} pedidos</span></div><div className="order-history-filters"><label>Estado<select className="form-select" value={filters.estado} onChange={(event) => setFilters((current) => ({ ...current, estado: event.target.value }))}><option>Pedido</option><option>Despachado</option><option>Entregado</option><option>Cancelado</option></select></label><label>Pedido<input className="form-control" type="search" placeholder="Ej. 4CB969B1" value={filters.codigo} onChange={(event) => setFilters((current) => ({ ...current, codigo: event.target.value }))} /></label><label>Desde<input className="form-control" type="date" value={filters.desde} onChange={(event) => setFilters((current) => ({ ...current, desde: event.target.value }))} /></label><label>Hasta<input className="form-control" type="date" value={filters.hasta} onChange={(event) => setFilters((current) => ({ ...current, hasta: event.target.value }))} /></label></div>{notice && <div className="alert alert-success mt-3 mb-0 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando pedidos...</p> : <><div className="admin-order-table mt-4"><div className="admin-order-head"><span>Pedido</span><span>Cliente</span><span>Fecha</span><span>Estado</span><span>Total</span><span>Acciones</span></div>{paginatedOrders.map((order) => <article className="admin-order-row" key={order.id}><div><strong>Pedido {order.id.slice(0, 8).toUpperCase()}</strong><small>{order.detalles.length} productos</small></div><div><strong>{order.cliente.nombre || order.cliente.rut || order.cliente.celular || "Cliente"}</strong><small>{order.cliente.rut || order.cliente.celular || "Sin identificador"}</small></div><span>{order.created_at ? dateFormatter.format(new Date(order.created_at)) : "-"}</span><span className={`order-status order-${order.estado.nombre.toLowerCase()}`}>{order.estado.nombre}</span><strong>{money.format(order.total)}</strong><button className="icon-button category-edit" type="button" onClick={() => setSelectedOrder(order)} aria-label={`Ver detalle del pedido ${order.id.slice(0, 8).toUpperCase()}`}><Eye size={16} /></button></article>)}{!visibleOrders.length && <p className="history-filter-empty">No hay pedidos que coincidan con los filtros.</p>}</div>{visibleOrders.length > pageSize && <nav className="product-pagination mt-4" aria-label="Paginación de pedidos"><small>Página {orderPage} de {totalPages} · {visibleOrders.length} pedidos</small><button className="btn btn-outline-primary btn-sm" type="button" disabled={orderPage === 1} onClick={() => setOrderPage((current) => Math.max(1, current - 1))}>Anterior</button><button className="btn btn-primary btn-sm" type="button" disabled={orderPage === totalPages} onClick={() => setOrderPage((current) => Math.min(totalPages, current + 1))}>Siguiente</button></nav>}</>}</section></div>{selectedOrder && <div className="modal-backdrop-custom"><section className="category-modal product-modal order-detail-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">PEDIDO</p><h2>Detalle del pedido</h2></div><button className="icon-button" type="button" onClick={() => setSelectedOrder(null)} aria-label="Cerrar detalle"><X size={19} /></button></header><div className="modal-body-custom"><div className="order-detail-meta"><span>Pedido {selectedOrder.id.slice(0, 8).toUpperCase()}</span><span>{selectedOrder.cliente.nombre || selectedOrder.cliente.rut || "Cliente"}</span><span>{selectedOrder.created_at ? dateFormatter.format(new Date(selectedOrder.created_at)) : ""}</span></div><div className="order-detail-lines"><div><span>Producto</span><span>Cantidad</span><span>Precio</span><span>Subtotal</span></div>{selectedOrder.detalles.map((line) => <div key={line.producto_id}><span>{line.nombre_producto}</span><span>{line.cantidad}</span><span>{money.format(line.precio_unitario)}</span><strong>{money.format(line.subtotal)}</strong></div>)}</div><div className="order-detail-total"><strong>Total</strong><strong>{money.format(selectedOrder.total)}</strong></div>

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

</div><footer><div className="order-state-actions">{availableTransitions(selectedOrder).map((nextState) => <button className={nextState === "Cancelado" ? "btn btn-outline-danger" : "btn btn-primary"} type="button" key={nextState} onClick={() => { setDeliveryPayment(null); setCreditDays(""); setConfirmation({ order: selectedOrder, nextState }); }}>{nextState === "Despachado" ? "Despachar" : nextState === "Entregado" ? "Entregar" : "Cancelar pedido"}</button>)}</div><button className="btn btn-light" type="button" onClick={() => setSelectedOrder(null)}>Cerrar</button></footer></section></div>}{confirmation && <div className="modal-backdrop-custom"><section className="category-modal confirmation-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">CONFIRMAR ACCION</p><h2>{confirmation.nextState === "Entregado" ? "¿Cliente pagó su pedido?" : "¿Cambiar estado del pedido?"}</h2></div><button className="icon-button" type="button" onClick={() => setConfirmation(null)} aria-label="Cerrar confirmación"><X size={19} /></button></header><div className="modal-body-custom"><p>El pedido <strong>{confirmation.order.id.slice(0, 8).toUpperCase()}</strong> cambiará de <strong>{confirmation.order.estado.nombre}</strong> a <strong>{confirmation.nextState}</strong>.</p>{confirmation.nextState === "Entregado" ? <><div className="payment-choice"><button type="button" className={deliveryPayment === true ? "btn btn-primary" : "btn btn-outline-primary"} onClick={() => { setDeliveryPayment(true); setCreditDays(""); }}>Sí, pagó</button><button type="button" className={deliveryPayment === false ? "btn btn-primary" : "btn btn-outline-primary"} onClick={() => setDeliveryPayment(false)}>No, queda a crédito</button></div>{deliveryPayment === false && <div className="mt-3"><label className="form-label" htmlFor="credit-days">Días de crédito</label><input id="credit-days" className="form-control" type="number" min="1" step="1" value={creditDays} onChange={(event) => setCreditDays(event.target.value)} required autoFocus /><small className="form-text">El vencimiento se calcula desde la fecha de entrega.</small></div>}</> : <p className="mb-0">Esta acción actualizará el estado visible para el cliente.</p>}</div><footer><button className="btn btn-light" type="button" disabled={updatingState} onClick={() => setConfirmation(null)}>Volver</button><button className={confirmation.nextState === "Cancelado" ? "btn btn-danger" : "btn btn-primary"} type="button" disabled={updatingState} onClick={changeOrderStatus}>{updatingState ? "Actualizando..." : confirmation.nextState === "Entregado" ? "Finalizar entrega" : "Confirmar cambio"}</button></footer></section></div>}</>;
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
  const customerName = (credit) => credit.cliente.nombre || credit.cliente.rut || credit.cliente.celular || "Cliente";
  const dueDays = (credit) => Math.max(0, Math.ceil((new Date(credit.fecha_vencimiento) - new Date()) / 86_400_000));

  return <><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">COBRANZAS</p><h1>Créditos</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Seguimiento de cuentas por cobrar</span></div></header><div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">CRÉDITOS</p><h2>{paidFilter === "pending" ? "Créditos pendientes" : "Historial de créditos pagados"}</h2><p>Controla los plazos de pago registrados al entregar los pedidos.</p></div><div className="summary-metric"><span>{credits.length}</span><small>{paidFilter === "pending" ? "Pendientes de pago" : "Pagados"}</small></div></section><section className="content-panel"><div className="panel-heading"><div><h2>Listado de créditos</h2><p>Consulta vencimientos y registra pagos recibidos.</p></div><span className="panel-count">{credits.length} registros</span></div><div className="credit-filters"><label htmlFor="credit-status">Vista</label><select id="credit-status" className="form-select" value={paidFilter} onChange={(event) => setPaidFilter(event.target.value)}><option value="pending">Pendientes</option><option value="paid">Historial pagados</option></select></div>{notice && <div className="alert alert-success mt-3 mb-0 category-notice"><CheckCircle2 size={18} />{notice}<button className="btn-close" type="button" onClick={() => setNotice("")} /></div>}{error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}{loading ? <p className="mt-4 text-secondary">Cargando créditos...</p> : <div className="credit-table mt-4"><div className="credit-table-head"><span>Cliente</span><span>Pedido</span><span>Días crédito</span><span>Entrega</span><span>Días al vencimiento</span><span>Vencimiento</span><span>{paidFilter === "paid" ? "Fecha pago" : "Acciones"}</span></div>{credits.length ? credits.map((credit) => <article className="credit-row" key={credit.id}><div><strong>{customerName(credit)}</strong><small>{credit.cliente.rut || credit.cliente.celular || "Sin identificador"}</small></div><strong>#{credit.pedido.id.slice(0, 8).toUpperCase()}</strong><span>{credit.dias_credito}</span><span>{dateFormatter.format(new Date(credit.fecha_entrega))}</span><span>{paidFilter === "pending" ? dueDays(credit) : "-"}</span><span>{dateFormatter.format(new Date(credit.fecha_vencimiento))}</span>{paidFilter === "paid" ? <span>{credit.fecha_pago ? dateFormatter.format(new Date(credit.fecha_pago)) : "-"}</span> : <button className="btn btn-outline-primary btn-sm" type="button" onClick={() => { setPaymentDate(new Date().toISOString().slice(0, 10)); setSelectedCredit(credit); }}>Marcar pagado</button>}</article>) : <p className="history-filter-empty">No hay créditos {paidFilter === "pending" ? "pendientes" : "pagados"}.</p>}</div>}</section></div>{selectedCredit && <div className="modal-backdrop-custom"><section className="category-modal confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="credit-payment-title"><header><div><p className="eyebrow">REGISTRAR PAGO</p><h2 id="credit-payment-title">¿Confirmar pago del crédito?</h2></div><button className="icon-button" type="button" onClick={() => setSelectedCredit(null)} aria-label="Cerrar confirmación"><X size={19} /></button></header><div className="modal-body-custom"><p>El crédito del pedido <strong>#{selectedCredit.pedido.id.slice(0, 8).toUpperCase()}</strong> quedará marcado como pagado.</p><label className="form-label" htmlFor="credit-payment-date">Fecha de pago</label><input id="credit-payment-date" className="form-control" type="date" value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} required /></div><footer><button className="btn btn-light" type="button" disabled={saving} onClick={() => setSelectedCredit(null)}>No</button><button className="btn btn-primary" type="button" disabled={saving || !paymentDate} onClick={confirmPayment}>{saving ? "Guardando..." : "Sí, marcar pagado"}</button></footer></section></div>}</>;
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

  const salesOrders = orders.filter((order) => {
    const createdAt = order.created_at ? new Date(order.created_at) : null;
    const from = filters.desde ? new Date(`${filters.desde}T00:00:00`) : null;
    const to = filters.hasta ? new Date(`${filters.hasta}T23:59:59.999`) : null;
    return order.estado.nombre !== "Cancelado" && (!from || (createdAt && createdAt >= from)) && (!to || (createdAt && createdAt <= to));
  });
  const totalSales = salesOrders.reduce((total, order) => total + Number(order.total), 0);
  const totalUnits = salesOrders.reduce((total, order) => total + order.detalles.reduce((sum, line) => sum + line.cantidad, 0), 0);
  const customerRanking = Object.values(salesOrders.reduce((ranking, order) => {
    const id = order.cliente.id;
    const name = order.cliente.nombre || order.cliente.rut || order.cliente.celular || "Cliente";
    ranking[id] ??= { id, name, orders: 0, total: 0 };
    ranking[id].orders += 1;
    ranking[id].total += Number(order.total);
    return ranking;
  }, {})).sort((first, second) => second.total - first.total).slice(0, 10);
  const productRanking = Object.values(salesOrders.reduce((ranking, order) => {
    order.detalles.forEach((line) => {
      ranking[line.producto_id] ??= { id: line.producto_id, name: line.nombre_producto, units: 0, total: 0 };
      ranking[line.producto_id].units += line.cantidad;
      ranking[line.producto_id].total += Number(line.subtotal);
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
      await api.post("/categorias", { nombre: name.trim(), activo: true, en_catalogo_publico: true });
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
  ];

  return <main className="admin-app"><aside className={`admin-sidebar ${menuOpen ? "is-open" : ""}`}><div className="sidebar-brand"><BrandMark /><span>Distribuidora Tridente</span><button className="sidebar-close d-lg-none" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú"><X size={20} /></button></div><p className="sidebar-label">OPERACION</p><nav className="sidebar-nav">{navigation.map(([Icon, label, key, enabled]) => <button key={label} className={section === key ? "active" : ""} disabled={!enabled} onClick={() => { setSection(key); setConfigurationOpen(false); setMenuOpen(false); }}><Icon size={19} /><span>{label}</span>{!enabled && <small>Pronto</small>}</button>)}<div className="sidebar-configuration"><button className={configurationOpen || section === "users" || section === "customers" || section === "settings" || section === "notification_logs" ? "active" : ""} onClick={() => setConfigurationOpen((current) => !current)}><Settings size={19} /><span>Configuración</span></button>{configurationOpen && <div className="sidebar-submenu"><button className={section === "users" ? "active" : ""} onClick={() => { setSection("users"); setMenuOpen(false); }}><Users size={17} /><span>Usuarios</span></button><button className={section === "customers" ? "active" : ""} onClick={() => { setSection("customers"); setMenuOpen(false); }}><Users size={17} /><span>Clientes</span></button><button className={section === "settings" ? "active" : ""} onClick={() => { setSection("settings"); setMenuOpen(false); }}><Settings size={17} /><span>Ajustes</span></button><button className={section === "notification_logs" ? "active" : ""} onClick={() => { setSection("notification_logs"); setMenuOpen(false); }}><Activity size={17} /><span>Logs Envíos</span></button></div>}</div></nav><div className="sidebar-bottom"><div className="sidebar-user"><span>RE</span><div><strong>Administrador</strong><small>Sesión activa</small></div></div><button className="logout-button" onClick={logout}><LogOut size={18} />Cerrar sesión</button></div></aside><div className="sidebar-backdrop d-lg-none" hidden={!menuOpen} onClick={() => setMenuOpen(false)} /><button className="icon-button admin-mobile-menu d-lg-none" type="button" onClick={() => setMenuOpen(true)} aria-label="Abrir menú"><Menu size={21} /></button>
    {section === "summary" ? <section className="admin-workspace"><AdminSalesDashboard /></section> : section === "products" ? <section className="admin-workspace"><ProductManager categories={categories} /></section> : section === "orders" ? <section className="admin-workspace"><AdminOrderManager /></section> : section === "credits" ? <section className="admin-workspace"><CreditManager /></section> : section === "notification_logs" ? <section className="admin-workspace"><NotificationLogs /></section> : section === "users" ? <section className="admin-workspace"><UserManager /></section> : section === "customers" ? <section className="admin-workspace"><CustomerManager /></section> : section === "settings" ? <section className="admin-workspace"><SystemSettings /></section> : <>

    <section className="admin-workspace"><header className="admin-topbar"><div className="topbar-title"><p className="eyebrow mb-1">CATALOGO</p><h1>Categorías</h1></div><div className="topbar-actions"><span className="topbar-date d-none d-sm-inline">Gestión de Categoría</span><button className="btn btn-primary" onClick={() => document.getElementById("category-name")?.focus()}><Plus size={18} />Nueva categoría</button></div></header>
      <div className="admin-content"><section className="admin-summary"><div><p className="eyebrow">INVENTARIO</p><h2>Organiza tu Categoría</h2><p>Las categorías agrupan los productos visibles para tus clientes.</p></div><div className="summary-metric"><span>{categories.length}</span><small>Categorías registradas</small></div></section>
        <section className="content-panel"><div className="panel-heading"><div><h2>Listado de categorías</h2><p>Administra la clasificación de tu catálogo.</p></div><span className="panel-count">{categories.length} registros</span></div><form className="category-form" onSubmit={createCategory}><div><label htmlFor="category-name" className="visually-hidden">Nombre de categoría</label><input id="category-name" className="form-control" placeholder="Escribe una nueva categoría" value={name} onChange={(event) => setName(event.target.value)} maxLength="120" required /></div><button className="btn btn-primary"><Plus size={18} />Agregar</button></form>
          {notice && <div className="alert alert-success alert-dismissible fade show mt-3 mb-0 category-notice" role="alert"><CheckCircle2 size={18} />{notice}<button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} /></div>}
          {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}
          {loading ? <p className="mt-4 text-secondary">Cargando categorías...</p> : <div className="category-table mt-4"><div className="category-table-head"><span>Categoría</span><span>Porcentaje</span><span>Catálogo Público</span><span>Estado</span><span>Acciones</span></div>{categories.length ? categories.map((category) => <div className="category-row" key={category.id}><div className="category-name"><span className="category-icon"><Boxes size={18} /></span><strong>{category.nombre}</strong></div><span className="category-percentage">{category.usa_porcentaje_cliente ? "Cliente" : `${Number(category.porcentaje)}%`}</span><span className={category.en_catalogo_publico ? "status-active" : "status-inactive"}>{category.en_catalogo_publico ? "Sí" : "No"}</span><span className={category.activo ? "status-active" : "status-inactive"}>{category.activo ? "Activa" : "Inactiva"}</span><button className="icon-button category-edit" onClick={() => openEdit(category)} aria-label={`Editar ${category.nombre}`}><Pencil size={16} /></button></div>) : <p className="text-secondary p-4 mb-0">Aún no hay categorías. Agrega la primera para comenzar.</p>}</div>}
        </section></div></section>{editingCategory && <div className="modal-backdrop-custom" role="presentation"><form className="category-modal" onSubmit={updateCategory} role="dialog" aria-modal="true" aria-labelledby="edit-category-title"><header><div><p className="eyebrow">CATEGORIA</p><h2 id="edit-category-title">Editar categoría</h2></div><button type="button" className="icon-button" onClick={() => setEditingCategory(null)} aria-label="Cerrar edición"><X size={19} /></button></header><div className="modal-body-custom"><label htmlFor="edit-category-name" className="form-label">Nombre</label><input id="edit-category-name" className="form-control" value={editName} onChange={(event) => setEditName(event.target.value)} maxLength="120" required autoFocus /><div className="status-toggle"><div><strong>Usar porcentaje del cliente</strong><small>Aplica el porcentaje configurado para el cliente.</small></div><label className="switch"><input type="checkbox" checked={editUsesCustomerPercentage} onChange={(event) => setEditUsesCustomerPercentage(event.target.checked)} /><span /></label></div>{!editUsesCustomerPercentage && <div className="mt-3"><label htmlFor="edit-category-percentage" className="form-label">Porcentaje de la categoría</label><input id="edit-category-percentage" className="form-control" type="number" min="0" max="100" step="0.01" value={editPercentage} onChange={(event) => setEditPercentage(event.target.value)} required /><small className="form-text">Se suma al precio base de los productos de esta categoría.</small></div>}<div className="status-toggle"><div><strong>Mostrar en catálogo público</strong><small>Determina si la categoría es visible para los clientes.</small></div><label className="switch"><input type="checkbox" checked={editEnCatalogoPublico} onChange={(event) => setEditEnCatalogoPublico(event.target.checked)} /><span /></label></div><div className="status-toggle"><div><strong>Estado de la categoría</strong><small>Las categorías inactivas no aparecen al cliente.</small></div><label className="switch"><input type="checkbox" checked={editActive} onChange={(event) => setEditActive(event.target.checked)} /><span /></label></div></div><footer><button type="button" className="btn btn-light" onClick={() => setEditingCategory(null)}>Cancelar</button><button className="btn btn-primary" disabled={saving}>{saving ? "Guardando..." : <><Save size={17} />Guardar cambios</>}</button></footer></form></div>}</>}</main>;
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
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [cart, setCart] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState(() => customer.direcciones?.find((address) => address.principal && address.activo)?.id ?? customer.direcciones?.find((address) => address.activo)?.id ?? "");
  const [section, setSection] = useState("create");
  const [orders, setOrders] = useState([]);
  const [historyFilters, setHistoryFilters] = useState({ estado: "Pedido", codigo: "", desde: "", hasta: "" });
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadProducts() {
    try {
      const { data } = await api.get("/productos", { params: { category_id: selectedCategory || undefined, search: query || undefined, customer_id: customer.id, page, page_size: 10 } });
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
    api.get("/categorias").then(({ data }) => setCategories(data)).catch(() => setError("No fue posible cargar las categorías."));
  }, []);

  useEffect(() => {
    const activeAddressId = customer.direcciones?.find((address) => address.principal && address.activo)?.id ?? customer.direcciones?.find((address) => address.activo)?.id ?? "";
    setSelectedAddress((current) => (current && customer.direcciones?.some((address) => address.id === current && address.activo)) ? current : activeAddressId);
  }, [customer.direcciones]);

  useEffect(() => {
    if (section !== "create") return undefined;
    const searchField = document.querySelector(".customer-workspace .search-field");
    if (!searchField || searchField.previousElementSibling?.classList.contains("customer-product-filters")) return undefined;
    const filters = document.createElement("div");
    filters.className = "customer-product-filters";
    const categorySelect = document.createElement("select");
    categorySelect.className = "form-select";
    categorySelect.setAttribute("aria-label", "Filtrar productos por categoría");
    categorySelect.append(new Option("Todas las categorías", ""));
    categories.forEach((category) => categorySelect.append(new Option(category.nombre, category.id)));
    categorySelect.value = selectedCategory;
    categorySelect.addEventListener("change", (event) => { setSelectedCategory(event.target.value); setPage(1); });
    filters.append(categorySelect);
    searchField.before(filters);
    return () => filters.remove();
  }, [categories, section]);

  useEffect(() => {
    const productGrid = document.querySelector(".customer-workspace .product-grid");
    if (section !== "create" || !productGrid || totalProducts <= 10) return undefined;
    const totalPages = Math.ceil(totalProducts / 10);
    const pager = document.createElement("nav");
    pager.className = "product-pagination customer-product-pagination";
    pager.setAttribute("aria-label", "Paginación del catálogo");
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
    productGrid.after(pager);
    return () => {
      previous.removeEventListener("click", goPrevious);
      next.removeEventListener("click", goNext);
      pager.remove();
    };
  }, [page, section, totalProducts]);

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
    root.render(<div className="modal-backdrop-custom"><section className="category-modal product-modal order-detail-modal" role="dialog" aria-modal="true"><header><div><p className="eyebrow">PEDIDO</p><h2>Detalle del pedido</h2></div><button className="icon-button" type="button" onClick={() => setSelectedOrder(null)} aria-label="Cerrar detalle"><X size={19} /></button></header><div className="modal-body-custom"><div className="order-detail-meta"><span>Pedido {selectedOrder.id.slice(0, 8).toUpperCase()}</span><span>{selectedOrder.created_at ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(selectedOrder.created_at)) : ""}</span></div><div className="order-detail-lines"><div><span>Producto</span><span>Cantidad</span><span>Precio</span><span>Subtotal</span></div>{selectedOrder.detalles.map((line) => <div key={line.producto_id}><span>{line.nombre_producto}</span><span>{line.cantidad}</span><span>{money.format(line.precio_unitario)}</span><strong>{money.format(line.subtotal)}</strong></div>)}</div><div className="order-detail-total"><strong>Total</strong><strong>{money.format(selectedOrder.total)}</strong></div></div><footer><button className="btn btn-light" type="button" onClick={() => setSelectedOrder(null)}>Cerrar</button></footer></section></div>);
    return () => { root.unmount(); container.remove(); };
  }, [selectedOrder]);

  function openHistory() {
    setHistoryFilters({ estado: "Pedido", codigo: "", desde: "", hasta: "" });
    setSection("history");
    setError("");
    loadHistory();
  }

  function add(product) {
    setCart((current) => {
      const line = current.find((item) => item.id === product.id);
      return line ? current.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item) : [...current, { ...product, quantity: 1 }];
    });
    setNotice(`${product.nombre} agregado al pedido.`);
  }

  function updateQuantity(productId, quantity) {
    setCart((current) => quantity < 1 ? current.filter((item) => item.id !== productId) : current.map((item) => item.id === productId ? { ...item, quantity } : item));
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
      const response = await api.post(`/clientes/${customer.id}/pedidos`, { direccion_id: selectedAddress, productos: cart.map((item) => ({ producto_id: item.id, cantidad: item.quantity })) });
      const orderCode = response?.data?.id?.slice(0, 8).toUpperCase() ?? "N/D";
      setCart([]);
      setNotice("");
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

  const total = cart.reduce((sum, item) => sum + Number(item.precio_cliente ?? item.precio) * item.quantity, 0);
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
          {notice && (
            <div className="alert alert-success alert-dismissible fade show">
              <CheckCircle2 size={18} />
              {notice}
              <button className="btn-close" type="button" onClick={() => setNotice("")} />
            </div>
          )}
          {error && <div className="alert alert-danger">{error}</div>}
          {section === "create" ? (
            <div className="row g-4">
              <section className="col-xl-8">
                <div className="search-field">
                  <Search size={20} />
                  <input
                    className="form-control form-control-lg"
                    placeholder="Busca por nombre de producto"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
                <div className="product-grid mt-4">
                  {products.map((product) => (
                    <article className="product" key={product.id}>
                      <div className="product-image">
                        {productImageSource(product.imagen_url) ? (
                          <img src={productImageSource(product.imagen_url)} alt="" />
                        ) : (
                          <Package size={30} />
                        )}
                      </div>
                      <small>{product.codigo}</small>
                      <h2>{product.nombre}</h2>
                      <strong>{money.format(product.precio_cliente ?? product.precio)}</strong>
                      <button className="btn btn-outline-primary mt-3" onClick={() => add(product)}>
                        <Plus size={17} />
                        Agregar
                      </button>
                    </article>
                  ))}
                </div>
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
                                  onClick={() => updateQuantity(item.id, item.quantity - 1)}
                                  title={item.quantity === 1 ? "Eliminar del pedido" : "Restar 1"}
                                  aria-label="Quitar unidad"
                                >
                                  {item.quantity === 1 ? <Trash2 size={14} strokeWidth={2.2} /> : <Minus size={14} strokeWidth={2.5} />}
                                </button>
                                <span className="cart-stepper-val">{item.quantity}</span>
                                <button
                                  type="button"
                                  className="cart-stepper-btn plus"
                                  onClick={() => updateQuantity(item.id, item.quantity + 1)}
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
  const [customer, setCustomer] = useState(null);
  const [view, setView] = useState("customer-access");

  const isPublicCatalogRoute = window.location.pathname.replace(/\/$/, "").toLowerCase() === "/public/catalogo";

  useEffect(() => {
    if (isPublicCatalogRoute) return undefined;
    const timers = new Map();
    const alertSelector = ".alert.alert-success, .alert.alert-danger";
    const prepareChartTooltips = () => {
      document.querySelectorAll(".dashboard-ranking .ranking-list li").forEach((item) => {
        const name = item.querySelector(".ranking-main strong")?.textContent?.trim();
        const valueElement = item.querySelector(".ranking-value");
        const value = valueElement?.textContent?.trim();
        const bar = item.querySelector(".ranking-main i");
        if (!name || !value || !valueElement || !bar) return;
        bar.title = `${name}: ${value}`;
        bar.setAttribute("aria-label", `${name}: ${value}`);
      });
    };
    const prepareAlert = (alert) => {
      if (alert.dataset.autoDismissPrepared) return;
      alert.dataset.autoDismissPrepared = "true";
      let dismiss = alert.querySelector(".btn-close");
      if (!dismiss) {
        dismiss = document.createElement("button");
        dismiss.className = "btn-close";
        dismiss.type = "button";
        dismiss.setAttribute("aria-label", "Cerrar mensaje");
        dismiss.addEventListener("click", () => alert.remove(), { once: true });
        alert.append(dismiss);
      }
      timers.set(alert, window.setTimeout(() => {
        if (alert.isConnected) dismiss.click();
      }, 5000));
    };
    const observer = new MutationObserver((records) => {
      records.forEach((record) => record.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.matches(alertSelector)) prepareAlert(node);
        node.querySelectorAll?.(alertSelector).forEach(prepareAlert);
      }));
      prepareChartTooltips();
    });
    document.querySelectorAll(alertSelector).forEach(prepareAlert);
    prepareChartTooltips();
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  if (isPublicCatalogRoute) return <PublicCatalog />;
  if (customer) return <Shop customer={customer} onProfileUpdated={setCustomer} onLogout={() => { setCustomerToken(null); setCustomer(null); }} />;
  if (view === "admin-dashboard") return <AdminDashboard onLogout={() => setView("customer-access")} />;
  if (view === "admin-access") return <AdminAccess onLogin={() => setView("admin-dashboard")} onCustomerAccess={() => setView("customer-access")} />;
  return <Access onCustomerLogin={setCustomer} onAdminLogin={() => setView("admin-dashboard")} />;
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
