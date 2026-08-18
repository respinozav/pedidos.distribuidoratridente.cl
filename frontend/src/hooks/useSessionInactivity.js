import { useEffect, useRef } from "react";
import Swal from "sweetalert2";
import { api } from "../services/api";

function getTokenDurationSeconds() {
  try {
    const authHeader = api.defaults.headers.common.Authorization;
    if (authHeader && authHeader.startsWith("Bearer ")) {
      const token = authHeader.replace("Bearer ", "");
      const base64Url = token.split(".")[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const payload = JSON.parse(window.atob(base64));
      if (payload.exp && payload.iat) {
        const durationSec = payload.exp - payload.iat;
        if (durationSec > 0) return durationSec;
      }
    }
  } catch {
    // Fallback if parsing fails
  }
  return 60 * 60; // 60 minutos por defecto (3600 segundos)
}

export function useSessionInactivity({ active, onLogout }) {
  const lastActivityRef = useRef(Date.now());
  const modalOpenRef = useRef(false);

  useEffect(() => {
    if (!active) {
      if (modalOpenRef.current) {
        Swal.close();
        modalOpenRef.current = false;
      }
      return;
    }

    lastActivityRef.current = Date.now();
    modalOpenRef.current = false;

    const handleUserActivity = () => {
      // Si el modal de advertencia no está abierto, actualizamos el timestamp de actividad
      if (!modalOpenRef.current) {
        lastActivityRef.current = Date.now();
      }
    };

    const activityEvents = [
      "mousedown",
      "mousemove",
      "keydown",
      "scroll",
      "touchstart",
      "click",
    ];

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleUserActivity, { passive: true });
    });

    const intervalId = setInterval(() => {
      if (modalOpenRef.current) return;

      const totalDurationSec = getTokenDurationSeconds();
      // Al minuto 59 (o a falta de 59 segundos para expirar):
      const warningCountdownSec = totalDurationSec > 60 ? 59 : Math.max(10, Math.floor(totalDurationSec / 2));
      const warningTriggerSec = totalDurationSec - warningCountdownSec;

      const idleSec = (Date.now() - lastActivityRef.current) / 1000;

      if (idleSec >= warningTriggerSec) {
        modalOpenRef.current = true;
        const initialSecondsLeft = Math.max(1, Math.ceil(totalDurationSec - idleSec));

        let timerInterval;
        Swal.fire({
          title: "¡Tu sesión está por expirar!",
          html: `No hemos detectado actividad en el sistema.<br/>Por seguridad, la sesión se cerrará en <b id="session-countdown-seconds" style="color: #dc3545; font-size: 1.25em;">${initialSecondsLeft}</b> segundos si no hay movimiento.`,
          icon: "warning",
          showCancelButton: true,
          confirmButtonText: "Mantener sesión activa",
          cancelButtonText: "Cerrar sesión",
          confirmButtonColor: "#0d6efd",
          cancelButtonColor: "#6c757d",
          allowOutsideClick: false,
          allowEscapeKey: false,
          timer: initialSecondsLeft * 1000,
          timerProgressBar: true,
          didOpen: () => {
            const b = document.getElementById("session-countdown-seconds");
            timerInterval = setInterval(() => {
              const leftMs = Swal.getTimerLeft();
              if (leftMs !== null && leftMs !== undefined) {
                const leftSec = Math.ceil(leftMs / 1000);
                if (b) b.textContent = `${leftSec}`;
              }
            }, 500);
          },
          willClose: () => {
            clearInterval(timerInterval);
          },
        }).then((result) => {
          modalOpenRef.current = false;
          if (result.isConfirmed) {
            // Usuario decide mantener su sesión activa
            lastActivityRef.current = Date.now();
          } else if (
            result.dismiss === Swal.DismissReason.timer ||
            result.dismiss === Swal.DismissReason.cancel
          ) {
            // Terminó el temporizador o el usuario eligió cerrar sesión
            if (onLogout) onLogout();
            Swal.fire({
              title: "Sesión finalizada",
              text: "Tu sesión ha expirado por inactividad.",
              icon: "info",
              confirmButtonText: "Aceptar",
              confirmButtonColor: "#0d6efd",
            });
          }
        });
      }
    }, 1000);

    return () => {
      clearInterval(intervalId);
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleUserActivity);
      });
      if (modalOpenRef.current) {
        Swal.close();
        modalOpenRef.current = false;
      }
    };
  }, [active, onLogout]);
}
