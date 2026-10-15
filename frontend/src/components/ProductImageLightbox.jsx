import React, { useEffect, useCallback } from "react";
import { X, Package, Tag, Hash } from "lucide-react";

export function getFullProductImage(imageBase64) {
  if (!imageBase64) return null;
  return imageBase64.startsWith("http")
    ? imageBase64
    : `data:image/jpeg;base64,${imageBase64}`;
}

export default function ProductImageLightbox({ product, onClose }) {
  if (!product) return null;

  const imageUrl = getFullProductImage(product.imagen_url);

  // Manejar tecla Escape para cerrar
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    // Bloquear scroll de fondo para mejor experiencia móvil/desktop
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [handleKeyDown]);

  return (
    <div
      className="lightbox-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Imagen ampliada de ${product.nombre}`}
    >
      {/* Botón flotante de cierre rápido */}
      <button
        type="button"
        className="lightbox-close-btn"
        onClick={onClose}
        aria-label="Cerrar imagen ampliada"
        title="Cerrar (Esc)"
      >
        <X size={24} />
      </button>

      {/* Contenedor central (detiene propagación para no cerrar al pinchar la imagen) */}
      <div
        className="lightbox-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="lightbox-image-wrapper">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={product.nombre}
              className="lightbox-image"
            />
          ) : (
            <div className="lightbox-fallback">
              <Package size={64} className="text-secondary opacity-50 mb-2" />
              <p className="text-muted small m-0">Sin imagen disponible</p>
            </div>
          )}
        </div>

        {/* Pie con información contextual del producto */}
        <div className="lightbox-caption">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-1">
            <h3 className="lightbox-title mb-0">{product.nombre}</h3>
            {product.codigo && (
              <span className="badge bg-light text-secondary border d-flex align-items-center gap-1">
                <Hash size={12} />
                {product.codigo}
              </span>
            )}
          </div>

          {product.categoria?.nombre && (
            <span className="badge bg-primary-subtle text-primary mt-1 d-inline-flex align-items-center gap-1">
              <Tag size={12} />
              {product.categoria.nombre}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
