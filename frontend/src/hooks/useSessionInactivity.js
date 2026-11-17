import { useEffect, useRef } from "react";
import Swal from "sweetalert2";
import { api, getActiveToken, getStoredSession, getStoredTimeOffset, saveSessionStorage, setAdminToken, setOnAuthExpired } from "../services/api";

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

const notificarSesionCaducada = (minutos) => {
  api.post("/auth/sesion-caducada", {
    minutos_inactividad: minutos,
    motivo: "Inactividad",
  }).catch(() => {});
};

export function useSessionInactivity({ active, onLogout }) {
  const lastActivityRef = useRef(Date.now());
  const modalOpenRef = useRef(false);
  const hookMountedAtRef = useRef(Date.now());

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

    const now = Date.now();
    lastActivityRef.current = now;
    try {
      localStorage.setItem("tridente_last_activity", String(now));
    } catch {}
    hookMountedAtRef.current = now;
    modalOpenRef.current = false;

    const handleUserActivity = () => {
      const ts = Date.now();
      lastActivityRef.current = ts;
      try {
        localStorage.setItem("tridente_last_activity", String(ts));
      } catch {}
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
      let totalDurationSec = 60 * 60; // 60 minutos por defecto (3600s)
      let tokenExpSec = null;

      if (payload) {
        if (payload.minutes && payload.minutes > 0) {
          totalDurationSec = payload.minutes * 60;
        } else if (payload.exp && payload.iat && payload.exp > payload.iat) {
          totalDurationSec = payload.exp - payload.iat;
        }
        if (payload.exp) {
          tokenExpSec = payload.exp;
        }
      }

      // Si el modal ya está abierto, dejamos que el modal maneje la cuenta regresiva
      if (modalOpenRef.current) return;

      // Compensar el desfase entre el reloj local del cliente y el servidor
      let offsetSec = getStoredTimeOffset();
      if (!offsetSec && payload?.iat) {
        offsetSec = Math.round(nowSec - payload.iat);
      }
      const nowServerSec = nowSec - offsetSec;

      const tokenSecondsLeft = tokenExpSec ? Math.max(0, Math.ceil(tokenExpSec - nowServerSec)) : null;

      // Calcular tiempo de inactividad sincronizado entre pestañas
      let lastActivity = lastActivityRef.current;
      try {
        const storedAct = localStorage.getItem("tridente_last_activity");
        if (storedAct) {
          lastActivity = Math.max(lastActivity, Number(storedAct));
        }
      } catch {}
      const idleSec = (Date.now() - lastActivity) / 1000;

      // Período de gracia inicial: si el hook lleva menos de 10 segundos activo,
      // no cerrar la sesión intempestivamente por discrepancias transitorias de reloj
      const secondsSinceMount = (Date.now() - hookMountedAtRef.current) / 1000;
      if (secondsSinceMount < 10 && tokenSecondsLeft !== null && tokenSecondsLeft <= 0) {
        return;
      }

      // 1. Si la inactividad superó el total de minutos configurados o el token ya expiró
      if (idleSec >= totalDurationSec || (tokenSecondsLeft !== null && tokenSecondsLeft <= 0)) {
        const mins = Math.max(1, Math.round(totalDurationSec / 60));
        notificarSesionCaducada(mins);
        if (onLogout) onLogout();
        Swal.fire({
          icon: "warning",
          title: "Sesión caducada",
          text: `Tu sesión ha caducado por inactividad tras superar los ${mins} minutos configurados. Por favor ingresa nuevamente con tus credenciales.`,
          confirmButtonText: "Aceptar",
          confirmButtonColor: "#0d6efd",
          allowOutsideClick: false,
        });
        return;
      }

      // 2. Ventana de advertencia: 59 segundos antes de expirar (o la mitad si dura <= 60s)
      const warningWindowSec = totalDurationSec > 60 ? 59 : Math.max(10, Math.floor(totalDurationSec / 2));
      const idleWarningTriggerSec = totalDurationSec - warningWindowSec;

      const isTokenExpiringSoon = tokenSecondsLeft !== null && tokenSecondsLeft <= warningWindowSec && tokenSecondsLeft > 0;
      const isIdleExpiringSoon = idleSec >= idleWarningTriggerSec;

      if (isTokenExpiringSoon || isIdleExpiringSoon) {
        modalOpenRef.current = true;
        const initialSecondsLeft = Math.min(
          warningWindowSec,
          Math.max(1, Math.min(tokenSecondsLeft ?? warningWindowSec, Math.ceil(totalDurationSec - idleSec)))
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
            }, 400);
          },
          willClose: () => {
            clearInterval(timerInterval);
          },
        }).then(async (result) => {
          modalOpenRef.current = false;
          if (result.isConfirmed) {
            // El usuario confirmó que desea mantener la sesión activa: renovar token en backend
            try {
              const { data } = await api.post("/auth/refresh");
              if (data?.access_token) {
                const session = getStoredSession();
                setAdminToken(data.access_token);
                saveSessionStorage(data.access_token, session?.role || "admin", session?.customer);
              }
              const renewedNow = Date.now();
              lastActivityRef.current = renewedNow;
              try {
                localStorage.setItem("tridente_last_activity", String(renewedNow));
              } catch {}
              Swal.fire({
                toast: true,
                position: "top-end",
                icon: "success",
                title: "Sesión renovada con éxito",
                showConfirmButton: false,
                timer: 2000,
              });
            } catch {
              if (onLogout) onLogout();
            }
          } else if (
            result.dismiss === Swal.DismissReason.timer ||
            result.dismiss === Swal.DismissReason.cancel
          ) {
            // El contador llegó a 0 o el usuario pulsó "Cerrar sesión"
            const mins = Math.max(1, Math.round(totalDurationSec / 60));
            notificarSesionCaducada(mins);
            if (onLogout) onLogout();
            Swal.fire({
              icon: "warning",
              title: "Sesión caducada",
              text: `Tu sesión ha caducado por inactividad tras superar los ${mins} minutos configurados.`,
              confirmButtonText: "Aceptar",
              confirmButtonColor: "#0d6efd",
              allowOutsideClick: false,
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
