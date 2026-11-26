import React, { useEffect, useState } from "react";
import "./LoadingScreen.css";
import { useLoading } from "../services/loadingService";

export default function LoadingScreen({ show: manualShow, text: manualText }) {
  const { isLoading: globalLoading, loadingText: globalText } = useLoading();
  const isVisible = manualShow !== undefined ? manualShow : globalLoading;
  const rawText = manualText || globalText || "Cargando....";

  // Manejo de animación suave de salida
  const [shouldRender, setShouldRender] = useState(isVisible);
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setShouldRender(true);
      setIsClosing(false);
    } else if (shouldRender) {
      setIsClosing(true);
      const timer = setTimeout(() => {
        setShouldRender(false);
        setIsClosing(false);
      }, 280);
      return () => clearTimeout(timer);
    }
  }, [isVisible, shouldRender]);

  if (!shouldRender) return null;

  // Si el texto incluye puntos suspensivos ("Cargando...."), separamos la raíz para animar los 4 puntos
  const cleanLabel = rawText.replace(/\.+$/, "");

  return (
    <div
      className={`tridente-loading-backdrop ${isClosing ? "is-closing" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={rawText}
    >
      <div className="tridente-loading-stage">
        {/* Caja de la órbita compacta con el logo agrandado y la estrella fugaz */}
        <div className="tridente-loading-orbit-box">
          {/* Medallón central redondo relleno en azul con el logo oficial de Distribuidora Tridente resaltado */}
          <div className="tridente-loading-medallion">
            <img
              src="/logo_tridente_clean.png"
              alt="Distribuidora Tridente"
              className="tridente-loading-logo-img"
            />
          </div>

          {/* SVG de alta definición con la órbita y la estrella fugaz */}
          <svg
            className="tridente-loading-svg"
            viewBox="0 0 200 200"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              {/* Degradado luminoso de la estela de la estrella fugaz */}
              <linearGradient
                id="tridenteCometTailGrad"
                x1="0%"
                y1="100%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor="#0284c7" stopOpacity="0" />
                <stop offset="35%" stopColor="#0284c7" stopOpacity="0.25" />
                <stop offset="70%" stopColor="#38bdf8" stopOpacity="0.85" />
                <stop offset="92%" stopColor="#bae6fd" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#ffffff" stopOpacity="1" />
              </linearGradient>

              {/* Filtro de resplandor para la estrella */}
              <filter id="tridenteStarGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="3.2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>

              {/* Filtro suave para chispas en la estela */}
              <filter id="tridenteSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Pista de órbita circular sutil alrededor del medallón azul */}
            <circle
              cx="100"
              cy="100"
              r="84"
              fill="none"
              stroke="rgba(56, 189, 248, 0.25)"
              strokeWidth="1.5"
              strokeDasharray="4 6"
            />

            {/* Grupo de la estrella fugaz que rota 360 grados */}
            <g className="tridente-shooting-star-group">
              {/* Estela curvada en arco de la estrella fugaz ajustada a r=84 */}
              <path
                d="M 21.1 71.3 A 84 84 0 0 1 100 16"
                fill="none"
                stroke="url(#tridenteCometTailGrad)"
                strokeWidth="3.6"
                strokeLinecap="round"
              />

              {/* Chispas flotantes y polvo estelar en la estela */}
              <circle
                cx="78.26"
                cy="18.86"
                r="2.4"
                fill="#e0f2fe"
                opacity="0.9"
                filter="url(#tridenteSoftGlow)"
              />
              <circle
                cx="51.82"
                cy="31.19"
                r="1.8"
                fill="#7dd3fc"
                opacity="0.75"
              />
              <circle
                cx="27.25"
                cy="58.00"
                r="1.3"
                fill="#38bdf8"
                opacity="0.5"
              />

              {/* Cabeza de la estrella fugaz (en la posición líder 100, 16) */}
              <g className="tridente-star-flare">
                {/* Halo difuso alrededor de la cabeza */}
                <circle
                  cx="100"
                  cy="16"
                  r="9"
                  fill="rgba(56, 189, 248, 0.45)"
                  filter="url(#tridenteStarGlow)"
                />
                {/* Estrella de 4 puntas centelleante (destello de estrella) */}
                <path
                  d="M 100 5 Q 100 16 111 16 Q 100 16 100 27 Q 100 16 89 16 Q 100 16 100 5 Z"
                  fill="#ffffff"
                  filter="url(#tridenteStarGlow)"
                />
                {/* Núcleo blanco brillante */}
                <circle cx="100" cy="16" r="3.6" fill="#ffffff" />
              </g>
            </g>
          </svg>
        </div>

        {/* Texto: 'Cargando....' con 4 puntos animados */}
        <div className="tridente-loading-text-container">
          <h3 className="tridente-loading-label">{cleanLabel}</h3>
          <span className="tridente-loading-dots" aria-hidden="true">
            <span className="tridente-loading-dot">.</span>
            <span className="tridente-loading-dot">.</span>
            <span className="tridente-loading-dot">.</span>
            <span className="tridente-loading-dot">.</span>
          </span>
        </div>
      </div>
    </div>
  );
}
