import React, { useEffect, useState } from "react";
import "./LoadingScreen.css";
import { useLoading } from "../services/loadingService";

export default function LoadingScreen({ show: manualShow, text: manualText }) {
  const { isLoading: globalLoading, loadingText: globalText } = useLoading();
  const isVisible = manualShow !== undefined ? manualShow : globalLoading;
  const rawText = manualText || globalText || "Cargando...";

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

  // Si el texto incluye puntos suspensivos ("Cargando..."), separamos la raíz para animar los puntos
  const cleanLabel = rawText.replace(/\.+$/, "");

  return (
    <div
      className={`tridente-loading-backdrop ${isClosing ? "is-closing" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={rawText}
    >
      <div className="tridente-loading-stage">
        {/* Caja de la órbita con el logo central y la estrella fugaz */}
        <div className="tridente-loading-orbit-box">
          {/* Medallón central redondo con el logo oficial de Distribuidora Tridente */}
          <div className="tridente-loading-medallion">
            <img
              src="/logo_tridente.png"
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

            {/* Pista de órbita circular sutil alrededor del logo */}
            <circle
              cx="100"
              cy="100"
              r="82"
              fill="none"
              stroke="rgba(56, 189, 248, 0.22)"
              strokeWidth="1.5"
              strokeDasharray="4 6"
            />

            {/* Grupo de la estrella fugaz que rota 360 grados */}
            <g className="tridente-shooting-star-group">
              {/* Estela curvada en arco de la estrella fugaz */}
              <path
                d="M 22.9 72 A 82 82 0 0 1 100 18"
                fill="none"
                stroke="url(#tridenteCometTailGrad)"
                strokeWidth="3.6"
                strokeLinecap="round"
              />

              {/* Chispas flotantes y polvo estelar en la estela */}
              <circle
                cx="78.78"
                cy="20.79"
                r="2.4"
                fill="#e0f2fe"
                opacity="0.9"
                filter="url(#tridenteSoftGlow)"
              />
              <circle
                cx="52.97"
                cy="32.83"
                r="1.8"
                fill="#7dd3fc"
                opacity="0.75"
              />
              <circle
                cx="28.99"
                cy="59.00"
                r="1.3"
                fill="#38bdf8"
                opacity="0.5"
              />

              {/* Cabeza de la estrella fugaz (en la posición líder 100, 18) */}
              <g className="tridente-star-flare">
                {/* Halo difuso alrededor de la cabeza */}
                <circle
                  cx="100"
                  cy="18"
                  r="9"
                  fill="rgba(56, 189, 248, 0.4)"
                  filter="url(#tridenteStarGlow)"
                />
                {/* Estrella de 4 puntas centelleante (destello de estrella) */}
                <path
                  d="M 100 7 Q 100 18 111 18 Q 100 18 100 29 Q 100 18 89 18 Q 100 18 100 7 Z"
                  fill="#ffffff"
                  filter="url(#tridenteStarGlow)"
                />
                {/* Núcleo blanco brillante */}
                <circle cx="100" cy="18" r="3.6" fill="#ffffff" />
              </g>
            </g>
          </svg>
        </div>

        {/* Texto: 'Cargando...' */}
        <div className="tridente-loading-text-container">
          <h3 className="tridente-loading-label">{cleanLabel}</h3>
          <span className="tridente-loading-dots" aria-hidden="true">
            <span className="tridente-loading-dot">.</span>
            <span className="tridente-loading-dot">.</span>
            <span className="tridente-loading-dot">.</span>
          </span>
        </div>
      </div>
    </div>
  );
}
