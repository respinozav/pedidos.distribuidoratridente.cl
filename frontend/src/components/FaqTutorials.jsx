import React from "react";
import { Video, ShoppingBag } from "lucide-react";
import "./faqTutorials.css";

const VIDEO_TUTORIAL = {
  id: "como-realizar-un-pedido",
  title: "Cómo realizar un pedido",
  src: "/videos/tutorial_portal_pedidos_v8.mp4",
  description:
    "Aprende paso a paso cómo buscar productos en el catálogo, seleccionar cantidades por unidad o por caja cerrada, revisar tu resumen y enviar tu pedido.",
};

export default function FaqTutorials({ onGoToShop }) {
  return (
    <div className="faq-container video-only-container">
      <div className="faq-video-section video-only-card">
        <div className="faq-video-section-header">
          <div className="faq-video-title-wrap">
            <div className="faq-video-icon">
              <Video size={24} />
            </div>
            <div>
              <h2>{VIDEO_TUTORIAL.title}</h2>
              <p>{VIDEO_TUTORIAL.description}</p>
            </div>
          </div>

          {onGoToShop && (
            <button
              type="button"
              className="btn btn-primary d-inline-flex align-items-center gap-2 fw-semibold"
              onClick={onGoToShop}
            >
              <ShoppingBag size={17} />
              Ir al Catálogo a Comprar
            </button>
          )}
        </div>

        {/* Reproductor de Video */}
        <div className="video-player-wrapper video-only-player">
          <video
            key={VIDEO_TUTORIAL.id}
            className="video-element"
            controls
            playsInline
            preload="metadata"
          >
            <source src={VIDEO_TUTORIAL.src} type="video/mp4" />
            Tu navegador no soporta reproducción de video HTML5.
          </video>
        </div>
      </div>
    </div>
  );
}
