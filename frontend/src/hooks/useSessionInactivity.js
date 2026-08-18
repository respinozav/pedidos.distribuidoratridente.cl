import { useEffect, useRef } from "react";
import Swal from "sweetalert2";
import { getActiveToken, setOnAuthExpired } from "../services/api";

function decodeToken(token) {
  if (!token) return null;
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(base64));
  } catch {
    return null;
  }
}

export function useSessionInactivity({ active, onLogout }) {
  const lastActivityRef = useRef(Date.now());
  const modalOpenRef = useRef(false);

  useEffect(() => {
    // Registrar listener para interceptor 401
    setOnAuthExpired(onLogout);
    return () => {
      setOnAuthExpired(null);
    };
  }, [onLogout]);

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
      const token = getActiveToken();
      const payload = decodeToken(token);

      const nowSec = Date.now() / 1000;
      let totalDurationSec = 60 * 60; // 60 minutos por defecto (3600 segundos)
      let tokenExpSec = null;

      if (payload) {
        if (payload.exp && payload.iat) {
          totalDurationSec = Math.max(10, payload.exp - payload.iat);
        }
        if (payload.exp) {
          tokenExpSec = payload.exp;
        }
      }

      // 1. Si el token ya expiró absolutamente por tiempo
      if (tokenExpSec && nowSec >= tokenExpSec) {
        if (modalOpenRef.current) {
          Swal.close();
          modalOpenRef.current = false;
        }
        if (onLogout) onLogout();
        Swal.fire({
          icon: "warning",
          title: "Sesión caducada",
          text: "Tu sesión ha expirado por tiempo límite. Por favor ingresa nuevamente con tus credenciales.",
          confirmButtonText: "Aceptar",
          confirmButtonColor: "#0d6efd",
          allowOutsideClick: false,
        });
        return;
      }

      if (modalOpenRef.current) return;

      // 2. Comprobar inactividad y tiempo restante
      const idleSec = (Date.now() - lastActivityRef.current) / 1000;
      const warningWindowSec = totalDurationSec > 60 ? 59 : Math.max(10, Math.floor(totalDurationSec / 2));
      const idleWarningTriggerSec = totalDurationSec - warningWindowSec;

      const remainingByToken = tokenExpSec ? Math.ceil(tokenExpSec - nowSec) : 999999;
      const remainingByIdle = Math.ceil(totalDurationSec - idleSec);

      const isTokenExpiringSoon = remainingByToken <= warningWindowSec && remainingByToken > 0;
      const isIdleExpiringSoon = idleSec >= idleWarningTriggerSec;

      if (isTokenExpiringSoon || isIdleExpiringSoon) {
        modalOpenRef.current = true;
        const initialSecondsLeft = Math.min(
          warningWindowSec,
          Math.max(1, Math.min(remainingByToken, remainingByIdle))
        );

        let timerInterval;
        Swal.fire({
          title: "¡Tu sesión está por expirar!",
          html: `No hemos detectado actividad en el sistema.<br/>Por seguridad, la sesión se cerrará en <b id="session-countdown-seconds" style="color: #dc3545; font-size: 1.3em;">${initialSecondsLeft}</b> segundos si no hay movimiento.`,
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
            // Usuario mantiene su sesión
            lastActivityRef.current = Date.now();
          } else if (
            result.dismiss === Swal.DismissReason.timer ||
            result.dismiss === Swal.DismissReason.cancel
          ) {
            // Terminó el temporizador o el usuario cerró sesión
            if (onLogout) onLogout();
            Swal.fire({
              icon: "info",
              title: "Sesión cerrada",
              text: "Tu sesión ha expirado por inactividad.",
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
