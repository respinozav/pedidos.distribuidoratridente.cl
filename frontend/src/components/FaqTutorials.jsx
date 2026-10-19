import React, { useState, useMemo } from "react";
import {
  ChevronDown,
  HelpCircle,
  MessageCircle,
  Mic,
  Package,
  Search,
  ShoppingBag,
  Sparkles,
  Truck,
  Video,
  X,
  CheckCircle2,
  DollarSign,
  ExternalLink,
} from "lucide-react";
import "./faqTutorials.css";

const VIDEO_TUTORIAL = {
  id: "como-realizar-un-pedido",
  title: "Cómo realizar un pedido",
  tagline: "Video Tutorial Operativo",
  src: "/videos/gemini_generated_video_df0ab31e.mp4",
  fallbackSrc: "/videos/como-realizar-un-pedido.mp4",
  description:
    "Aprende paso a paso cómo buscar productos en el catálogo, seleccionar cantidades por unidad o por caja cerrada, revisar tu resumen y enviar tu pedido de forma rápida.",
  steps: [
    {
      num: 1,
      title: "Explora o dicta productos",
      desc: "Filtra por categorías o usa el micrófono para dictar el producto.",
    },
    {
      num: 2,
      title: "Elige Unidad o Caja",
      desc: "Selecciona si deseas empaque cerrado con precio por caja o unidades individuales.",
    },
    {
      num: 3,
      title: "Revisa y Envía",
      desc: "Verifica tu dirección de despacho activa y confirma el envío.",
    },
  ],
};

const CATEGORIES = [
  { id: "todas", label: "Todas las preguntas" },
  { id: "pedidos", label: "Pedidos y Carrito", icon: ShoppingBag },
  { id: "voz", label: "Búsqueda por Voz", icon: Mic },
  { id: "empaque", label: "Cajas vs Unidades", icon: Package },
  { id: "despacho", label: "Despachos y Entregas", icon: Truck },
  { id: "pagos", label: "Precios y Facturación", icon: DollarSign },
];

