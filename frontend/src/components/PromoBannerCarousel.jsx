import React, { useState, useEffect, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Sparkles,
  ShoppingBag,
  Plus,
  Minus,
  Check,
  Package,
  TrendingUp,
  PackageCheck,
  X,
  Play,
  Pause,
} from "lucide-react";
import { formatImageSrc, getBannerTheme } from "../utils/imageHelper";

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

export default function PromoBannerCarousel({
  banners = [],
  onAddToCart = null,
  previewBanner = null,
  isPreview = false,
}) {
  const displayBanners = previewBanner
    ? [previewBanner]
    : banners;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(!isPreview);
  const [progress, setProgress] = useState(0);
  const [selectedBannerForModal, setSelectedBannerForModal] = useState(null);
  const [quantity, setQuantity] = useState(1);

  const intervalRef = useRef(null);
  const progressIntervalRef = useRef(null);
  const AUTOPLAY_DURATION = 5000;
  const PROGRESS_TICK = 50;

  useEffect(() => {
    if (currentIndex >= displayBanners.length) {
      setCurrentIndex(0);
    }
  }, [displayBanners.length]);

  useEffect(() => {
    if (isPreview || displayBanners.length <= 1 || !isPlaying || selectedBannerForModal) {
      setProgress(0);
      return;
    }

    let currentProgress = 0;
    setProgress(0);

    progressIntervalRef.current = setInterval(() => {
      currentProgress += (PROGRESS_TICK / AUTOPLAY_DURATION) * 100;
      if (currentProgress >= 100) currentProgress = 100;
      setProgress(currentProgress);
    }, PROGRESS_TICK);

    intervalRef.current = setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % displayBanners.length);
    }, AUTOPLAY_DURATION);

    return () => {
      clearTimeout(intervalRef.current);
      clearInterval(progressIntervalRef.current);
    };
  }, [currentIndex, isPlaying, displayBanners.length, isPreview, selectedBannerForModal]);

  if (!displayBanners.length) return null;

  const currentBanner = displayBanners[currentIndex] || displayBanners[0];

  const handlePrev = (e) => {
    e?.stopPropagation();
    setCurrentIndex((prev) => (prev === 0 ? displayBanners.length - 1 : prev - 1));
  };

  const handleNext = (e) => {
    e?.stopPropagation();
    setCurrentIndex((prev) => (prev + 1) % displayBanners.length);
  };

  const handleDotClick = (index, e) => {
    e?.stopPropagation();
    setCurrentIndex(index);
    setProgress(0);
  };

  const togglePlayPause = (e) => {
    e?.stopPropagation();
    setIsPlaying((prev) => !prev);
  };

  const handleBannerAction = () => {
    if (isPreview) return;
    if (currentBanner.producto || currentBanner.producto_id) {
      setQuantity(1);
      setSelectedBannerForModal(currentBanner);
    }
  };

  const handleCloseModal = () => {
    setSelectedBannerForModal(null);
    setQuantity(1);
  };

  const handleConfirmAddToCart = () => {
    if (!selectedBannerForModal) return;
    const prod = selectedBannerForModal.producto;
    if (prod && onAddToCart) {
      onAddToCart(prod, quantity);
    }
    handleCloseModal();
  };

  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    setImgError(false);
  }, [currentIndex, currentBanner?.id]);

  const bannerBg = currentBanner.color_fondo || "#082620";
  const theme = getBannerTheme(bannerBg);
  const rawProductImg = currentBanner.producto?.imagen_url;
  const productImg = formatImageSrc(rawProductImg);
  
  const modalProduct = selectedBannerForModal?.producto;
  const modalUnitPrice =
    modalProduct?.precio_cliente != null
      ? Number(modalProduct.precio_cliente)
      : modalProduct?.precio != null
      ? Number(modalProduct.precio)
      : null;

  const topTag = (currentBanner.etiqueta_1 || "").trim();
  const redBadge = (currentBanner.etiqueta_roja || "PROMOCIÓN").trim();

  return (
    <>
      <div
        className={`promo-banner-wrapper ${isPreview ? "is-preview" : ""}`}
        style={{
          background: `linear-gradient(135deg, ${theme.bgStart || bannerBg} 0%, ${theme.bgEnd || "rgba(15, 23, 42, 0.95)"} 100%)`,
        }}
      >
        <div
          className="promo-banner-glow"
          style={{
            background: `radial-gradient(circle at 25% 25%, ${theme.glowColor || "rgba(255, 255, 255, 0.15)"} 0%, transparent 65%)`,
          }}
        />

        <div className="promo-banner-content">
          <div className="promo-banner-left">
            {topTag && (
              <div className="promo-pill-container">
                <span
                  className="promo-pill-badge"
                  style={{
                    background: theme.tagBg,
                    borderColor: theme.tagBorder,
                    color: theme.tagColor,
                  }}
                >
                  {topTag}
                </span>
              </div>
            )}

            <h2 className="promo-banner-title">{currentBanner.titulo}</h2>

            {currentBanner.subtitulo && (
              <p
                className="promo-banner-subtitle"
                style={{ color: theme.subtitleColor || "rgba(255, 255, 255, 0.85)" }}
              >
                {currentBanner.subtitulo}
              </p>
            )}

            <div className="promo-banner-cta-group">
              <button
                type="button"
                className="promo-banner-btn"
                onClick={handleBannerAction}
                style={{
                  background: theme.btnBackground,
                  boxShadow: theme.btnShadow,
                }}
              >
                <span>{currentBanner.texto_boton || "Aprovechar Beneficio →"}</span>
              </button>
            </div>
          </div>

          <div className="promo-banner-right" onClick={handleBannerAction}>
            <div className="promo-card">
              <div className="promo-badge-red">
                {redBadge}
              </div>

              <div className="promo-card-image-wrap">
                {productImg && !imgError ? (
                  <img
                    src={productImg}
                    alt={currentBanner.producto?.nombre || currentBanner.titulo}
                    className="promo-card-img"
                    onError={() => setImgError(true)}
                  />
                ) : (
                  <div className="promo-card-placeholder">
                    <Package size={50} className="text-secondary opacity-75" />
                    <span>{currentBanner.producto?.nombre || "Distribuidora Tridente"}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {displayBanners.length > 1 && !isPreview && (
          <div
            className="promo-control-bar"
            style={{
              borderColor: theme.tagBorder || "rgba(255, 255, 255, 0.18)",
              boxShadow: `0 4px 16px rgba(0, 0, 0, 0.4), 0 0 12px ${theme.glowColor || "transparent"}`,
            }}
          >
            <button
              type="button"
              className="promo-nav-btn"
              onClick={handlePrev}
              aria-label="Banner anterior"
              style={{
                "--btn-hover-bg": theme.tagBg || "rgba(255, 255, 255, 0.25)",
                "--btn-hover-border": theme.tagBorder || "rgba(255, 255, 255, 0.35)",
              }}
            >
              <ChevronLeft size={18} />
            </button>

            {/* Botón Pausa / Reproducir */}
            <button
              type="button"
              className="promo-play-btn"
              onClick={togglePlayPause}
              aria-label={isPlaying ? "Pausar carrusel" : "Reproducir carrusel"}
              style={{
                "--btn-hover-bg": theme.tagBg || "rgba(255, 255, 255, 0.25)",
                "--btn-hover-border": theme.tagBorder || "rgba(255, 255, 255, 0.35)",
              }}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            </button>

            {/* Indicadores de Slide y Barra de Progreso */}
            <div className="promo-indicators">
              {displayBanners.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  className={`promo-indicator-dot ${
                    idx === currentIndex ? "active" : ""
                  }`}
                  onClick={(e) => handleDotClick(idx, e)}
                  style={
                    idx === currentIndex
                      ? {
                          background: theme.btnBackground || theme.tagColor || "#10b981",
                          boxShadow: `0 0 8px ${theme.glowColor || "rgba(255, 255, 255, 0.4)"}`,
                        }
                      : {}
                  }
                  aria-label={`Ir al banner ${idx + 1}`}
                />
              ))}
              <span className="promo-slide-counter">
                {currentIndex + 1} / {displayBanners.length}
              </span>
            </div>

            {/* Flecha Siguiente */}
            <button
              type="button"
              className="promo-nav-btn"
              onClick={handleNext}
              aria-label="Banner siguiente"
              style={{
                "--btn-hover-bg": theme.tagBg || "rgba(255, 255, 255, 0.25)",
                "--btn-hover-border": theme.tagBorder || "rgba(255, 255, 255, 0.35)",
              }}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        )}

        {/* Barra de progreso continua animada en el borde inferior */}
        {displayBanners.length > 1 && !isPreview && isPlaying && (
          <div className="promo-progress-track">
            <div
              className="promo-progress-fill"
              style={{
                width: `${progress}%`,
                background: theme.btnBackground || `linear-gradient(90deg, ${theme.tagColor || '#10b981'}, ${theme.subtitleColor || '#34d399'})`,
                boxShadow: `0 0 10px ${theme.glowColor || "transparent"}`,
              }}
            />
          </div>
        )}
      </div>

      {/* MODAL STEPPER: ¿Cuántas unidades deseas agregar al pedido? */}
      {selectedBannerForModal && (
        <div
          className="modal-backdrop-custom promo-modal-backdrop"
          onClick={handleCloseModal}
          role="presentation"
        >
          <div
            className="category-modal promo-stepper-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <header>
              <div>
                <p className="eyebrow">COMPRA RÁPIDA</p>
                <h2>¿Cuántas unidades deseas agregar?</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={handleCloseModal}
                aria-label="Cerrar modal"
              >
                <X size={20} />
              </button>
            </header>

            <div className="modal-body-custom">
              <div className="promo-modal-product-card">
                {formatImageSrc(selectedBannerForModal.producto?.imagen_url) ? (
                  <img
                    src={formatImageSrc(selectedBannerForModal.producto.imagen_url)}
                    alt={selectedBannerForModal.producto.nombre}
                    className="promo-modal-prod-img"
                  />
                ) : (
                  <div className="promo-modal-prod-fallback">
                    <Package size={32} />
                  </div>
                )}
                <div className="promo-modal-prod-info">
                  <strong>
                    {selectedBannerForModal.producto?.nombre ||
                      selectedBannerForModal.titulo}
                  </strong>
                  <span className="promo-modal-prod-code">
                    Cód: {selectedBannerForModal.producto?.codigo || "PROMO"}
                  </span>
                  {modalUnitPrice != null && (
                    <span className="promo-modal-prod-price">
                      Precio Unitario: <strong>{money.format(modalUnitPrice)}</strong>
                    </span>
                  )}
                </div>
              </div>

              {/* Selector de cantidad Stepper */}
              <div className="promo-stepper-group">
                <label className="form-label">Cantidad a solicitar</label>
                <div className="promo-stepper-controls">
                  <button
                    type="button"
                    className="btn btn-outline-secondary promo-stepper-btn"
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    disabled={quantity <= 1}
                  >
                    <Minus size={18} />
                  </button>
                  <input
                    type="number"
                    min="1"
                    className="form-control text-center promo-stepper-input"
                    value={quantity}
                    onChange={(e) =>
                      setQuantity(Math.max(1, parseInt(e.target.value) || 1))
                    }
                  />
                  <button
                    type="button"
                    className="btn btn-outline-secondary promo-stepper-btn"
                    onClick={() => setQuantity((q) => q + 1)}
                  >
                    <Plus size={18} />
                  </button>
                </div>
              </div>

              {/* Cálculo en vivo de subtotal */}
              {modalUnitPrice != null && (
                <div className="promo-modal-subtotal-box">
                  <span>Subtotal estimado:</span>
                  <strong>{money.format(modalUnitPrice * quantity)}</strong>
                </div>
              )}
            </div>

            <footer>
              <button
                type="button"
                className="btn btn-light"
                onClick={handleCloseModal}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-primary d-flex align-items-center gap-2"
                onClick={handleConfirmAddToCart}
              >
                <ShoppingBag size={18} />
                Agregar a la canasta ({quantity})
              </button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}
