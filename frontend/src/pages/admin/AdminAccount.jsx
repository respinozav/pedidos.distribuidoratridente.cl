import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, Save, KeyRound, UserCheck } from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import StockAlertBell from "../../components/admin/StockAlertBell";

export default function AdminAccount({ onProfileUpdated }) {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ nombre: "", celular: "" });
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "" });
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function loadProfile() {
    try {
      setLoading(true);
      const { data } = await api.get("/admin/perfil");
      setProfile(data);
      setForm({
        nombre: data.nombre || "",
        celular: data.celular || "",
      });
      if (onProfileUpdated) {
        onProfileUpdated(data);
      }
    } catch (err) {
      setError("No fue posible cargar la información de tu perfil.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, []);

  async function handleSaveProfile(e) {
    e.preventDefault();
    setError("");
    setNotice("");
    try {
      setSavingProfile(true);
      const { data } = await api.put("/admin/perfil", {
        nombre: form.nombre.trim(),
        celular: form.celular ? form.celular.trim() : null,
      });
      setProfile(data);
      if (onProfileUpdated) {
        onProfileUpdated(data);
      }
      setNotice("Tus datos personales fueron actualizados correctamente.");
      Swal.fire({
        icon: "success",
        title: "Datos actualizados",
        text: "Tus datos personales fueron guardados con éxito.",
        timer: 2000,
        showConfirmButton: false,
      });
    } catch (err) {
      const msg = err.response?.data?.detail || "No fue posible actualizar tus datos.";
      setError(msg);
      Swal.fire({
        icon: "error",
        title: "Error al guardar",
        text: msg,
      });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setError("");
    setNotice("");
    if (!passwordForm.new_password || passwordForm.new_password.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    try {
      setSavingPassword(true);
      await api.put("/admin/perfil/clave", {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setPasswordForm({ current_password: "", new_password: "" });
      setNotice("Contraseña actualizada exitosamente.");
      Swal.fire({
        icon: "success",
        title: "Contraseña actualizada",
        text: "Tu contraseña ha sido cambiada correctamente.",
        timer: 2500,
        showConfirmButton: false,
      });
    } catch (err) {
      const msg = err.response?.data?.detail || "No fue posible cambiar la contraseña.";
      setError(msg);
      Swal.fire({
        icon: "error",
        title: "Error de contraseña",
        text: msg,
      });
    } finally {
      setSavingPassword(false);
    }
  }

  if (loading) {
    return (
      <div className="p-4 text-secondary">
        <p>Cargando información del perfil...</p>
      </div>
    );
  }

  return (
    <div className="admin-account-container">
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CUENTA</p>
          <h1>Mis datos</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Mi perfil</span>
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content">
        <section className="admin-summary">
          <div>
            <p className="eyebrow">CUENTA</p>
            <h2>Administra tus datos personales</h2>
            <p>Gestiona tu información de contacto, credenciales y seguridad de tu cuenta de administrador.</p>
          </div>
          <div className="summary-metric">
            <span>1</span>
            <small>Sesión de administrador</small>
          </div>
        </section>

        {notice && (
          <div className="alert alert-success alert-dismissible fade show d-flex align-items-center gap-2 mb-4" role="alert">
            <CheckCircle2 size={18} />
            <span>{notice}</span>
            <button type="button" className="btn-close ms-auto" aria-label="Cerrar" onClick={() => setNotice("")} />
          </div>
        )}

        {error && (
          <div className="alert alert-danger alert-dismissible fade show d-flex align-items-center gap-2 mb-4" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
            <button type="button" className="btn-close ms-auto" aria-label="Cerrar" onClick={() => setError("")} />
          </div>
        )}

        <div className="row g-4 align-items-stretch">
          <div className="col-lg-6 col-12 d-flex flex-column">
            <form className="content-panel h-100 d-flex flex-column" onSubmit={handleSaveProfile}>
              <div className="panel-heading mb-3">
                <div>
                  <h2>Datos personales</h2>
                  <p>El rol y correo no se pueden modificar.</p>
                </div>
              </div>

              <div className="row g-3">
                <div className="col-sm-6 col-12">
                  <label className="form-label">Rol</label>
                  <input
                    className="form-control"
                    value={profile?.rol?.nombre || "Administrador"}
                    disabled
                  />
                </div>

                <div className="col-sm-6 col-12">
                  <label className="form-label">Correo electrónico</label>
                  <input
                    className="form-control"
                    value={profile?.correo ?? ""}
                    disabled
                  />
                </div>

                <div className="col-sm-6 col-12">
                  <label className="form-label">Nombre</label>
                  <input
                    className="form-control"
                    value={form.nombre}
                    onChange={(event) => setForm({ ...form, nombre: event.target.value })}
                    required
                  />
                </div>

                <div className="col-sm-6 col-12">
                  <label className="form-label">Celular</label>
                  <input
                    className="form-control"
                    value={form.celular}
                    onChange={(event) => setForm({ ...form, celular: event.target.value })}
                    placeholder="+56 9 1234 5678"
                  />
                </div>
              </div>

              <div className="mt-auto pt-4">
                <button className="btn btn-primary" type="submit" disabled={savingProfile}>
                  {savingProfile ? "Guardando..." : "Guardar datos"}
                </button>
              </div>
            </form>
          </div>

          <div className="col-lg-6 col-12 d-flex flex-column">
            <form className="content-panel h-100 d-flex flex-column" onSubmit={handleChangePassword}>
              <div className="panel-heading mb-3">
                <div>
                  <h2>Cambiar contraseña</h2>
                  <p>Usa al menos 8 caracteres.</p>
                </div>
              </div>

              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label">Contraseña actual</label>
                  <input
                    className="form-control"
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })}
                    required
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Nueva contraseña</label>
                  <input
                    className="form-control"
                    type="password"
                    minLength="8"
                    value={passwordForm.new_password}
                    onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="mt-auto pt-4">
                <button className="btn btn-primary" type="submit" disabled={savingPassword}>
                  {savingPassword ? "Cambiando..." : "Cambiar contraseña"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
