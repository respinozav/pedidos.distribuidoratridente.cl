import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  Ear,
  MapPin,
  Mic,
  MicOff,
  Minus,
  Package,
  Plus,
  Radio,
  RotateCcw,
  Search,
  Sparkles,
  Trash2,
  User,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
});

// Normalización universal: elimina tildes, diacríticos y pasa a minúsculas
export const normalizarTextoBusqueda = (str) => {
  if (!str) return "";
  return str
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
};

export const limpiarRutParaBusqueda = (rut) => {
  if (!rut) return "";
  return rut.toString().replace(/[^0-9kK]/g, "").toLowerCase();
};

export const limpiarTelefonoParaBusqueda = (tel) => {
  if (!tel) return "";
  return tel.toString().replace(/[^0-9]/g, "");
};

export default function ModalCrearPedidoVoz({ isOpen, onClose, onOrderCreated }) {
  if (!isOpen) return null;

  // Estados de Clientes
  const [customers, setCustomers] = useState([]);
  const [loadingCustomers, setLoadingCustomers] = useState(false);
  const [customerSearch, setCustomerSearch] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerAddresses, setCustomerAddresses] = useState([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [clientCandidates, setClientCandidates] = useState([]);
  const [searchingBackendCustomers, setSearchingBackendCustomers] = useState(false);

  // Estados de Voz y Diálogo Bidireccional
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isHandsFree, setIsHandsFree] = useState(true);
  const [transcript, setTranscript] = useState("");
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [assistantMessage, setAssistantMessage] = useState(
    "Hola, soy tu Asistente Tridente. ¿Para qué cliente deseas armar el pedido?"
  );

  // Máquina de estados conversacional:
  // 'ESPERANDO_CLIENTE' | 'ESPERANDO_PRODUCTOS' | 'ESPERANDO_CANTIDAD' | 'DESAMBIGUAR_PRODUCTO' | 'CONFIRMACION_FINAL'
  const [conversationState, setConversationState] = useState("ESPERANDO_CLIENTE");
  const [pendingProduct, setPendingProduct] = useState(null);
  const [ambiguousItems, setAmbiguousItems] = useState([]);
  const [detectedCategory, setDetectedCategory] = useState(null);
  const [categoryBrands, setCategoryBrands] = useState([]);
  const [categoryProducts, setCategoryProducts] = useState([]);

  // Estados del Borrador del Pedido
  const [cartItems, setCartItems] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState([]);
  const [manualSearch, setManualSearch] = useState("");
  const [manualSearchResults, setManualSearchResults] = useState([]);

  // Referencias para evitar cierres obsoletos en eventos asíncronos de audio
  const synthRef = useRef(typeof window !== "undefined" ? window.speechSynthesis : null);
  const recognitionRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const isListeningRef = useRef(false);
  const isHandsFreeRef = useRef(true);
  const isMutedRef = useRef(false);
  const transcriptRef = useRef("");
  const selectedCustomerRef = useRef(null);
  const cartItemsRef = useRef([]);
  const conversationStateRef = useRef("ESPERANDO_CLIENTE");
  const pendingProductRef = useRef(null);
  const customersRef = useRef([]);
  const activeVoicesRef = useRef([]);

  // Sincronizar referencias con estados reactivos
  useEffect(() => {
    isSpeakingRef.current = isSpeaking;
  }, [isSpeaking]);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    isHandsFreeRef.current = isHandsFree;
  }, [isHandsFree]);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    selectedCustomerRef.current = selectedCustomer;
  }, [selectedCustomer]);

  useEffect(() => {
    cartItemsRef.current = cartItems;
  }, [cartItems]);

  useEffect(() => {
    conversationStateRef.current = conversationState;
  }, [conversationState]);

  useEffect(() => {
    pendingProductRef.current = pendingProduct;
  }, [pendingProduct]);

  useEffect(() => {
    customersRef.current = customers;
  }, [customers]);

  // Montar componentes y arrancar asistente
  useEffect(() => {
    cargarClientes();
    cargarCatalogo();
    inicializarVoces();
    inicializarReconocimientoVoz();

    // Saludo inicial y arranque de ciclo conversacional
    const timerInicio = setTimeout(() => {
      arrancarConversacionInicial();
    }, 450);

    return () => {
      clearTimeout(timerInicio);
      detenerTodoAudio();
    };
  }, []);

  const detenerTodoAudio = () => {
    if (synthRef.current) {
      try {
        synthRef.current.cancel();
      } catch (_) {}
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (_) {}
    }
    setIsSpeaking(false);
    setIsListening(false);
  };

  const inicializarVoces = () => {
    if (!synthRef.current) return;
    const cargarVoces = () => {
      try {
        activeVoicesRef.current = synthRef.current.getVoices() || [];
      } catch (_) {}
    };
    cargarVoces();
    if (synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = cargarVoces;
    }
  };

  const obtenerMejorVozEspanol = () => {
    const voces = activeVoicesRef.current || [];
    if (!voces.length && synthRef.current) {
      activeVoicesRef.current = synthRef.current.getVoices() || [];
    }
    const disponibles = activeVoicesRef.current;
    // Prioridad: es-CL -> es-419 -> es-US -> es-ES -> cualquier español
    const cl = disponibles.find((v) => v.lang === "es-CL" || v.lang.replace("_", "-") === "es-CL");
    if (cl) return cl;
    const latam = disponibles.find((v) => v.lang.includes("419") || v.lang === "es-US");
    if (latam) return latam;
    const es = disponibles.find((v) => v.lang.startsWith("es"));
    if (es) return es;
    return disponibles[0] || null;
  };

  // Función Central de Síntesis de Voz (TTS) con Prevención de Eco Acústico
  const hablarMensaje = (texto, callbackOnEnd) => {
    if (!texto) return;
    setAssistantMessage(texto);

    // Si está silenciado o no hay soporte TTS
    if (isMutedRef.current || !synthRef.current) {
      if (callbackOnEnd && isHandsFreeRef.current) {
        setTimeout(() => {
          callbackOnEnd();
        }, 300);
      }
      return;
    }

    try {
      // REGLA ANTI-ECO: Apagar micrófono mientras el agente habla
      abortarEscucha();

      synthRef.current.cancel();

      const utterance = new SpeechSynthesisUtterance(texto);
      const voz = obtenerMejorVozEspanol();
      if (voz) utterance.voice = voz;
      utterance.lang = voz?.lang || "es-CL";
      utterance.rate = 1.05;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        setIsSpeaking(true);
        isSpeakingRef.current = true;
        abortarEscucha();
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        isSpeakingRef.current = false;
        if (callbackOnEnd && isHandsFreeRef.current) {
          // Pausa de 250ms anti-eco para que cese el audio de los parlantes
          setTimeout(() => {
            callbackOnEnd();
          }, 250);
        }
      };

      utterance.onerror = (e) => {
        console.warn("SpeechSynthesis error:", e);
        setIsSpeaking(false);
        isSpeakingRef.current = false;
        if (callbackOnEnd && isHandsFreeRef.current) {
          setTimeout(() => {
            callbackOnEnd();
          }, 250);
        }
      };

      synthRef.current.speak(utterance);
    } catch (e) {
      console.error("Error al sintetizar voz:", e);
      setIsSpeaking(false);
      isSpeakingRef.current = false;
    }
  };

  // Reconocimiento de Voz nativo (STT)
  const inicializarReconocimientoVoz = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("SpeechRecognition no soportado en este navegador.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "es-CL";

    rec.onstart = () => {
      setIsListening(true);
      isListeningRef.current = true;
    };

    rec.onresult = (event) => {
      let currentTranscript = "";
      for (let i = 0; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }
      setTranscript(currentTranscript);
      transcriptRef.current = currentTranscript;
    };

    rec.onerror = (event) => {
      if (event.error !== "no-speech" && event.error !== "aborted") {
        console.warn("Speech recognition error:", event.error);
      }
      setIsListening(false);
      isListeningRef.current = false;
    };

    rec.onend = () => {
      setIsListening(false);
      isListeningRef.current = false;

      // Si el usuario dijo algo, procesarlo inmediatamente de forma automática
      const textoCapturado = transcriptRef.current.trim();
      if (textoCapturado.length > 0) {
        procesarEntradaVoz(textoCapturado);
      }
    };

    recognitionRef.current = rec;
  };

  const iniciarEscucha = () => {
    if (!recognitionRef.current) return;
    if (isSpeakingRef.current) return; // No encender si el agente sigue hablando
    if (isListeningRef.current) return;

    setTranscript("");
    transcriptRef.current = "";

    try {
      recognitionRef.current.start();
    } catch (e) {
      // Puede ocurrir si ya estaba en arranque
    }
  };

  const abortarEscucha = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (_) {}
    }
    setIsListening(false);
    isListeningRef.current = false;
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      Swal.fire({
        icon: "info",
        title: "Micrófono no soportado",
        text: "Tu navegador no soporta reconocimiento de voz nativo (Web Speech API). Puedes usar el teclado en el campo de texto.",
      });
      return;
    }

    if (isListening) {
      abortarEscucha();
    } else {
      if (isSpeaking) {
        synthRef.current?.cancel();
        setIsSpeaking(false);
        isSpeakingRef.current = false;
      }
      iniciarEscucha();
    }
  };

  // Carga inicial de datos
  const cargarClientes = async () => {
    setLoadingCustomers(true);
    try {
      const { data } = await api.get("/clientes");
      const list = data || [];
      setCustomers(list);
      customersRef.current = list;
    } catch (e) {
      console.error("Error al cargar clientes:", e);
    } finally {
      setLoadingCustomers(false);
    }
  };

  const cargarCatalogo = async () => {
    try {
      const { data } = await api.get("/productos");
      setCatalogProducts(data || []);
    } catch (e) {
      console.error("Error al cargar productos:", e);
    }
  };

  // Saludo conversacional inicial
  const arrancarConversacionInicial = () => {
    if (selectedCustomerRef.current) {
      setConversationState("ESPERANDO_PRODUCTOS");
      hablarMensaje(
        `Hola, soy tu Asistente Tridente. Cliente ${
          selectedCustomerRef.current.alias || selectedCustomerRef.current.nombre
        } seleccionado. ¿Qué productos deseas agregar al pedido?`,
        () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        }
      );
    } else {
      setConversationState("ESPERANDO_CLIENTE");
      hablarMensaje(
        "Hola, soy tu Asistente Tridente. ¿Para qué cliente deseas armar el pedido?",
        () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        }
      );
    }
  };

  const handleSelectCustomer = (client) => {
    setSelectedCustomer(client);
    selectedCustomerRef.current = client;
    setCustomerSearch("");
    setClientCandidates([]);

    const dirs = client.direcciones || [];
    setCustomerAddresses(dirs);
    const principalDir = dirs.find((d) => d.principal) || dirs[0];
    setSelectedAddressId(principalDir ? principalDir.id : "");

    // Si estábamos esperando cliente, avanzar al paso de productos
    if (conversationStateRef.current === "ESPERANDO_CLIENTE") {
      setConversationState("ESPERANDO_PRODUCTOS");
    }
  };

  // Procesamiento Central de la Entrada por Voz con Máquina de Estados
  const procesarEntradaVoz = async (textoDictado) => {
    const texto = (textoDictado || transcriptRef.current || "").trim();
    if (!texto) return;

    abortarEscucha();
    setIsProcessingVoice(true);

    try {
      // 1. Si estamos en confirmación final y el usuario dijo sí / confirmar
      const textoBajo = texto.toLowerCase();
      if (conversationStateRef.current === "CONFIRMACION_FINAL") {
        if (
          textoBajo.includes("si") ||
          textoBajo.includes("sí") ||
          textoBajo.includes("confirmar") ||
          textoBajo.includes("emitir") ||
          textoBajo.includes("dale") ||
          textoBajo.includes("proceder")
        ) {
          await ejecutarEmisionPedido();
          return;
        } else if (
          textoBajo.includes("no") ||
          textoBajo.includes("espera") ||
          textoBajo.includes("falta") ||
          textoBajo.includes("cancelar")
        ) {
          setConversationState("ESPERANDO_PRODUCTOS");
          hablarMensaje(
            "Entendido. ¿Qué otro producto deseas agregar o modificar?",
            () => {
              if (isHandsFreeRef.current) iniciarEscucha();
            }
          );
          return;
        }
      }

      // 2. Si estamos en desambiguación y el usuario eligió una opción por voz
      if (
        conversationStateRef.current === "DESAMBIGUAR_PRODUCTO" &&
        ambiguousItems.length > 0
      ) {
        const itemAmbiguo = ambiguousItems[0];
        let opcionElegida = null;

        if (
          textoBajo.includes("primero") ||
          textoBajo.includes("primera") ||
          textoBajo.includes("uno") ||
          textoBajo.includes("1")
        ) {
          opcionElegida = itemAmbiguo.opciones[0];
        } else if (
          textoBajo.includes("segundo") ||
          textoBajo.includes("segunda") ||
          textoBajo.includes("dos") ||
          textoBajo.includes("2")
        ) {
          opcionElegida = itemAmbiguo.opciones[1] || itemAmbiguo.opciones[0];
        } else if (
          textoBajo.includes("tercero") ||
          textoBajo.includes("tercera") ||
          textoBajo.includes("tres") ||
          textoBajo.includes("3")
        ) {
          opcionElegida = itemAmbiguo.opciones[2] || itemAmbiguo.opciones[0];
        } else {
          // Búsqueda por coincidencia de nombre
          opcionElegida = itemAmbiguo.opciones.find((op) =>
            textoBajo.includes(op.nombre.toLowerCase()) || op.nombre.toLowerCase().includes(textoBajo)
          );
        }

        if (opcionElegida) {
          resolverItemAmbiguo(itemAmbiguo, opcionElegida);
          return;
        }
      }

      // 3. Llamar al backend para interpretar el dictado
      const { data } = await api.post(
        "/pedidos/asistente-ia/interpretar-dictado",
        {
          texto: texto,
          cliente_id: selectedCustomerRef.current
            ? selectedCustomerRef.current.id
            : null,
          estado_conversacion: conversationStateRef.current,
        }
      );

      // A. Manejo de Comandos Especiales detectados por Backend
      if (data.comando_detectado === "finalizar") {
        if (!cartItemsRef.current.length) {
          hablarMensaje(
            "El pedido aún no tiene productos. Dicta al menos un producto antes de finalizar.",
            () => {
              if (isHandsFreeRef.current) iniciarEscucha();
            }
          );
          return;
        }
        setConversationState("CONFIRMACION_FINAL");
        const tot = calcularTotales(cartItemsRef.current);
        const cliNom =
          selectedCustomerRef.current?.alias ||
          selectedCustomerRef.current?.nombre ||
          "el cliente";
        const mensajeFinal = `El pedido para ${cliNom} tiene ${
          cartItemsRef.current.length
        } productos por un total de ${money.format(
          tot.total
        )}. ¿Deseas confirmar la emisión a Defontana?`;
        hablarMensaje(mensajeFinal, () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        });
        return;
      }

      if (data.comando_detectado === "confirmar") {
        await ejecutarEmisionPedido();
        return;
      }

      if (data.comando_detectado === "eliminar" && data.parametro_comando) {
        const prodTerm = data.parametro_comando.toLowerCase();
        setCartItems((prev) =>
          prev.filter(
            (p) =>
              !p.nombre.toLowerCase().includes(prodTerm) &&
              !p.codigo.toLowerCase().includes(prodTerm)
          )
        );
        hablarMensaje(
          data.mensaje_voz || `Eliminado ${data.parametro_comando} del pedido.`,
          () => {
            if (isHandsFreeRef.current) iniciarEscucha();
          }
        );
        return;
      }

      if (data.comando_detectado === "vaciar") {
        setCartItems([]);
        setAmbiguousItems([]);
        setPendingProduct(null);
        setDetectedCategory(null);
        setCategoryBrands([]);
        setCategoryProducts([]);
        hablarMensaje(
          "He vaciado el borrador del pedido. ¿Qué productos deseas agregar?",
          () => {
            if (isHandsFreeRef.current) iniciarEscucha();
          }
        );
        return;
      }

      // B. Detección de Cliente
      if (data.cliente_detectado_id && !selectedCustomerRef.current) {
        const foundClient = customersRef.current.find(
          (c) => c.id === data.cliente_detectado_id
        );
        if (foundClient) {
          handleSelectCustomer(foundClient);
        }
      } else if (data.clientes_candidatos && data.clientes_candidatos.length > 0) {
        setClientCandidates(data.clientes_candidatos);
        hablarMensaje(data.mensaje_voz, () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        });
        return;
      }

      // C. Detección de Categoría General (ej: "cigarros", "bolsas", "vasos", etc.)
      if (data.categoria_detectada && data.marcas_categoria && data.marcas_categoria.length > 0) {
        setDetectedCategory(data.categoria_detectada);
        setCategoryBrands(data.marcas_categoria || []);
        setCategoryProducts(data.productos_categoria || []);
        setConversationState("EXPLORANDO_CATEGORIA");
        hablarMensaje(data.mensaje_voz, () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        });
        return;
      }

      // D. Caso: Producto encontrado que espera cantidad (ESPERANDO_CANTIDAD)
      if (data.producto_pendiente_cantidad) {
        setPendingProduct(data.producto_pendiente_cantidad);
        setConversationState("ESPERANDO_CANTIDAD");
        hablarMensaje(data.mensaje_voz, () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        });
        return;
      }

      // D. Si estábamos en ESPERANDO_CANTIDAD y el usuario respondió la cantidad
      if (
        conversationStateRef.current === "ESPERANDO_CANTIDAD" &&
        pendingProductRef.current &&
        data.items &&
        data.items.length > 0
      ) {
        const cantItem = data.items[0];
        agregarProductoAlBorrador(
          pendingProductRef.current,
          cantItem.cantidad || 1,
          cantItem.tipo_empaque || "unidad"
        );
        setPendingProduct(null);
        setConversationState("ESPERANDO_PRODUCTOS");

        const msgVoz = `Agregadas ${cantItem.cantidad || 1} ${
          cantItem.tipo_empaque === "caja" ? "cajas" : "unidades"
        } de ${pendingProductRef.current.nombre}. ¿Deseas agregar más productos o finalizar?`;
        hablarMensaje(msgVoz, () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        });
        return;
      }

      // E. Procesar Productos Exactos y Múltiples (Desambiguación)
      const newAmbiguos = [];
      const newItemsToAdd = [];

      for (const it of data.items || []) {
        if (it.estado === "exacto" && it.producto) {
          newItemsToAdd.push({
            producto: it.producto,
            cantidad: it.cantidad || 1,
            tipo_empaque: it.tipo_empaque || "unidad",
          });
        } else if (it.estado === "multiple" && it.opciones?.length > 0) {
          newAmbiguos.push(it);
        }
      }

      if (newItemsToAdd.length > 0) {
        for (const item of newItemsToAdd) {
          agregarProductoAlBorrador(
            item.producto,
            item.cantidad,
            item.tipo_empaque
          );
        }
      }

      if (newAmbiguos.length > 0) {
        setAmbiguousItems(newAmbiguos);
        setConversationState("DESAMBIGUAR_PRODUCTO");
      } else {
        setAmbiguousItems([]);
        if (selectedCustomerRef.current) {
          setConversationState("ESPERANDO_PRODUCTOS");
        }
      }

      // F. Locución de Respuesta del Agente
      const locucion =
        data.mensaje_voz ||
        data.mensaje_asistente ||
        "Dictado procesado. ¿Qué más deseas agregar?";
      hablarMensaje(locucion, () => {
        if (isHandsFreeRef.current) iniciarEscucha();
      });
    } catch (e) {
      console.error("Error al interpretar dictado:", e);
      hablarMensaje(
        "Hubo un problema al procesar el dictado. Por favor inténtalo de nuevo.",
        () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        }
      );
    } finally {
      setIsProcessingVoice(false);
    }
  };

  // Resolver ítem ambiguo seleccionado por voz o clic
  const resolverItemAmbiguo = (ambiguo, opcionSeleccionada) => {
    agregarProductoAlBorrador(
      opcionSeleccionada,
      ambiguo.cantidad || 1,
      ambiguo.tipo_empaque || "unidad"
    );
    setAmbiguousItems((prev) => prev.filter((item) => item !== ambiguo));
    setConversationState("ESPERANDO_PRODUCTOS");

    const empNombre =
      ambiguo.tipo_empaque === "caja" ? "cajas" : "unidades";
    const msg = `Agregado ${ambiguo.cantidad || 1} ${empNombre} de ${
      opcionSeleccionada.nombre
    }. ¿Deseas agregar más productos o finalizar?`;
    hablarMensaje(msg, () => {
      if (isHandsFreeRef.current) iniciarEscucha();
    });
  };

  const handleSelectCategoryBrand = (marca) => {
    // Si el usuario pulsa en una marca o familia sugerida por voz
    procesarEntradaVoz(marca);
  };

  // Agregar al borrador del pedido
  const agregarProductoAlBorrador = (
    prod,
    cantidad = 1,
    tipo_empaque = "unidad"
  ) => {
    setDetectedCategory(null);
    setCategoryBrands([]);
    setCategoryProducts([]);
    setCartItems((prev) => {
      const index = prev.findIndex(
        (p) => p.id === prod.id && p.tipo_empaque === tipo_empaque
      );

      let precioFinal = Number(prod.precio) || 0;
      if (tipo_empaque === "caja" && prod.precio_caja) {
        precioFinal = Number(prod.precio_caja);
      }

      if (index >= 0) {
        const copy = [...prev];
        const nuevaCantidad = copy[index].cantidad + cantidad;
        copy[index] = {
          ...copy[index],
          cantidad: nuevaCantidad,
          subtotal: nuevaCantidad * precioFinal,
        };
        return copy;
      }

      return [
        ...prev,
        {
          id: prod.id,
          codigo: prod.codigo,
          nombre: prod.nombre,
          precio_unitario: precioFinal,
          cantidad: cantidad,
          tipo_empaque: tipo_empaque,
          cantidad_caja: prod.cantidad_caja,
          tiene_caja: prod.tiene_caja,
          afecto: Boolean(prod.afecto),
          subtotal: cantidad * precioFinal,
        },
      ];
    });
  };

  const modificarCantidad = (index, delta) => {
    setCartItems((prev) => {
      const copy = [...prev];
      const target = copy[index];
      const newCant = target.cantidad + delta;
      if (newCant <= 0) {
        return copy.filter((_, i) => i !== index);
      }
      target.cantidad = newCant;
      target.subtotal = newCant * target.precio_unitario;
      return copy;
    });
  };

  const eliminarLinea = (index) => {
    setCartItems((prev) => prev.filter((_, i) => i !== index));
  };

  // Búsqueda manual de productos
  useEffect(() => {
    if (!manualSearch.trim()) {
      setManualSearchResults([]);
      return;
    }
    const term = manualSearch.toLowerCase();
    const results = catalogProducts
      .filter(
        (p) =>
          p.activo &&
          ((p.nombre && p.nombre.toLowerCase().includes(term)) ||
            (p.codigo && p.codigo.toLowerCase().includes(term)))
      )
      .slice(0, 8);
    setManualSearchResults(results);
  }, [manualSearch, catalogProducts]);

  // Búsqueda remota complementaria (fallback si no está en la carga inicial)
  useEffect(() => {
    const term = customerSearch.trim();
    if (term.length < 2) return;

    const timer = setTimeout(async () => {
      try {
        setSearchingBackendCustomers(true);
        const { data } = await api.get("/clientes", { params: { search: term } });
        if (data && data.length > 0) {
          setCustomers((prev) => {
            const existingIds = new Set(prev.map((c) => c.id));
            const newOnes = data.filter((c) => !existingIds.has(c.id));
            if (newOnes.length > 0) {
              const updated = [...prev, ...newOnes];
              customersRef.current = updated;
              return updated;
            }
            return prev;
          });
        }
      } catch (err) {
        console.warn("Error en búsqueda remota de clientes:", err);
      } finally {
        setSearchingBackendCustomers(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [customerSearch]);

  // Filtrado de clientes de alta precisión con ranking multi-token y normalización de tildes
  const filteredCustomers = useMemo(() => {
    if (!customerSearch.trim()) return [];

    const rawTerm = customerSearch.trim();
    const normTerm = normalizarTextoBusqueda(rawTerm);
    const termTokens = normTerm.split(/\s+/).filter(Boolean);
    const cleanRutTerm = limpiarRutParaBusqueda(rawTerm);
    const cleanPhoneTerm = limpiarTelefonoParaBusqueda(rawTerm);

    const scored = [];

    for (const c of customers) {
      const aliasNorm = normalizarTextoBusqueda(c.alias || "");
      const nombreNorm = normalizarTextoBusqueda(c.nombre || "");
      const rutClean = limpiarRutParaBusqueda(c.rut || "");
      const phoneClean = limpiarTelefonoParaBusqueda(c.celular || "");
      const correoNorm = normalizarTextoBusqueda(c.correo || "");

      // Cadena consolidada de búsqueda
      const fullText = `${aliasNorm} ${nombreNorm} ${correoNorm} ${c.rut || ""} ${c.celular || ""}`;

      let score = 0;

      // 1. Coincidencia exacta de alias o nombre
      if (aliasNorm === normTerm || nombreNorm === normTerm) {
        score += 200;
      }
      // 2. Prefijo en alias o nombre
      else if (aliasNorm.startsWith(normTerm) || nombreNorm.startsWith(normTerm)) {
        score += 150;
      }
      // 3. Substring completo
      else if (aliasNorm.includes(normTerm) || nombreNorm.includes(normTerm)) {
        score += 100;
      }

      // 4. Coincidencia por RUT
      if (cleanRutTerm.length >= 2 && rutClean) {
        if (rutClean === cleanRutTerm) {
          score += 180;
        } else if (rutClean.includes(cleanRutTerm) || cleanRutTerm.includes(rutClean)) {
          score += 120;
        }
      }

      // 5. Coincidencia por Celular
      if (cleanPhoneTerm.length >= 4 && phoneClean) {
        if (phoneClean === cleanPhoneTerm) {
          score += 150;
        } else if (phoneClean.includes(cleanPhoneTerm)) {
          score += 90;
        }
      }

      // 6. Coincidencia multi-token (cada palabra debe coincidir en algún campo)
      if (termTokens.length > 0) {
        const matchingTokens = termTokens.filter((token) => fullText.includes(token));
        if (matchingTokens.length === termTokens.length) {
          score += 70 + termTokens.length * 10;
        } else if (matchingTokens.length > 0 && matchingTokens.length / termTokens.length >= 0.5) {
          score += 35 * (matchingTokens.length / termTokens.length);
        }
      }

      if (score > 0) {
        scored.push({ customer: c, score });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, 15).map((item) => item.customer);
  }, [customerSearch, customers]);

  // Cálculo de totales
  const calcularTotales = (items) => {
    return items.reduce(
      (acc, line) => {
        acc.total += line.subtotal;
        if (line.afecto) {
          acc.afecto += line.subtotal;
        } else {
          acc.exento += line.subtotal;
        }
        return acc;
      },
      { afecto: 0, exento: 0, total: 0 }
    );
  };

  const totales = calcularTotales(cartItems);

  // Confirmar y Emitir Pedido
  const ejecutarEmisionPedido = async () => {
    if (!selectedCustomerRef.current) {
      hablarMensaje("Debes seleccionar un cliente de destino antes de emitir.");
      Swal.fire("Atención", "Debes seleccionar un cliente de destino.", "warning");
      return;
    }
    if (!selectedAddressId) {
      hablarMensaje(
        "El cliente no tiene dirección de despacho activa para emitir el pedido."
      );
      Swal.fire(
        "Atención",
        "El cliente seleccionado debe tener al menos una dirección de despacho activa.",
        "warning"
      );
      return;
    }
    if (!cartItemsRef.current.length) {
      hablarMensaje("El pedido no contiene productos.");
      Swal.fire("Atención", "El pedido no contiene productos.", "warning");
      return;
    }

    setIsSubmitting(true);
    abortarEscucha();

    try {
      const payload = {
        cliente_id: selectedCustomerRef.current.id,
        direccion_id: selectedAddressId,
        productos: cartItemsRef.current.map((line) => ({
          producto_id: line.id,
          cantidad: line.cantidad,
          tipo_empaque: line.tipo_empaque || "unidad",
        })),
      };

      const { data } = await api.post("/pedidos/admin/crear-pedido", payload);

      const folio =
        data.folio_defontana_afecto || data.folio_defontana;
      const mensajeExitoVoz = folio
        ? `Pedido emitido con éxito bajo el folio Defontana ${folio} y sincronizado al ERP.`
        : "Pedido generado exitosamente y sincronizado con Defontana ERP.";

      hablarMensaje(mensajeExitoVoz, () => {
        if (onOrderCreated) {
          onOrderCreated(data);
        }
        onClose();
      });

      Swal.fire({
        icon: "success",
        title: "¡Pedido Emitido con Éxito!",
        html: `
          <p>El pedido <strong>#${data.id?.slice(0, 8).toUpperCase()}</strong> fue generado exitosamente.</p>
          ${
            folio
              ? `<p class="badge bg-success p-2 mt-2">Folio Defontana: ${folio}</p>`
              : ""
          }
        `,
      });
    } catch (e) {
      console.error("Error al emitir pedido:", e);
      const errorMsg =
        e.response?.data?.detail || "Ocurrió un error al emitir el pedido.";
      hablarMensaje(
        `Hubo un problema al emitir el pedido: ${errorMsg}`,
        () => {
          if (isHandsFreeRef.current) iniciarEscucha();
        }
      );
      Swal.fire("Error", errorMsg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop-custom" role="presentation" style={{ zIndex: 1060 }}>
      {/* Estilos CSS scoped para animaciones sonoras y visualizador */}
      <style>{`
        @keyframes soundwave {
          0%, 100% { height: 6px; opacity: 0.4; }
          50% { height: 28px; opacity: 1; }
        }
        .soundwave-bar {
          width: 4px;
          background: #2563eb;
          border-radius: 4px;
          animation: soundwave 1.1s ease-in-out infinite;
        }
        .soundwave-bar:nth-child(2) { animation-delay: 0.15s; height: 18px; }
        .soundwave-bar:nth-child(3) { animation-delay: 0.3s; height: 26px; }
        .soundwave-bar:nth-child(4) { animation-delay: 0.45s; height: 20px; }
        .soundwave-bar:nth-child(5) { animation-delay: 0.6s; height: 14px; }

        @keyframes pulse-radar {
          0% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
          70% { transform: scale(1.06); box-shadow: 0 0 0 16px rgba(220, 38, 38, 0); }
          100% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
        }
        .pulse-recording {
          animation: pulse-radar 1.4s infinite;
        }

        @keyframes pulse-subtle {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        .animate-subtle-pulse {
          animation: pulse-subtle 1.8s infinite;
        }
      `}</style>

      <div
        className="category-modal"
        style={{
          maxWidth: "1020px",
          width: "95%",
          maxHeight: "94vh",
          display: "flex",
          flexDirection: "column",
          borderRadius: "16px",
        }}
      >
        {/* Header Modal */}
        <header className="d-flex justify-content-between align-items-center pb-2 border-bottom">
          <div className="d-flex align-items-center gap-3">
            <div
              className="p-2 rounded-circle shadow-sm"
              style={{ backgroundColor: "#eff6ff", color: "#2563eb" }}
            >
              <Sparkles size={24} />
            </div>
            <div>
              <div className="d-flex align-items-center gap-2">
                <span className="eyebrow mb-0" style={{ color: "#2563eb", fontWeight: 700 }}>
                  AGENTE CONVERSACIONAL TRIDENTE IA
                </span>
                <span className="badge bg-primary text-white" style={{ fontSize: "0.7rem" }}>
                  Bidireccional Manos Libres
                </span>
              </div>
              <h2 className="mb-0" style={{ fontSize: "1.35rem" }}>
                Crear Pedido Asistido por Voz
              </h2>
            </div>
          </div>

          <div className="d-flex align-items-center gap-2">
            {/* Control Silenciar / Reactivar Audio del Agente */}
            <button
              type="button"
              className={`btn btn-sm d-flex align-items-center gap-1 ${
                isMuted ? "btn-outline-danger" : "btn-outline-secondary"
              }`}
              onClick={() => {
                const nextMuted = !isMuted;
                setIsMuted(nextMuted);
                isMutedRef.current = nextMuted;
                if (nextMuted && synthRef.current) {
                  synthRef.current.cancel();
                  setIsSpeaking(false);
                  isSpeakingRef.current = false;
                }
              }}
              title={isMuted ? "Activar voz del agente" : "Silenciar voz del agente"}
            >
              {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              <span className="d-none d-sm-inline">{isMuted ? "Voz Silenciada" : "Voz Activa"}</span>
            </button>

            {/* Toggle Manos Libres */}
            <button
              type="button"
              className={`btn btn-sm d-flex align-items-center gap-1 ${
                isHandsFree ? "btn-success" : "btn-outline-secondary"
              }`}
              onClick={() => {
                const nextHf = !isHandsFree;
                setIsHandsFree(nextHf);
                isHandsFreeRef.current = nextHf;
              }}
              title={
                isHandsFree
                  ? "Modo Manos Libres activo: el agente pregunta y escucha solo"
                  : "Modo Manual: pulsa el micrófono para hablar"
              }
            >
              <Radio size={15} />
              <span className="d-none d-sm-inline">
                {isHandsFree ? "Manos Libres: ON" : "Manos Libres: OFF"}
              </span>
            </button>

            <button
              type="button"
              className="icon-button ms-2"
              onClick={onClose}
              aria-label="Cerrar modal"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Cuerpo del Modal */}
        <div
          className="modal-body-custom"
          style={{ overflowY: "auto", flex: "1 1 auto", padding: "1.15rem 0.5rem" }}
        >
          {/* PASO 1: Selector de Cliente */}
          <div className="card mb-3 p-3 shadow-sm border-0" style={{ backgroundColor: "#f8fafc" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <strong className="d-flex align-items-center gap-2 text-dark">
                <User size={18} className="text-primary" /> Paso 1: Cliente de Destino
              </strong>

              {selectedCustomer && (
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary py-0"
                  onClick={() => {
                    setSelectedCustomer(null);
                    selectedCustomerRef.current = null;
                    setCustomerAddresses([]);
                    setSelectedAddressId("");
                    setConversationState("ESPERANDO_CLIENTE");
                    hablarMensaje(
                      "¿Para qué cliente deseas armar el pedido?",
                      () => {
                        if (isHandsFreeRef.current) iniciarEscucha();
                      }
                    );
                  }}
                >
                  Cambiar cliente
                </button>
              )}
            </div>

            {!selectedCustomer ? (
              <div className="position-relative">
                <div className="position-relative">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Buscar o dictar cliente por Razón Social, Alias, RUT o Celular..."
                    value={customerSearch}
                    onChange={(e) => setCustomerSearch(e.target.value)}
                    autoFocus
                  />
                  {searchingBackendCustomers && (
                    <div
                      className="position-absolute top-50 end-0 translate-middle-y me-3 text-secondary"
                      style={{ fontSize: "0.8rem", pointerEvents: "none" }}
                    >
                      <RotateCcw size={14} className="animate-spin text-primary" />
                    </div>
                  )}
                </div>

                {filteredCustomers.length > 0 && (
                  <div
                    className="dropdown-menu show w-100 position-absolute shadow mt-1"
                    style={{ maxHeight: "260px", overflowY: "auto", zIndex: 1070 }}
                  >
                    {filteredCustomers.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        className="dropdown-item d-flex justify-content-between align-items-center py-2 border-bottom"
                        onClick={() => handleSelectCustomer(c)}
                      >
                        <div>
                          <strong>{c.alias || c.nombre}</strong>
                          {c.alias && c.nombre && c.alias !== c.nombre && (
                            <small className="text-muted d-block">{c.nombre}</small>
                          )}
                          <div className="d-flex align-items-center gap-2 mt-1">
                            <span className="badge bg-light text-secondary border" style={{ fontSize: "0.75rem" }}>
                              {c.rut || "Sin RUT"}
                            </span>
                            {c.celular && (
                              <small className="text-secondary" style={{ fontSize: "0.75rem" }}>
                                Tel: {c.celular}
                              </small>
                            )}
                          </div>
                        </div>
                        <span className="badge bg-light text-dark border">
                          {c.porcentaje ? `${c.porcentaje}% desc.` : "Precio lista"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {customerSearch.trim().length >= 2 && filteredCustomers.length === 0 && !searchingBackendCustomers && (
                  <div
                    className="dropdown-menu show w-100 position-absolute shadow mt-1 p-3 text-center text-secondary small"
                    style={{ zIndex: 1070 }}
                  >
                    No se encontraron clientes para "<strong>{customerSearch}</strong>".
                    <div className="text-muted mt-1" style={{ fontSize: "0.75rem" }}>
                      Intenta con otra palabra, alias o solo los números del RUT.
                    </div>
                  </div>
                )}

                {/* Candidatos sugeridos por el agente por coincidencia de voz */}
                {clientCandidates.length > 0 && (
                  <div className="mt-2 p-2 bg-white rounded border border-primary">
                    <span className="small text-primary fw-bold d-block mb-1">
                      💡 El agente detectó posibles opciones de cliente. Selecciona una:
                    </span>
                    <div className="d-flex flex-wrap gap-2">
                      {clientCandidates.map((cand) => {
                        const fullClient = customers.find((c) => c.id === cand.id);
                        return (
                          <button
                            key={cand.id}
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => {
                              if (fullClient) handleSelectCustomer(fullClient);
                            }}
                          >
                            <strong>{cand.alias || cand.nombre}</strong>{" "}
                            <small className="text-muted">({cand.rut || "RUT"})</small>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                <small className="text-muted mt-1 d-block">
                  Tip: También puedes dictar directamente: <em>"pedido para Minimarket San Jorge..."</em>
                </small>
              </div>
            ) : (
              <div className="row g-2 align-items-center">
                <div className="col-md-7">
                  <div className="p-2 bg-white rounded border">
                    <strong className="d-block text-primary">
                      {selectedCustomer.alias || selectedCustomer.nombre}
                    </strong>
                    <small className="text-secondary d-block">
                      {selectedCustomer.nombre && selectedCustomer.alias
                        ? `${selectedCustomer.nombre} · `
                        : ""}
                      {selectedCustomer.rut || "Sin RUT"} · Cel: {selectedCustomer.celular || "-"}
                    </small>
                  </div>
                </div>
                <div className="col-md-5">
                  <label className="form-label small text-secondary mb-1">
                    <MapPin size={14} className="me-1" /> Dirección de Despacho
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={selectedAddressId}
                    onChange={(e) => setSelectedAddressId(e.target.value)}
                  >
                    {customerAddresses.map((dir) => (
                      <option key={dir.id} value={dir.id}>
                        {dir.direccion} {dir.comuna ? `(${dir.comuna})` : ""}{" "}
                        {dir.principal ? "⭐ Principal" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* PASO 2: Consola Agéntica Bidireccional de Voz */}
          <div
            className="card mb-3 p-3 border-0 shadow-sm"
            style={{
              backgroundColor: isListening ? "#fef2f2" : isSpeaking ? "#f0f9ff" : "#f0fdf4",
              transition: "background-color 0.3s ease",
            }}
          >
            <div className="d-flex align-items-center justify-content-between mb-2">
              <div className="d-flex align-items-center gap-2">
                <strong
                  className="d-flex align-items-center gap-2"
                  style={{
                    color: isListening ? "#991b1b" : isSpeaking ? "#0369a1" : "#166534",
                  }}
                >
                  <Sparkles size={18} /> Paso 2: Diálogo y Dictado por Voz
                </strong>

                {/* Badge de fase conversacional */}
                <span
                  className="badge rounded-pill"
                  style={{
                    backgroundColor: "#ffffff",
                    color: "#334155",
                    border: "1px solid #cbd5e1",
                    fontSize: "0.75rem",
                  }}
                >
                  {conversationState === "ESPERANDO_CLIENTE" && "Paso: Indicar Cliente"}
                  {conversationState === "ESPERANDO_PRODUCTOS" && "Paso: Dictando Productos"}
                  {conversationState === "ESPERANDO_CANTIDAD" && "Paso: Indicar Cantidad"}
                  {conversationState === "DESAMBIGUAR_PRODUCTO" && "Paso: Desambiguar Producto"}
                  {conversationState === "CONFIRMACION_FINAL" && "Paso: Confirmación Final"}
                </span>
              </div>

              {/* Indicador de estado de audio */}
              <div className="d-flex align-items-center gap-2">
                {isSpeaking && (
                  <div className="d-flex align-items-center gap-1 bg-white px-2 py-1 rounded-pill border">
                    <span className="small text-primary fw-bold me-1">Agente hablando:</span>
                    <div className="soundwave-bar" />
                    <div className="soundwave-bar" />
                    <div className="soundwave-bar" />
                    <div className="soundwave-bar" />
                    <div className="soundwave-bar" />
                  </div>
                )}

                {isListening && (
                  <span className="badge bg-danger pulse-recording d-flex align-items-center gap-1 px-3 py-1">
                    <Ear size={14} /> Escuchando tu voz...
                  </span>
                )}
              </div>
            </div>

            {/* Burbuja del Asistente (Respuesta Hablada y Visual) */}
            <div
              className="p-3 mb-2 rounded border shadow-sm d-flex align-items-start gap-2"
              style={{
                backgroundColor: "#ffffff",
                borderColor: isSpeaking ? "#93c5fd" : "#e2e8f0",
              }}
            >
              <div
                className="rounded-circle p-2 mt-1"
                style={{
                  backgroundColor: isSpeaking ? "#dbeafe" : "#f1f5f9",
                  color: isSpeaking ? "#2563eb" : "#475569",
                }}
              >
                <Sparkles size={18} />
              </div>
              <div className="flex-grow-1">
                <div className="d-flex justify-content-between align-items-center mb-1">
                  <strong style={{ fontSize: "0.85rem", color: "#1e293b" }}>
                    Agente Tridente IA:
                  </strong>
                  <button
                    type="button"
                    className="btn btn-sm btn-link text-decoration-none p-0 text-secondary"
                    onClick={() => hablarMensaje(assistantMessage)}
                    title="Repetir mensaje hablado"
                  >
                    <Volume2 size={15} /> Repetir audio
                  </button>
                </div>
                <p className="mb-0 text-dark fw-medium" style={{ fontSize: "0.95rem" }}>
                  {assistantMessage}
                </p>

                {/* Opciones interactivas de marcas si se detectó una categoría */}
                {detectedCategory && categoryBrands.length > 0 && (
                  <div className="mt-2 pt-2 border-top border-light">
                    <span className="small text-primary fw-bold d-block mb-1">
                      🏷️ Opciones disponibles en {detectedCategory} (haz clic o dicta tu elección):
                    </span>
                    <div className="d-flex flex-wrap gap-2">
                      {categoryBrands.map((marca, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className="btn btn-sm btn-outline-primary bg-white shadow-sm d-inline-flex align-items-center gap-1"
                          onClick={() => handleSelectCategoryBrand(marca)}
                          title={`Ver opciones de ${marca}`}
                        >
                          <Sparkles size={13} className="text-primary" />
                          <span>{marca}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Si un producto está esperando cantidad */}
            {pendingProduct && (
              <div className="alert alert-warning py-2 px-3 mb-2 small d-flex align-items-center justify-content-between">
                <div>
                  <strong>Producto detectado:</strong> {pendingProduct.nombre}{" "}
                  <span className="badge bg-light text-dark border ms-1">
                    {money.format(pendingProduct.precio)}
                  </span>
                  <div className="text-secondary mt-1">
                    Por favor dicta la cantidad (ej: <em>"3 paquetes"</em>, <em>"5 unidades"</em> o <em>"2 cajas"</em>).
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary"
                  onClick={() => {
                    setPendingProduct(null);
                    setConversationState("ESPERANDO_PRODUCTOS");
                  }}
                >
                  Cancelar
                </button>
              </div>
            )}

            {/* Barra de Micrófono y Transcripción */}
            <div className="d-flex gap-2 align-items-center mt-1">
              <button
                type="button"
                className={`btn btn-lg d-flex align-items-center justify-content-center p-3 rounded-circle shadow ${
                  isListening
                    ? "btn-danger pulse-recording"
                    : isSpeaking
                    ? "btn-info text-white"
                    : "btn-primary"
                }`}
                style={{ width: "56px", height: "56px", flexShrink: 0 }}
                onClick={toggleListening}
                title={isListening ? "Detener micrófono" : "Hablar con el agente"}
              >
                {isListening ? <MicOff size={26} /> : <Mic size={26} />}
              </button>

              <div className="flex-grow-1 position-relative">
                <input
                  type="text"
                  className="form-control"
                  style={{
                    borderColor: isListening ? "#ef4444" : "#cbd5e1",
                    boxShadow: isListening ? "0 0 0 3px rgba(239, 68, 68, 0.2)" : "none",
                  }}
                  placeholder={
                    isListening
                      ? "🎙️ Escuchando... habla de forma natural..."
                      : isSpeaking
                      ? "🔊 El agente está hablando..."
                      : "Escribe o dicta aquí tus productos (ej: Bolsa camiseta 5 un, Pall mall 2 cartones...)"
                  }
                  value={transcript}
                  onChange={(e) => {
                    setTranscript(e.target.value);
                    transcriptRef.current = e.target.value;
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      procesarEntradaVoz(transcript);
                    }
                  }}
                />
              </div>

              <button
                type="button"
                className="btn btn-success d-flex align-items-center gap-1 shadow-sm"
                disabled={isProcessingVoice || !transcript.trim()}
                onClick={() => procesarEntradaVoz(transcript)}
              >
                {isProcessingVoice ? (
                  <RotateCcw size={16} className="animate-spin" />
                ) : (
                  <Sparkles size={16} />
                )}
                Interpretar
              </button>
            </div>

            {/* Opciones de Desambiguación Hablada / Visual */}
            {ambiguousItems.length > 0 && (
              <div className="mt-3 p-3 bg-white rounded border border-warning shadow-sm">
                <strong className="text-warning-emphasis d-flex align-items-center gap-1 mb-2">
                  <AlertCircle size={16} /> Opciones encontradas para desambiguar:
                </strong>
                {ambiguousItems.map((amb, idx) => (
                  <div key={idx} className="mb-2 p-2 bg-light rounded">
                    <span className="small text-secondary d-block mb-1">
                      Para el término: <strong>"{amb.termino_original}"</strong> ({amb.cantidad}{" "}
                      {amb.tipo_empaque}):
                    </span>
                    <div className="d-flex flex-wrap gap-2">
                      {amb.opciones.map((opc, opcIdx) => (
                        <button
                          key={opc.id}
                          type="button"
                          className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1 text-start"
                          onClick={() => resolverItemAmbiguo(amb, opc)}
                        >
                          <span className="badge bg-primary me-1">{opcIdx + 1}</span>
                          <span>
                            <strong>{opc.nombre}</strong>{" "}
                            <small className="text-muted">({money.format(opc.precio)})</small>
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* PASO 3: Vista Previa y Borrador de Pedido en Vivo */}
          <div className="card p-3 border-0 shadow-sm" style={{ backgroundColor: "#f8fafc" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <strong className="text-dark d-flex align-items-center gap-2">
                <Package size={18} className="text-primary" /> Paso 3: Vista Previa del Pedido
              </strong>

              {/* Búsqueda manual complementaria */}
              <div className="position-relative" style={{ width: "290px" }}>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="+ Agregar producto manualmente..."
                  value={manualSearch}
                  onChange={(e) => setManualSearch(e.target.value)}
                />
                {manualSearchResults.length > 0 && (
                  <div
                    className="dropdown-menu show w-100 position-absolute shadow mt-1"
                    style={{ maxHeight: "200px", overflowY: "auto", zIndex: 1070 }}
                  >
                    {manualSearchResults.map((prod) => (
                      <button
                        key={prod.id}
                        type="button"
                        className="dropdown-item d-flex justify-content-between align-items-center py-1 small"
                        onClick={() => {
                          agregarProductoAlBorrador(prod, 1, "unidad");
                          setManualSearch("");
                        }}
                      >
                        <span className="text-truncate" style={{ maxWidth: "190px" }}>
                          {prod.nombre}
                        </span>
                        <strong>{money.format(prod.precio)}</strong>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Tabla del Borrador */}
            {cartItems.length === 0 ? (
              <p className="text-secondary text-center py-4 mb-0">
                Aún no has agregado productos al pedido. Dicta mediante el micrófono (ej:{" "}
                <em>"5 paquetes de bolsa camiseta y 2 cartones de Pall Mall"</em>) o búscalos en la barra.
              </p>
            ) : (
              <div className="table-responsive bg-white rounded border">
                <table className="table table-sm table-hover mb-0 align-middle">
                  <thead className="table-light small">
                    <tr>
                      <th>Código</th>
                      <th>Producto</th>
                      <th className="text-center">Empaque</th>
                      <th className="text-center" style={{ width: "120px" }}>
                        Cantidad
                      </th>
                      <th className="text-end">Precio Unit.</th>
                      <th className="text-end">Subtotal</th>
                      <th style={{ width: "40px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {cartItems.map((item, idx) => (
                      <tr key={`${item.id}-${item.tipo_empaque}-${idx}`}>
                        <td className="small text-muted">{item.codigo}</td>
                        <td>
                          <strong>{item.nombre}</strong>
                          {item.afecto ? (
                            <span className="badge bg-primary ms-1" style={{ fontSize: "0.65rem" }}>
                              Afecto
                            </span>
                          ) : (
                            <span className="badge bg-secondary ms-1" style={{ fontSize: "0.65rem" }}>
                              Exento
                            </span>
                          )}
                        </td>
                        <td className="text-center">
                          <span
                            className={`badge ${
                              item.tipo_empaque === "caja"
                                ? "bg-info text-dark"
                                : "bg-light text-dark border"
                            }`}
                          >
                            {item.tipo_empaque === "caja"
                              ? `Caja ${item.cantidad_caja ? `x${item.cantidad_caja}` : ""}`
                              : "Unidad"}
                          </span>
                        </td>
                        <td>
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary p-1"
                              style={{ width: "24px", height: "24px", lineHeight: 1 }}
                              onClick={() => modificarCantidad(idx, -1)}
                            >
                              <Minus size={12} />
                            </button>
                            <span className="fw-bold px-2">{item.cantidad}</span>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary p-1"
                              style={{ width: "24px", height: "24px", lineHeight: 1 }}
                              onClick={() => modificarCantidad(idx, 1)}
                            >
                              <Plus size={12} />
                            </button>
                          </div>
                        </td>
                        <td className="text-end">{money.format(item.precio_unitario)}</td>
                        <td className="text-end fw-bold text-success">
                          {money.format(item.subtotal)}
                        </td>
                        <td className="text-center">
                          <button
                            type="button"
                            className="btn btn-sm text-danger p-0"
                            onClick={() => eliminarLinea(idx)}
                            title="Eliminar producto"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Resumen de Totales */}
            {cartItems.length > 0 && (
              <div className="d-flex justify-content-between align-items-end mt-3">
                <div className="text-secondary small">
                  <span>
                    💡 Puedes decir <em>"Finalizar pedido"</em> o <em>"Confirmar"</em> para emitir
                    por voz.
                  </span>
                </div>
                <div className="p-3 bg-white rounded border shadow-sm" style={{ minWidth: "260px" }}>
                  <div className="d-flex justify-content-between small text-secondary mb-1">
                    <span>Afecto Neto:</span>
                    <span>{money.format(totales.afecto)}</span>
                  </div>
                  <div className="d-flex justify-content-between small text-secondary mb-1">
                    <span>Exento:</span>
                    <span>{money.format(totales.exento)}</span>
                  </div>
                  <div className="d-flex justify-content-between small text-secondary mb-2">
                    <span>IVA (19%):</span>
                    <span>{money.format(Math.round(totales.afecto * 0.19))}</span>
                  </div>
                  <div className="d-flex justify-content-between border-top pt-2">
                    <strong className="fs-6">Total Pedido:</strong>
                    <strong className="fs-5 text-success">{money.format(totales.total)}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Modal */}
        <footer className="d-flex justify-content-between align-items-center pt-3 border-top">
          <button
            type="button"
            className="btn btn-light"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancelar
          </button>

          <button
            type="button"
            className="btn btn-primary btn-lg d-flex align-items-center gap-2"
            disabled={isSubmitting || !selectedCustomer || cartItems.length === 0}
            onClick={ejecutarEmisionPedido}
          >
            {isSubmitting ? (
              <>
                <RotateCcw size={18} className="animate-spin" />
                Emitiendo a Defontana...
              </>
            ) : (
              <>
                <CheckCircle2 size={18} />
                Confirmar y Emitir Pedido ({money.format(totales.total)})
              </>
            )}
          </button>
        </footer>
      </div>
    </div>
  );
}