const FAQS = [
  {
    id: "hacer-pedido",
    category: "pedidos",
    question: "¿Cómo realizo un pedido en la plataforma?",
    answer: (
      <div>
        <p>Realizar un pedido es muy sencillo y toma menos de 2 minutos:</p>
        <ol>
          <li>Ingresa al menú <strong>Realizar pedido</strong>.</li>
          <li>Navega por las categorías o escribe/dicta el nombre del producto en el buscador.</li>
          <li>Haz clic en el botón <strong>+ Agregar</strong> del producto deseado.</li>
          <li>Si el producto tiene formato caja, el sistema te preguntará si deseas comprar por <em>Unidad</em> o por <em>Caja cerrada</em>.</li>
          <li>Ingresa la cantidad requerida y agrégalo al pedido.</li>
          <li>En la barra lateral derecha verás tu resumen. Selecciona tu dirección de despacho y presiona <strong>Enviar pedido</strong>.</li>
        </ol>
      </div>
    ),
  },
  {
    id: "dictado-voz",
    category: "voz",
    question: "¿Cómo funciona el dictado por voz para buscar productos?",
    answer: (
      <div>
        <p>
          En la barra de búsqueda de productos verás un icono de micrófono 🎙️. Al presionarlo:
        </p>
        <ul>
          <li>El botón comenzará a emitir un pulso animado en color rojo.</li>
          <li>El campo indicará <em>"🎙️ Escuchando... di el nombre del producto"</em>.</li>
          <li>Habla con claridad (por ejemplo: <em>"alfajor bon o bon"</em> o <em>"jugo"</em>).</li>
          <li>La aplicación transcribirá tu voz y filtrará automáticamente el listado en tiempo real sin que tengas que teclear.</li>
        </ul>
        <div className="faq-answer-tip">
          💡 <strong>Tip:</strong> Requiere que permitas el acceso al micrófono en tu navegador (Google Chrome, Microsoft Edge o Safari).
        </div>
      </div>
    ),
  },
  {
    id: "caja-vs-unidad",
    category: "empaque",
    question: "¿Cuál es la diferencia entre pedir por Caja o por Unidad?",
    answer: (
      <div>
        <p>
          Muchos de nuestros productos cuentan con precios y empaques mayoristas:
        </p>
        <ul>
          <li><strong>Por Unidad:</strong> Puedes pedir las unidades sueltas que necesites para reponer tu negocio con menor inversión inicial.</li>
          <li><strong>Por Caja / Display:</strong> Viene en su formato original de fábrica (ej. Caja x20 o x40 unidades) y te permite acceder a un precio mayorista más conveniente por unidad.</li>
        </ul>
        <p>
          Al presionar <em>Agregar</em> en un producto con caja disponible, podrás comparar ambos precios antes de confirmar.
        </p>
      </div>
    ),
  },
  {
    id: "sin-stock",
    category: "pedidos",
    question: "¿Qué puedo hacer si un producto no tiene stock disponible?",
    answer: (
      <div>
        <p>
          Si un producto se encuentra agotado, verás una etiqueta de <strong>Sin stock</strong> y un botón con campana 🔔 <strong>Avisarme</strong>.
        </p>
        <p>
          Al hacer clic podrás ingresar tu correo electrónico. Apenas recibamos reposición en bodega con stock disponible, el sistema te enviará una notificación automática para que puedas agregarlo a tu pedido.
        </p>
      </div>
    ),
  },
  {
    id: "historial-pedidos",
    category: "despacho",
    question: "¿Dónde puedo revisar el historial y estado de mis pedidos?",
    answer: (
      <div>
        <p>
          En el menú lateral haz clic en <strong>Pedidos históricos</strong>. Allí podrás:
        </p>
        <ul>
          <li>Ver el listado de todos tus pedidos realizados con fecha, total y código.</li>
          <li>Consultar el estado de cada pedido: <em>Pedido</em>, <em>Despachado</em>, <em>Entregado</em> o <em>Cancelado</em>.</li>
          <li>Hacer clic en <strong>Ver detalle</strong> para revisar la lista de productos, precios y comprobante de despacho.</li>
        </ul>
      </div>
    ),
  },
  {
    id: "cambiar-direccion",
    category: "despacho",
    question: "¿Cómo selecciono o cambio mi dirección de entrega?",
    answer: (
      <div>
        <p>
          Al momento de confirmar tu pedido en la columna derecha de tu carrito, encontrarás un selector desplegable con tus <strong>direcciones de despacho registradas</strong>.
        </p>
        <p>
          Si necesitas añadir o modificar una dirección comercial o de local, puedes hacerlo desde <strong>Mis datos</strong> o coordinarlo con tu vendedor asignado.
        </p>
      </div>
    ),
  },
  {
    id: "precios-impuestos",
    category: "pagos",
    question: "¿Los precios que veo en la plataforma incluyen IVA?",
    answer: (
      <div>
        <p>
          Todos los precios de los productos y los totales generados en los pedidos están calculados con los impuestos correspondientes para facilitar tu cuadratura y facturación directa.
        </p>
      </div>
    ),
  },
  {
    id: "soporte-vendedor",
    category: "pagos",
    question: "¿Cómo puedo contactar a mi vendedor asignado o resolver un problema?",
    answer: (
      <div>
        <p>
          Si tienes una duda especial sobre crédito, condiciones comerciales o productos que no encuentras en el catálogo:
        </p>
        <ul>
          <li>Usa el banner <strong>Focus Group</strong> en la parte superior para sugerir nuevos productos.</li>
          <li>Escríbenos directamente a través del botón de <strong>WhatsApp de Distribuidora Tridente</strong> para atención inmediata con nuestro equipo.</li>
        </ul>
      </div>
    ),
  },
];

