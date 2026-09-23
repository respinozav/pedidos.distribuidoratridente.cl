import React, { useEffect, useState, useMemo } from "react";
import {
  MessageCircle,
  ExternalLink,
  ShoppingBag,
  FileText,
  Sparkles,
  Package,
  X,
  Phone,
  Truck,
  CheckCircle2,
  ChevronRight,
  Store,
} from "lucide-react";
import { api } from "../../services/api";
import PromoBannerCarousel from "../../components/PromoBannerCarousel";
import { formatImageSrc } from "../../utils/imageHelper";
import "./publicPublicidades.css";

const WHATSAPP_PHONE = "56944488407";
const WHATSAPP_DISPLAY = "+56 9 4448 8407";
const MAIN_SITE_URL = "https://www.distribuidoratridente.cl";

export default function PublicPublicidades() {
  const [banners, setBanners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBanner, setSelectedBanner] = useState(null);

  // Detección de modo embebido (iframe o query param ?embed=true)
  const isEmbedded = useMemo(() => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("embed") === "true" || urlParams.get("embed") === "1") {
        return true;
      }
      return window.self !== window.top;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    async function fetchBanners() {
      try {
        setLoading(true);
        setError(null);
        const { data } = await api.get("/publicidades", {
          headers: { Authorization: "" },
        });
        if (isMounted) {
          setBanners(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error("Error al cargar publicidades:", err);
        if (isMounted) {
          setError("No fue posible cargar las promociones en este momento.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchBanners();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleBannerAction = (banner) => {
    setSelectedBanner(banner);
  };

  const handleCloseModal = () => {
    setSelectedBanner(null);
  };

  // Construir link de WhatsApp con mensaje personalizado
  const getWhatsAppLink = (banner) => {
    let msg = `Hola Distribuidora Tridente, vi una promoción en su sitio web y quisiera cotizar para mi negocio.`;
    if (banner) {
      const prodName = banner.producto?.nombre || banner.titulo;
      const code = banner.producto?.codigo ? ` (Cód: ${banner.producto.codigo})` : "";
      msg = `Hola Distribuidora Tridente, me interesa la promoción: "${banner.titulo}" - Producto: ${prodName}${code}. ¿Podrían brindarme información y precios para comerciantes?`;
    }
    return `https://wa.me/${WHATSAPP_PHONE}?text=${encodeURIComponent(msg)}`;
  };

  return (
    <div className={`public-publicidades-page ${isEmbedded ? "is-embedded" : ""}`}>
      {/* HEADER / BARRA DE NAVEGACIÓN (solo si no está embebido) */}
      {!isEmbedded && (
        <header className="pub-header">
          <div className="pub-header-container">
            <a href={MAIN_SITE_URL} className="pub-brand" title="Ir a Distribuidora Tridente">
              <img
                src="/logo_tridente.png"
                alt="Distribuidora Tridente Logo"
                className="pub-brand-logo"
                onError={(e) => {
                  e.target.style.display = "none";
                }}
              />
              <div className="pub-brand-title">
                <span className="pub-brand-name">Distribuidora Tridente</span>
                <span className="pub-brand-subtitle">Venta Mayorista Exclusiva</span>
              </div>
            </a>

            <nav className="pub-nav-links">
              <a href={MAIN_SITE_URL} className="pub-nav-link">
                <span className="pub-link-text">Inicio</span>
              </a>
              <a
                href="/public/catalogo"
                target="_blank"
                rel="noopener noreferrer"
                className="pub-nav-link"
              >
                <span className="pub-link-text">Catálogo Digital</span>
              </a>
              <a
                href={getWhatsAppLink(null)}
                target="_blank"
                rel="noopener noreferrer"
                className="pub-btn-whatsapp"
              >
                <MessageCircle size={16} />
                <span>WhatsApp</span>
              </a>
              <a href="/" className="pub-btn-gold">
                <Store size={16} />
                <span>Portal de Pedidos</span>
              </a>
            </nav>
          </div>
        </header>
      )}

      {/* CONTENIDO PRINCIPAL */}
      <main className="pub-main-container">
        {!isEmbedded && (
          <section className="pub-hero-intro">
            <div className="pub-hero-badge">
              <Sparkles size={16} />
              <span>Venta Mayorista Exclusiva para Comerciantes</span>
            </div>
            <h1 className="pub-hero-title">
              Distribuidora Mayorista en{" "}
              <span className="pub-highlight-amber">La Serena y Ovalle</span>
            </h1>
            <p className="pub-hero-subtitle">
              Promociones especiales, descuentos por volumen y oportunidades exclusivas
              para abastecer tu almacén, minimarket o negocio con stock garantizado.
            </p>
          </section>
        )}

        {/* ÁREA DEL BANNER / CARRUSEL */}
        <section className="pub-banner-showcase">
          {loading ? (
            <div className="pub-loading-box">
              <div className="pub-spinner" />
              <p className="mb-0 text-white-50">Cargando promociones vigentes...</p>
            </div>
          ) : error ? (
            <div className="pub-empty-box">
              <Package size={40} className="text-warning mb-2" />
              <h4>{error}</h4>
              <p className="text-secondary mb-3">Puedes revisar nuestro catálogo completo o consultarnos directamente.</p>
              <div className="d-flex justify-content-center gap-2">
                <a href="/public/catalogo" target="_blank" rel="noopener noreferrer" className="pub-btn-gold">
                  Ver Catálogo Digital
                </a>
                <a href={getWhatsAppLink(null)} target="_blank" rel="noopener noreferrer" className="pub-btn-whatsapp">
                  Cotizar por WhatsApp
                </a>
              </div>
            </div>
          ) : banners.length === 0 ? (
            <div className="pub-empty-box">
              <Sparkles size={40} className="text-warning mb-2" />
              <h3>¡Próximamente nuevas promociones!</h3>
              <p className="text-secondary mb-4">
                Estamos preparando nuevos beneficios para tu comercio. Mientras tanto, explora nuestro catálogo digital con más de 500 productos.
              </p>
              <div className="d-flex justify-content-center gap-2 flex-wrap">
                <a href="/public/catalogo" target="_blank" rel="noopener noreferrer" className="pub-btn-gold">
                  <FileText size={16} />
                  Ver Catálogo Digital
                </a>
                <a href={getWhatsAppLink(null)} target="_blank" rel="noopener noreferrer" className="pub-btn-whatsapp">
                  <MessageCircle size={16} />
                  Consultar Ofertas por WhatsApp
                </a>
              </div>
            </div>
          ) : (
            <PromoBannerCarousel
              banners={banners}
              onBannerClick={handleBannerAction}
            />
          )}
        </section>

        {/* CUADRÍCULA DE TODAS LAS PROMOCIONES ACTIVAS (si hay más de 1) */}
        {!loading && banners.length > 1 && (
          <section className="pub-grid-section">
            <div className="pub-section-header">
              <div>
                <span className="pub-section-tag">Oportunidades Destacadas</span>
                <h2 className="pub-section-title">Todas las Promociones de la Semana</h2>
              </div>
              <span className="text-secondary small">
                {banners.length} promociones activas
              </span>
            </div>

            <div className="pub-cards-grid">
              {banners.map((b) => {
                const prod = b.producto;
                const imgSrc = formatImageSrc(prod?.imagen_url);
                return (
                  <article key={b.id} className="pub-card">
                    {b.etiqueta_roja && (
                      <span className="pub-card-badge">{b.etiqueta_roja}</span>
                    )}

                    <div className="pub-card-image-wrap">
                      {imgSrc ? (
                        <img
                          src={imgSrc}
                          alt={prod?.nombre || b.titulo}
                          className="pub-card-img"
                          loading="lazy"
                        />
                      ) : (
                        <div className="text-center p-3 text-secondary">
                          <Package size={36} />
                        </div>
                      )}
                    </div>

                    <div className="pub-card-content">
                      {b.etiqueta_1 && (
                        <span className="pub-card-tag">{b.etiqueta_1}</span>
                      )}
                      <h3 className="pub-card-title">{b.titulo}</h3>
                      {b.subtitulo && (
                        <p className="pub-card-subtitle">{b.subtitulo}</p>
                      )}

                      <div className="pub-card-actions">
                        <button
                          type="button"
                          className="pub-card-btn-action"
                          onClick={() => handleBannerAction(b)}
                        >
                          <MessageCircle size={15} />
                          <span>{b.texto_boton || "Cotizar"}</span>
                        </button>
                        <button
                          type="button"
                          className="pub-card-btn-secondary"
                          onClick={() => handleBannerAction(b)}
                          title="Ver detalles"
                        >
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {/* BENEFICIOS / TRUST PILLS (solo si no está embebido) */}
        {!isEmbedded && (
          <section className="pub-trust-bar">
            <div className="pub-trust-pill">
              <span className="pub-trust-icon">🚚</span>
              <span>Despacho semanal en La Serena, Coquimbo y Ovalle</span>
            </div>
            <div className="pub-trust-pill">
              <span className="pub-trust-icon">📦</span>
              <span>Stock asegurado de primeras marcas</span>
            </div>
            <div className="pub-trust-pill">
              <span className="pub-trust-icon">💼</span>
              <span>Precios y márgenes diseñados para tu comercio</span>
            </div>
          </section>
        )}
      </main>

      {/* FOOTER (solo si no está embebido) */}
      {!isEmbedded && (
        <footer className="pub-footer">
          <div className="pub-footer-content">
            <p className="mb-0">
              © {new Date().getFullYear()} Distribuidora Tridente. Todos los derechos reservados.
            </p>
            <div className="pub-footer-links">
              <a href={MAIN_SITE_URL} target="_blank" rel="noopener noreferrer">
                Sitio Principal
              </a>
              <a href="/public/catalogo" target="_blank" rel="noopener noreferrer">
                Catálogo Digital
              </a>
              <a href="/" target="_blank" rel="noopener noreferrer">
                Portal de Pedidos
              </a>
            </div>
          </div>
        </footer>
      )}

      {/* BOTÓN FLOTANTE WHATSAPP (solo si no está embebido) */}
      {!isEmbedded && (
        <a
          href={getWhatsAppLink(null)}
          target="_blank"
          rel="noopener noreferrer"
          className="pub-floating-whatsapp"
          title="Contáctanos vía WhatsApp"
        >
          <div className="pub-floating-icon-wrap">
            <MessageCircle size={18} />
          </div>
          <span>¡Escríbenos por WhatsApp!</span>
        </a>
      )}

      {/* MODAL DE ACCIÓN PÚBLICA PARA VISITANTES */}
      {selectedBanner && (
        <div
          className="pub-modal-backdrop"
          onClick={handleCloseModal}
          role="presentation"
        >
          <div
            className="pub-modal-dialog"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="pub-modal-header">
              <h3>Promoción Destacada</h3>
              <button
                type="button"
                className="pub-modal-close-btn"
                onClick={handleCloseModal}
                aria-label="Cerrar ventana"
              >
                <X size={20} />
              </button>
            </div>

            <div className="pub-modal-body">
              <div className="pub-modal-prod-preview">
                {formatImageSrc(selectedBanner.producto?.imagen_url) ? (
                  <img
                    src={formatImageSrc(selectedBanner.producto.imagen_url)}
                    alt={selectedBanner.producto?.nombre || selectedBanner.titulo}
                    className="pub-modal-prod-img"
                  />
                ) : (
                  <div className="pub-modal-prod-img d-flex align-items-center justify-content-center text-secondary">
                    <Package size={28} />
                  </div>
                )}
                <div className="pub-modal-prod-details">
                  <strong>{selectedBanner.producto?.nombre || selectedBanner.titulo}</strong>
                  {selectedBanner.producto?.codigo && (
                    <span>Código: {selectedBanner.producto.codigo}</span>
                  )}
                  {selectedBanner.subtitulo && (
                    <span className="text-light mt-1">{selectedBanner.subtitulo}</span>
                  )}
                </div>
              </div>

              <div className="pub-modal-actions-list">
                {/* Botón WhatsApp */}
                <a
                  href={getWhatsAppLink(selectedBanner)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="pub-modal-btn-whatsapp"
                  onClick={handleCloseModal}
                >
                  <MessageCircle size={18} />
                  <span>Cotizar por WhatsApp</span>
                </a>

                {/* Botón Portal de Pedidos */}
                <a
                  href="/"
                  className="pub-modal-btn-portal"
                  onClick={handleCloseModal}
                >
                  <ShoppingBag size={18} />
                  <span>Ingresar al Portal de Pedidos</span>
                </a>

                {/* Botón Catálogo */}
                <a
                  href="/public/catalogo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="pub-modal-btn-catalog"
                  onClick={handleCloseModal}
                >
                  <FileText size={18} />
                  <span>Ver Catálogo Digital Completo</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