export default function FaqTutorials({ onGoToShop, isAdminOrVendor = false }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("todas");
  const [openFaqId, setOpenFaqId] = useState("hacer-pedido");

  // Filtrar FAQs según búsqueda y categoría
  const filteredFaqs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return FAQS.filter((faq) => {
      const matchCat =
        selectedCategory === "todas" || faq.category === selectedCategory;
      if (!matchCat) return false;
      if (!q) return true;
      const questionMatch = faq.question.toLowerCase().includes(q);
      return questionMatch;
    });
  }, [searchQuery, selectedCategory]);

  const toggleFaq = (id) => {
    setOpenFaqId((current) => (current === id ? null : id));
  };

  return (
    <div className="faq-container">
      {/* Header Principal con Buscador */}
      <header className="faq-header">
        <div className="faq-header-badge">
          <Sparkles size={14} />
          Centro de Ayuda y Tutoriales
        </div>
        <h1>¿Cómo podemos ayudarte hoy?</h1>
        <p>
          Encuentra videos explicativos sobre cómo opera la aplicación, guías
          paso a paso y respuestas a las preguntas más frecuentes de
          Distribuidora Tridente.
        </p>

        <div className="faq-search-box">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="faq-search-input"
            placeholder="Escribe tu duda o busca un tema (ej. cómo pedir, voz, cajas, despacho)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="faq-search-clear"
              onClick={() => setSearchQuery("")}
              title="Borrar búsqueda"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </header>

      {/* SECCIÓN VIDEO DESTACADO OPERATIVO */}
      <section className="faq-video-section">
        <div className="faq-video-section-header">
          <div className="faq-video-title-wrap">
            <div className="faq-video-icon">
              <Video size={22} />
            </div>
            <div>
              <span className="badge bg-primary bg-opacity-10 text-primary fw-semibold px-2 py-1 mb-1">
                {VIDEO_TUTORIAL.tagline}
              </span>
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
        <div className="video-player-wrapper">
          <video
            key={VIDEO_TUTORIAL.id}
            className="video-element"
            controls
            playsInline
            preload="metadata"
          >
            <source src={VIDEO_TUTORIAL.src} type="video/mp4" />
            {VIDEO_TUTORIAL.fallbackSrc && (
              <source src={VIDEO_TUTORIAL.fallbackSrc} type="video/mp4" />
            )}
            Tu navegador no soporta reproducción de video HTML5.
          </video>
        </div>

        {/* Pasos clave si están definidos para este video */}
        {VIDEO_TUTORIAL.steps && (
          <div className="video-steps-grid">
            {VIDEO_TUTORIAL.steps.map((st) => (
              <div key={st.num} className="video-step-card">
                <div className="video-step-number">{st.num}</div>
                <div className="video-step-text">
                  <strong>{st.title}</strong>
                  <span>{st.desc}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECCIÓN PREGUNTAS FRECUENTES (FAQ) */}
      <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
        <div>
          <h3 className="mb-1 fw-bold text-dark d-flex align-items-center gap-2">
            <HelpCircle size={22} className="text-primary" />
            Preguntas Frecuentes
          </h3>
          <p className="text-muted small mb-0">
            Encuentra soluciones inmediatas a las dudas operativas más comunes.
          </p>
        </div>
      </div>

      {/* Tabs de Categorías */}
      <div className="faq-categories-tabs">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              className={`faq-tab-btn ${isActive ? "active" : ""}`}
              onClick={() => setSelectedCategory(cat.id)}
            >
              {Icon && <Icon size={15} />}
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Acordeón de FAQs */}
      <div className="faq-accordion">
        {filteredFaqs.length > 0 ? (
          filteredFaqs.map((faq) => {
            const isOpen = openFaqId === faq.id;
            return (
              <div
                key={faq.id}
                className={`faq-item ${isOpen ? "is-open" : ""}`}
              >
                <button
                  type="button"
                  className="faq-question-btn"
                  onClick={() => toggleFaq(faq.id)}
                  aria-expanded={isOpen}
                >
                  <div className="faq-question-title">
                    <CheckCircle2 size={18} className="faq-question-icon" />
                    <span>{faq.question}</span>
                  </div>
                  <ChevronDown size={18} className="faq-chevron" />
                </button>
                {isOpen && (
                  <div className="faq-answer-panel">{faq.answer}</div>
                )}
              </div>
            );
          })
        ) : (
          <div className="text-center py-5 bg-white rounded-3 border">
            <HelpCircle size={36} className="text-muted mb-2" />
            <h5 className="fw-bold text-dark">No encontramos resultados</h5>
            <p className="text-muted small mb-3">
              No hay preguntas que coincidan con tu búsqueda "{searchQuery}".
            </p>
            <button
              type="button"
              className="btn btn-outline-primary btn-sm"
              onClick={() => {
                setSearchQuery("");
                setSelectedCategory("todas");
              }}
            >
              Ver todas las preguntas
            </button>
          </div>
        )}
      </div>

      {/* Banner de Contacto / Soporte WhatsApp */}
      <div className="faq-support-banner">
        <div className="faq-support-info">
          <div className="faq-support-icon">
            <MessageCircle size={26} />
          </div>
          <div className="faq-support-text">
            <h3>¿Aún tienes dudas o necesitas asistencia personalizada?</h3>
            <p>
              Nuestro equipo de ventas y atención al cliente está disponible
              para asistirte vía WhatsApp o teléfono.
            </p>
          </div>
        </div>

        <a
          href="https://wa.me/56966607248?text=Hola%2C%20tengo%20una%20consulta%20sobre%20la%20plataforma%20de%20pedidos"
          target="_blank"
          rel="noopener noreferrer"
          className="faq-whatsapp-btn"
        >
          <MessageCircle size={18} />
          Chatear por WhatsApp
          <ExternalLink size={14} />
        </a>
      </div>
    </div>
  );
}
