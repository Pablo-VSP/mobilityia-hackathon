# ITP LATAM - WB Workshop

> Export of [https://partyrock.aws/u/dxduarte/ILIvEOSua/ITP-LATAM-WB-Workshop](https://partyrock.aws/u/dxduarte/ILIvEOSua/ITP-LATAM-WB-Workshop)

---

# WORKING BACKWARDS JOURNEY POWERED BY AI

You are about to embark in a Working Backwards journey. Working Backwards is Amazon mechanism for innovation. Amazon's Working Backwards mechanism is a strategic approach to product development and innovation that starts with the customer and works backward to the technology. Rather than beginning with an idea or technology and trying to find customers for it. This forces teams to deeply understand the customer problem, articulate the value proposition clearly, and ensure that every feature serves a genuine customer need before any development begins. By starting with the desired customer experience and working backward to determine what capabilities, technologies, and resources are required, Amazon ensures that innovation remains customer-obsessed and that teams build products that truly matter to customers rather than solutions in search of problems.

---

## STEP 1 - LISTEN THE CUSTOMER

To better understand who the customer is and to answer the first Working Backwards question - "Who is the customer and what insights do we have about them?" - we must be purposeful and frame the challenge clearly. Innovation doesn't happen by chance. Innovation is the result of directing our choices with awareness, purpose, and deliberate action. We need to be intentional in our decisions. Please provide the following information and press PLAY APP.

### What do we want to solve?

Este proyecto tiene como objetivo construir un sistema autónomo de optimización de flotas impulsado por agentes de IA utilizando Amazon Bedrock AgentCore. El sistema analiza datos telemétricos de autobuses y toma decisiones para reducir el consumo de combustible, anticipar el mantenimiento de unidades y optimizar las operaciones.

### Who is the customer?

Un proveedor de servicios de movilidad que conecta ciudades mediante rutas programadas de autobuses, ofreciendo distintos niveles de servicio (económico, ejecutivo, lujo) y gestionando venta de boletos, horarios y logística de viajes.

**Atributos clave:**

- Tipo: Empresa de transporte
- Servicio: Traslado de pasajeros por carretera
- Cobertura: Regional (varias ciudades del país)
- Canales: Taquillas físicas, web y app
- Variables operativas: rutas, horarios, precios, disponibilidad, tipo de servicio

### Company Name

**Mobility ADO**

### What are the pain points, needs, and wants?

- Gastos excesivos de combustible — Sin visibilidad sobre qué genera el consumo, no puedo controlarlo
- Poco retorno de inversión por viaje — Los márgenes son tan ajustados que cada viaje debe ser más rentable
- Falta de métricas de conducción óptima — No tengo estándares claros para evaluar y mejorar el desempeño de mis conductores
- Variabilidad en la flota — Conductores diferentes = consumos diferentes = imposible estandarizar eficiencia
- Presión regulatoria ambiental — Necesito demostrar reducción de emisiones, pero sin datos no puedo probarlo
- Resistencia al cambio tecnológico — Mis equipos operativos desconfían de nuevas herramientas, especialmente si las ven como vigilancia
- Ciclos de decisión largos — Necesito evidencia sólida antes de invertir, pero el tiempo corre
- No se cuenta con una herramienta que anticipe la realización de mantenimientos preventivos, evitando mantenimientos mayores que representan un alto costo a la operacion

> En esencia: Gasto mucho en combustible, no sé por qué, y no puedo mejorar lo que no mido.

### Segment

- Transportation & Logistics Industry

### Social Context

**Contexto Social y Cultural — Mobility ADO | México**

#### Características Clave del Segmento

**Mobility ADO** opera en un entorno donde el transporte terrestre de pasajeros no es solo un servicio comercial, sino una **infraestructura social crítica**. En México, el autobús de carretera representa el modo de movilidad interurbana más accesible para millones de personas, lo que posiciona a la empresa en un cruce entre lógica empresarial y responsabilidad social percibida.

#### Dinámica Social y Cultural que Moldea sus Decisiones

##### 🏢 Cultura Organizacional y Jerarquía Interna

Las empresas de transporte en México operan bajo estructuras **fuertemente jerárquicas**, donde las decisiones estratégicas se concentran en niveles directivos y la operación en campo mantiene una cultura de autonomía informal. Esto genera una brecha entre quienes deciden adoptar tecnología y quienes deben ejecutarla día a día. Los conductores y supervisores de ruta perciben las herramientas de monitoreo como **mecanismos de vigilancia y control**, no como apoyo operativo, lo que activa resistencia activa o pasiva al cambio.

La confianza se construye de manera **relacional y gradual** — no basta con presentar datos; se requiere demostración práctica, acompañamiento cercano y validación por parte de figuras de autoridad reconocidas dentro de la organización.

##### 👥 Roles e Influencias en la Toma de Decisiones

En este segmento, la decisión de adoptar una solución tecnológica como un sistema de optimización de flotas con IA involucra múltiples actores con motivaciones distintas:

| Actor | Rol | Motivación principal |
|---|---|---|
| Director de Operaciones | Decisor estratégico | Reducción de costos y eficiencia medible |
| Gerente de Flota | Evaluador técnico | Control operativo y menos fallas |
| Conductores | Usuario final | Estabilidad laboral, no ser "vigilados" |
| Área Financiera | Validador de ROI | Justificación del gasto ante directivos |
| Área de Sustentabilidad | Habilitador regulatorio | Cumplimiento ambiental y reputación |

La influencia del **gremio de conductores** y los sindicatos es un factor social relevante: cualquier herramienta que se perciba como evaluación punitiva del desempeño individual puede encontrar resistencia organizada.

##### 📐 Normas y Valores que Condicionan el Comportamiento

**Pragmatismo operativo:** En la cultura empresarial mexicana del transporte, prevalece una mentalidad de *"si funciona, no lo toques"*. La innovación se adopta cuando resuelve un problema concreto e inmediato, no por tendencia tecnológica. Esto significa que el sistema debe demostrar valor tangible y rápido.

**Desconfianza hacia lo intangible:** La IA y los algoritmos generan escepticismo en equipos operativos que valoran la experiencia empírica sobre modelos predictivos. La frase cultural implícita es: *"yo conozco mis rutas mejor que cualquier sistema"*.

**Cultura del dato incipiente:** A diferencia de sectores como fintech o retail, el transporte terrestre en México tiene una madurez digital heterogénea. Muchas decisiones aún se toman por intuición o experiencia acumulada, no por análisis de datos estructurados.

**Responsabilidad colectiva del resultado:** El éxito o fracaso de una ruta se percibe como responsabilidad compartida entre conductor, despachador y gerencia. Esto puede ser un aliado si el sistema se presenta como herramienta de equipo, no de fiscalización individual.

##### 🌍 Presiones Externas y Percepciones Sociales

**Presión regulatoria ambiental creciente:** México ha incrementado sus compromisos climáticos bajo el Acuerdo de París y la agenda de la SEMARNAT. Las empresas de transporte enfrentan presión para demostrar reducción de emisiones, especialmente en rutas que atraviesan zonas metropolitanas con restricciones de circulación. Esto convierte la **trazabilidad de emisiones** en una necesidad estratégica, no solo operativa.

**Imagen pública y reputación sectorial:** El transporte de pasajeros en México carga con percepciones sociales mixtas — asociado históricamente con informalidad, accidentes y servicio inconsistente. Empresas como ADO han construido una diferenciación por calidad, lo que hace que la eficiencia operativa también sea un **activo de marca**.

**Competencia y presión de márgenes:** La expansión de alternativas como aerolíneas de bajo costo y plataformas de movilidad compartida presiona los márgenes del transporte terrestre. Esto genera urgencia real por optimizar costos sin sacrificar calidad de servicio.

##### 🔄 Motivaciones Profundas Detrás de las Necesidades Declaradas

Más allá de los dolores operativos explícitos, las motivaciones subyacentes que impulsan la búsqueda de una solución como esta son:

- **Control y certeza:** En un entorno de alta variabilidad (precios de combustible, condiciones viales, comportamiento de conductores), el deseo profundo es **reducir la incertidumbre** y tener visibilidad real sobre lo que ocurre en la operación.
- **Legitimidad ante stakeholders:** Poder presentar datos concretos de eficiencia y sostenibilidad ante inversionistas, reguladores y clientes corporativos es un diferenciador competitivo con valor social y financiero.
- **Preservación del modelo de negocio:** La preocupación no es solo ahorrar combustible — es **garantizar la viabilidad del negocio** en un contexto donde los márgenes se comprimen y la presión externa aumenta.
- **Reconocimiento interno:** Los tomadores de decisión que impulsen esta transformación buscan también **validación dentro de su organización** como líderes que modernizaron la operación.

#### Síntesis del Perfil Social

> Mobility ADO toma decisiones en un entorno donde la **confianza se gana con evidencia práctica**, la **jerarquía define los ritmos de adopción**, y la **cultura operativa valora la experiencia sobre el algoritmo**. El éxito de una solución tecnológica en este contexto depende tanto de su capacidad técnica como de su habilidad para integrarse sin amenazar las identidades y roles establecidos dentro de la organización. La narrativa correcta no es *"la IA reemplaza el juicio humano"*, sino *"la IA le da a tu equipo información que antes no tenía para tomar mejores decisiones"*.

---

### Country

Mexico

### Language

Spanish Latin America

---

### Economic Context

**Contexto Económico Clave — Mobility ADO | Transporte de Pasajeros por Carretera | México**

#### Entorno Macroeconómico que Afecta las Decisiones de Inversión

**Presión inflacionaria persistente** sobre los costos operativos del transporte: el diésel, las refacciones y la mano de obra calificada han registrado incrementos sostenidos, comprimiendo márgenes en un sector donde las tarifas al pasajero tienen límites regulatorios y alta sensibilidad al precio. Esto convierte la eficiencia operativa en una palanca de supervivencia, no solo de optimización.

**Tipo de cambio volátil** impacta directamente la estructura de costos: los autobuses, sistemas telemétricos y tecnología de IA se adquieren o licencian en dólares, mientras los ingresos se generan en pesos. Cada depreciación del peso encarece la inversión tecnológica y alarga los ciclos de decisión de compra.

**Crecimiento moderado del PIB** con recuperación desigual post-pandemia. El sector transporte terrestre de pasajeros recuperó volumen, pero no necesariamente rentabilidad, dado el alza estructural en costos de combustible y mantenimiento.

#### Comportamiento de Compra y Prioridades de Gasto

**El ROI demostrable es el filtro principal de decisión.** En un entorno de márgenes ajustados, las áreas financieras exigen evidencia cuantificada antes de aprobar cualquier inversión tecnológica. Los proyectos sin métricas claras de retorno en menos de 18–24 meses enfrentan rechazo o postergación indefinida.

**Ciclos de aprobación presupuestal largos y escalonados.** Las empresas del segmento operan con estructuras corporativas donde la inversión en tecnología compite con necesidades operativas inmediatas (mantenimiento correctivo, renovación de flota, cumplimiento regulatorio). La tecnología percibida como "no esencial" queda rezagada.

**Preferencia por modelos de gasto operativo (OpEx) sobre capital (CapEx).** Ante la incertidumbre económica, los operadores de transporte prefieren esquemas de suscripción, pago por uso o resultados garantizados, que no comprometan liquidez ni activos en el balance.

**El combustible representa entre el 35% y el 45% del costo operativo total** de una empresa de autobuses en México. Cualquier solución que demuestre reducción directa en este rubro tiene atención inmediata de la dirección financiera y operativa.

#### Impacto del Entorno Económico en las Decisiones Financieras

**Presión regulatoria ambiental con costo económico real.** Las normas de emisiones (NOM-044, compromisos de descarbonización) generan obligaciones que requieren evidencia medible. Sin datos telemétricos, la empresa no puede acreditar cumplimiento ni acceder a incentivos fiscales o financiamiento verde, lo que representa un costo de oportunidad creciente.

**La variabilidad operativa entre conductores es una fuga económica no contabilizada.** La ausencia de estándares de conducción eficiente genera dispersión en el consumo de combustible que, a escala de flota, representa millones de pesos anuales en pérdidas no visibles en el P&L.

**El mantenimiento correctivo no planificado destruye rentabilidad por viaje.** Una unidad fuera de servicio no solo genera costo de reparación mayor, sino pérdida de ingresos, penalizaciones contractuales y daño reputacional. En un contexto donde el crédito para capital de trabajo es costoso (tasas Banxico elevadas), los imprevistos financieros tienen un impacto desproporcionado.

**La desconfianza tecnológica tiene raíz económica.** Los equipos operativos asocian nuevas herramientas de monitoreo con recortes de personal o sanciones, lo que genera resistencia activa. Esta resistencia tiene un costo real: retrasa la adopción, reduce la calidad del dato y limita el valor del sistema.

#### Síntesis Estratégica del Perfil Económico

| Dimensión | Impacto en la Decisión |
|---|---|
| Costos de combustible al alza | Alta urgencia de soluciones con ahorro medible |
| Márgenes operativos comprimidos | Exige ROI rápido y demostrable |
| Volatilidad cambiaria | Favorece modelos OpEx en pesos |
| Presión regulatoria ambiental | Crea necesidad de datos de emisiones verificables |
| Tasas de interés elevadas | Penaliza el mantenimiento correctivo no previsto |
| Resistencia interna al cambio | Requiere estrategia de adopción gradual con victorias tempranas |

> **La decisión de invertir en un sistema de optimización de flotas con IA no es tecnológica: es financiera.** El cliente comprará cuando vea que el costo de no actuar supera el costo de la solución.

---

### Technology Context

**Contexto Tecnológico: Mobility ADO — Transporte y Logística | México**

#### Madurez Tecnológica del Segmento

Mobility ADO opera en un segmento de transporte terrestre de pasajeros que históricamente ha sido **conservador en adopción tecnológica**, pero que en los últimos 5 años ha experimentado una presión creciente hacia la digitalización, impulsada por competidores de movilidad (plataformas de ride-hailing, aerolíneas de bajo costo) y por exigencias regulatorias ambientales.

**Nivel de madurez estimado: Intermedio-Transicional**

La empresa ya cuenta con canales digitales (app, web, taquillas conectadas), lo que indica una base tecnológica funcional. Sin embargo, la inteligencia operativa —el uso de datos para tomar decisiones en tiempo real sobre flota, rutas y conductores— sigue siendo un área **subdesarrollada o inexistente**. Existe infraestructura, pero no explotación analítica de ella.

#### Características Tecnológicas Clave del Segmento

##### Infraestructura y Herramientas Actuales

- Uso de **sistemas ERP o TMS básicos** para gestión de rutas, horarios y boletos
- Presencia de **GPS embarcado** en unidades, pero frecuentemente subutilizado (solo para rastreo, no para análisis)
- Canales digitales de venta activos, pero desconectados de la inteligencia operativa
- Escasa integración entre datos de campo (telemetría) y sistemas de gestión central

##### Datos y Analítica

- Generación de datos operativos existe, pero **no hay cultura de explotación analítica**
- Las decisiones de mantenimiento y combustible se toman de forma **reactiva**, basadas en experiencia del operador, no en datos
- Ausencia de dashboards en tiempo real para supervisores de flota
- No existe un modelo predictivo de mantenimiento ni de eficiencia por conductor

##### Conectividad y Dispositivos

- Alta penetración de **smartphones entre conductores y personal operativo** (uso personal intensivo)
- Conectividad en terminales y oficinas es estable; en carretera puede ser intermitente según la ruta
- Preferencia por interfaces **móviles simples** sobre plataformas web complejas en el nivel operativo

#### Actitudes y Apertura hacia Nuevas Tecnologías

##### Dirección y Alta Gerencia

- **Apertura condicionada**: dispuestos a invertir si existe evidencia de ROI claro y medible
- Ciclos de decisión largos por cultura corporativa y necesidad de justificación financiera sólida
- Sensibilidad alta a **reducción de costos operativos** como argumento principal de adopción
- Interés creciente en cumplimiento ambiental como driver secundario (presión regulatoria)

##### Mandos Medios y Operativos

- **Resistencia moderada-alta** a herramientas percibidas como mecanismos de vigilancia o control
- Mayor apertura cuando la tecnología se presenta como **apoyo al trabajo**, no como sustitución o fiscalización
- Familiaridad con apps de consumo (WhatsApp, Google Maps) que puede aprovecharse como referencia de UX
- Desconfianza hacia sistemas complejos que requieren capacitación extensa

##### Conductores

- Perfil tecnológico **básico-intermedio**: usan smartphones, pero no están familiarizados con telemetría o plataformas de análisis
- Receptivos a retroalimentación si se presenta como **mejora de desempeño personal** (bonos, reconocimiento) y no como sanción
- La gamificación y los incentivos son palancas efectivas de adopción en este perfil

#### Cómo el Acceso, Conocimiento y Preferencias Tecnológicas Moldean la Adopción

| Dimensión | Comportamiento Observado |
|---|---|
| **Acceso** | Infraestructura digital existe pero fragmentada; el dato está disponible pero no conectado |
| **Conocimiento** | Brecha entre lo que la tecnología puede hacer y lo que el equipo sabe aprovechar |
| **Actitud** | Pragmática: adoptan si ven beneficio tangible rápido; rechazan si perciben complejidad o control |
| **Preferencias** | Interfaces simples, móviles, con alertas accionables; rechazo a plataformas densas en datos sin interpretación |
| **Confianza** | Se construye con pilotos pequeños, resultados visibles y acompañamiento humano en la implementación |

#### Implicaciones para la Solución de IA con Amazon Bedrock AgentCore

- El sistema debe **traducir datos complejos en recomendaciones simples y accionables**, no en reportes técnicos
- La narrativa de adopción interna debe posicionarse como **"asistente de operaciones"**, no como sistema de vigilancia
- Los primeros resultados deben ser **rápidos y visibles** (primeras 4-8 semanas) para vencer los ciclos de decisión largos
- La integración con dispositivos móviles es crítica para la adopción en campo
- El módulo de mantenimiento predictivo tiene el **mayor potencial de adopción inmediata**, ya que resuelve un dolor concreto, medible y sin connotación de control sobre personas
- La reducción de emisiones debe ser **cuantificada y reportable** para responder a la presión regulatoria como argumento de valor adicional

---

### Cultural Context

**Contexto Cultural Clave: Mobility ADO — México**

#### Valores Culturales que Moldean la Toma de Decisiones

**Jerarquía y autoridad institucional:** En México, las decisiones estratégicas de alto impacto tienden a concentrarse en niveles directivos. La adopción de tecnología como IA y telemática requiere aval explícito de liderazgo senior antes de que los equipos operativos la legitimen. Sin ese respaldo visible, la resistencia al cambio se amplifica.

**Confianza basada en relaciones personales (confianza relacional):** El cliente mexicano no compra tecnología, compra a quien se la vende. La credibilidad del proveedor se construye a través del trato cercano, la presencia constante y el acompañamiento post-venta. Las decisiones de inversión tecnológica se aceleran cuando existe una relación de confianza establecida, no solo evidencia técnica.

**Aversión al riesgo y cultura de evidencia:** Existe una tendencia marcada a solicitar pruebas piloto, casos de éxito locales y garantías antes de comprometer presupuesto. El ciclo de decisión largo mencionado como pain point es, en parte, un reflejo cultural: invertir sin certeza se percibe como imprudencia, no como agilidad.

#### Normas y Creencias que Influyen en el Comportamiento Operativo

**Desconfianza hacia la vigilancia tecnológica:** En el contexto laboral mexicano, la telemática y el monitoreo de conductores puede interpretarse como control punitivo más que como herramienta de mejora. Esta percepción activa resistencia sindical y operativa. El encuadre del sistema debe enfatizar desarrollo profesional y reconocimiento, no fiscalización.

**Cultura del "mientras funcione":** El mantenimiento reactivo está profundamente arraigado en operaciones de transporte en México. Intervenir una unidad que "todavía corre" se percibe como gasto innecesario. Cambiar este paradigma requiere demostrar el costo real del mantenimiento correctivo frente al preventivo con datos propios de la flota.

**Orgullo por la operación propia:** Los equipos operativos con años de experiencia valoran su conocimiento empírico. Una solución de IA que "les diga qué hacer" puede generar rechazo. El sistema debe posicionarse como un asistente que potencia su criterio, no como un reemplazo de su expertise.

#### Presiones del Entorno que Aceleran la Adopción

**Regulación ambiental creciente:** México avanza en compromisos de reducción de emisiones bajo acuerdos internacionales. ADO, como operador de escala nacional, enfrenta presión regulatoria y reputacional para demostrar métricas ambientales concretas. Esto convierte la visibilidad de emisiones en una necesidad estratégica, no solo operativa.

**Competencia y márgenes comprimidos:** El sector de transporte terrestre en México opera con márgenes ajustados y competencia de plataformas digitales de movilidad. La eficiencia operativa ya no es una ventaja diferencial, es una condición de supervivencia.

**Digitalización acelerada post-pandemia:** La adopción de canales digitales (app, web) por parte de ADO refleja una organización que ya inició su transformación digital. Existe apertura institucional a la tecnología, pero con expectativa de resultados tangibles y rápidos.

#### Implicaciones Directas para el Proyecto

| Factor Cultural | Implicación para el Sistema |
|---|---|
| Jerarquía decisional | Presentar ROI ejecutivo claro antes que funcionalidades técnicas |
| Confianza relacional | Priorizar acompañamiento humano en la implementación |
| Resistencia a la vigilancia | Comunicar el sistema como "copiloto de eficiencia", no como auditor |
| Mantenimiento reactivo | Mostrar casos reales de ahorro por mantenimiento predictivo |
| Presión regulatoria | Incluir reportes de emisiones como entregable visible del sistema |
| Cultura de evidencia | Diseñar un piloto acotado con métricas irrefutables desde la semana uno |

---

### My name is...

**Valentina Herrera**

---

### Regulatory Context

**Contexto Regulatorio Clave — Mobility ADO | México**

#### Marco Regulatorio Principal

##### 🚌 Transporte Federal de Pasajeros

La operación de rutas interurbanas en México está regulada principalmente por la **Secretaría de Infraestructura, Comunicaciones y Transportes (SICT)**, antes SCT. Las empresas como ADO requieren **concesiones federales** para operar rutas entre estados, lo que implica:

- Cumplimiento de itinerarios y tarifas autorizadas
- Renovación periódica de permisos por unidad
- Restricciones sobre modificación de rutas sin aprobación previa

Esto **limita la flexibilidad operativa** y hace que cualquier optimización de rutas deba alinearse con los permisos vigentes, no solo con la eficiencia técnica.

##### ⛽ Regulación de Emisiones y Medio Ambiente

La **NOM-044-SEMARNAT** establece los límites máximos de emisiones contaminantes para vehículos pesados nuevos. Para la flota existente, aplican verificaciones periódicas y presión creciente del **Programa de Verificación Vehicular** en estados con alta contaminación.

A nivel federal, México tiene compromisos bajo el **Acuerdo de París** y la **Ley General de Cambio Climático**, que obligan a sectores intensivos en emisiones —como el transporte— a reportar y reducir su huella de carbono. Esto convierte la **medición de emisiones en una obligación emergente**, no solo una ventaja competitiva.

> **Impacto directo:** ADO necesita datos verificables de reducción de emisiones para cumplir con auditorías ambientales y anticiparse a regulaciones más estrictas que ya están en discusión legislativa.

##### 🔧 Normativas de Seguridad y Mantenimiento Vehicular

La **NOM-068-SCT-2-2014** regula las condiciones físico-mecánicas mínimas de los vehículos de autotransporte federal. El incumplimiento puede derivar en:

- Retención de unidades en operativos de la **Guardia Nacional**
- Multas y suspensión de concesiones
- Responsabilidad civil ante accidentes

Esto crea una **presión regulatoria directa** sobre el mantenimiento preventivo: no es solo un tema de costos, sino de continuidad operativa y riesgo legal.

##### 👨‍✈️ Regulación Laboral del Personal de Conducción

Los conductores de autotransporte están sujetos a la **Ley Federal del Trabajo** y a normativas específicas de la SICT sobre:

- Horas máximas de conducción continua
- Descansos obligatorios entre turnos
- Licencias federales por categoría (tipo E para autobús)

Cualquier sistema de monitoreo de conductores debe diseñarse considerando el **marco de privacidad laboral** y los acuerdos sindicales vigentes, ya que la resistencia sindical puede bloquear implementaciones tecnológicas percibidas como vigilancia.

##### 🔐 Protección de Datos y Tecnología

La **Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP)** regula el tratamiento de datos de pasajeros y empleados. El uso de telemetría, geolocalización y análisis de comportamiento de conductores debe:

- Contar con avisos de privacidad actualizados
- Justificarse bajo principios de **finalidad y proporcionalidad**
- Considerar el consentimiento informado de los conductores monitoreados

##### 💰 Política Fiscal y de Combustibles

El precio del diésel en México está parcialmente regulado por la política de **IEPS (Impuesto Especial sobre Producción y Servicios)**, con subsidios que han variado según el contexto político. Las empresas de transporte concesionado pueden acceder a **estímulos fiscales al IEPS** sobre combustibles, lo que hace que la **documentación precisa del consumo** sea un requisito fiscal, no solo operativo.

#### Cómo el Marco Regulatorio Influye en las Decisiones de ADO

| Dimensión | Influencia Regulatoria | Comportamiento Resultante |
|---|---|---|
| **Inversión tecnológica** | Necesidad de evidencia para auditorías ambientales y fiscales | Busca soluciones que generen reportes verificables y auditables |
| **Mantenimiento** | NOM-068 y riesgo de retención de unidades | Prioriza mantenimiento preventivo sobre correctivo por presión legal |
| **Monitoreo de conductores** | Marco laboral y sindical restrictivo | Requiere implementación gradual con enfoque en beneficio, no en control |
| **Optimización de rutas** | Concesiones fijas de la SICT | La optimización se enfoca en eficiencia dentro de rutas autorizadas, no en rediseño de red |
| **Reporte de emisiones** | Ley de Cambio Climático y compromisos internacionales | Necesita datos estructurados y continuos, no mediciones puntuales |
| **Gestión de combustible** | Estímulos fiscales al IEPS | La medición precisa del consumo tiene valor fiscal directo y justifica la inversión en telemetría |

#### Tensiones Regulatorias Clave a Considerar

**1. Innovación vs. Concesión rígida:** El modelo de concesiones limita la agilidad operativa. Un sistema de IA que recomiende ajustes de ruta o frecuencia debe operar dentro de los parámetros autorizados, lo que reduce el alcance de la optimización autónoma.

**2. Monitoreo vs. Privacidad laboral:** La telemetría de conductores es técnicamente posible y regulatoriamente necesaria, pero sindicalmente sensible. El diseño del sistema debe enmarcar el monitoreo como **herramienta de seguridad y eficiencia**, no como mecanismo disciplinario.

**3. Urgencia ambiental vs. Ciclos de decisión largos:** Las regulaciones ambientales se endurecerán, pero la cultura corporativa de ADO exige evidencia antes de invertir. Esto crea una **ventana de oportunidad estrecha**: quien implemente primero tendrá ventaja regulatoria y competitiva.

---

### Professional Context

**Contexto Profesional Clave — Mobility ADO | México**

#### Perfil del Tomador de Decisiones

El decisor principal opera en un entorno donde la presión operativa es constante y los márgenes de rentabilidad son estrechos. Generalmente ocupa roles como **Director de Operaciones, Gerente de Flota o Director de Tecnología**, con responsabilidad directa sobre la eficiencia del servicio, la rentabilidad por ruta y el cumplimiento regulatorio. Su perfil combina experiencia técnica en logística terrestre con creciente exposición a herramientas digitales, aunque su adopción tecnológica suele ser cautelosa y basada en evidencia.

#### Influencia del Entorno Laboral en sus Necesidades y Comportamientos

##### Industria y Contexto Operativo

El transporte de pasajeros por carretera en México opera bajo un modelo de alta complejidad logística: múltiples rutas, flotas heterogéneas, conductores con perfiles diversos y una infraestructura vial que introduce variabilidad constante. Esto genera una cultura operativa donde **la reactividad predomina sobre la planeación estratégica**, ya que los equipos están acostumbrados a resolver problemas en tiempo real más que a anticiparlos.

##### Presiones Económicas y de Rentabilidad

El combustible representa uno de los mayores rubros de costo operativo —frecuentemente entre el 30% y 40% del costo total por viaje—, y su volatilidad en México lo convierte en una variable crítica e incontrolable percibida. Esta presión genera una **necesidad urgente de visibilidad y control**, pero también una resistencia a invertir en soluciones cuyo retorno no sea inmediato y medible.

##### Cultura Organizacional y Resistencia al Cambio

En empresas de transporte tradicional mexicanas, existe una cultura operativa arraigada donde los conductores y supervisores de campo perciben las herramientas de monitoreo como mecanismos de vigilancia más que como aliados de mejora. Esto obliga al decisor a **gestionar el cambio internamente** antes de poder capturar el valor tecnológico, añadiendo una capa de complejidad política y humana al proceso de adopción.

##### Ciclos de Decisión e Inversión

El entorno corporativo de empresas como ADO implica estructuras de aprobación multicapa, donde cualquier inversión tecnológica significativa requiere justificación financiera robusta, alineación con objetivos estratégicos y validación de casos de uso reales. El decisor **necesita evidencia antes de comprometerse**, lo que alarga los ciclos pero también significa que, una vez convencido, el compromiso es sólido y de largo plazo.

##### Presión Regulatoria y Reputacional

México avanza hacia marcos regulatorios más exigentes en materia de emisiones y eficiencia energética para el transporte. Empresas de escala nacional como ADO enfrentan **escrutinio público y gubernamental**, lo que convierte la reducción de emisiones en una necesidad tanto operativa como reputacional. Sin embargo, sin datos estructurados, la empresa no puede demostrar avances ni cumplimiento.

##### Gestión de Activos y Mantenimiento

La falta de mantenimiento predictivo genera un patrón costoso: las unidades fallan en operación, se incurre en mantenimientos correctivos de alto costo, se afecta la puntualidad del servicio y se deteriora la experiencia del pasajero. El decisor vive este ciclo con frustración porque **sabe que es evitable**, pero carece de las herramientas para anticiparlo sistemáticamente.

#### Comportamientos Clave Derivados de su Contexto

| Comportamiento | Origen |
|---|---|
| Exige ROI claro y rápido | Márgenes ajustados y ciclos de aprobación largos |
| Desconfía de soluciones "caja negra" | Cultura operativa basada en experiencia tangible |
| Prioriza estabilidad operativa sobre innovación | Riesgo de afectar el servicio durante implementación |
| Busca estandarización de procesos | Variabilidad de conductores y consumos |
| Valora datos propios sobre benchmarks externos | Contexto operativo muy específico por ruta y región |
| Necesita herramientas que no generen conflicto interno | Resistencia de equipos de campo al monitoreo |

#### Síntesis del Contexto Profesional

El decisor en Mobility ADO opera en la intersección entre **la presión por eficiencia inmediata y la necesidad de transformación estructural a largo plazo**. Su entorno laboral lo condiciona a ser pragmático, orientado a resultados medibles y cauteloso con la tecnología, no por falta de visión, sino porque el costo de equivocarse —en márgenes, en operación y en cultura interna— es alto. Una solución de IA que hable su idioma operativo, demuestre valor rápido y no amenace la dinámica de sus equipos tiene una ventana real de adopción.

---

### Social and Environmental Consciousness

**Contexto Social y Ambiental — Mobility ADO | México**

#### 🌎 Presión Regulatoria y Compromisos Climáticos en México

México ha asumido compromisos internacionales bajo el Acuerdo de París, con metas de reducción de emisiones de GEI que impactan directamente al sector transporte, responsable de aproximadamente el **23% de las emisiones nacionales de CO₂**. La Secretaría de Medio Ambiente y Recursos Naturales (SEMARNAT) y la Agencia Nacional de Seguridad Vial (ANSV) ejercen presión creciente sobre operadores de transporte para demostrar eficiencia energética medible y verificable.

> **Implicación directa:** Sin datos telemétricos estructurados, ADO no puede cumplir ni demostrar avances ante reguladores, lo que representa un riesgo reputacional y legal creciente.

#### 🚌 El Transporte Público como Bien Social en México

En el contexto mexicano, el autobús de pasajeros interurbano no es percibido únicamente como un servicio comercial — es un **bien social esencial**. Para millones de mexicanos de segmentos medios y populares, representa la única opción de movilidad entre ciudades. Esto genera una doble expectativa social:

- **Accesibilidad económica:** La sociedad espera tarifas justas y estables, lo que comprime los márgenes operativos y hace que la eficiencia interna sea la única palanca real de rentabilidad.
- **Responsabilidad de servicio:** Retrasos, cancelaciones o unidades en mal estado generan impacto social amplificado, especialmente en comunidades con baja conectividad alternativa.

#### ♻️ Sostenibilidad como Diferenciador Competitivo Emergente

El consumidor mexicano urbano — especialmente en segmentos ejecutivo y premium — muestra una sensibilidad ambiental creciente. Estudios de comportamiento del consumidor en México indican que:

- El **67% de los viajeros frecuentes** considera relevante que la empresa de transporte tenga prácticas sostenibles documentadas.
- La **reducción de emisiones verificable** se está convirtiendo en un criterio de elección entre operadores, particularmente en rutas competidas.
- Las empresas que comunican activamente sus métricas ambientales generan mayor **lealtad de marca** en segmentos de ingreso medio-alto.

> **Para ADO:** Optimizar el consumo de combustible no es solo un ahorro operativo — es un argumento comercial y de posicionamiento de marca ante un segmento que valora la responsabilidad ambiental.

#### 👷 Justicia Social y Condiciones Laborales del Conductor

- **Dignidad laboral:** Cualquier sistema de monitoreo de conducción debe enmarcarse como herramienta de desarrollo profesional, no de vigilancia. La resistencia al cambio tecnológico identificada como pain point tiene raíces culturales profundas en este sector.
- **Equidad en la evaluación:** Los conductores perciben como injusto ser comparados sin considerar variables externas (tráfico, condición de la ruta, clima). Un sistema de IA que contextualice el desempeño genera mayor aceptación y legitimidad.
- **Impacto en comunidades locales:** ADO opera en regiones donde es uno de los principales empleadores. Sus decisiones operativas tienen efecto directo en el bienestar de comunidades enteras.

#### 📊 Cómo Estas Dinámicas Moldean las Decisiones de ADO

| Dimensión | Impacto en Prioridades Operativas |
|---|---|
| **Regulación ambiental** | Necesidad urgente de métricas de emisiones auditables |
| **Expectativa social de accesibilidad** | Eficiencia operativa como única vía para sostener tarifas competitivas |
| **Consumidor consciente** | Sostenibilidad como argumento de marca y fidelización |
| **Cultura laboral del conductor** | Adopción tecnológica requiere enfoque formativo, no punitivo |
| **Presión de márgenes** | Cada litro de combustible ahorrado tiene impacto social y financiero simultáneo |

#### 🔑 Síntesis Estratégica

Para Mobility ADO, la optimización de flota mediante IA no es únicamente una decisión tecnológica — es una **respuesta simultánea a presiones sociales, ambientales y económicas** que convergen en el mismo punto: la necesidad de medir, demostrar y mejorar lo que hoy opera en la opacidad. Un sistema autónomo de optimización no solo reduce costos; **legitima a ADO como operador responsable** ante reguladores, pasajeros, conductores y comunidades, en un entorno donde la sostenibilidad ya dejó de ser opcional.

---

### Competitive Context

**Panorama Competitivo: Optimización de Flotas con IA para Transporte de Pasajeros por Carretera — México**

#### 1. Contexto del Mercado

El sector de transporte terrestre de pasajeros en México opera en un entorno de márgenes ajustados, alta informalidad competitiva y creciente presión regulatoria. Empresas como ADO dominan el segmento formal de larga y media distancia, pero enfrentan una competencia fragmentada que va desde operadores regionales hasta plataformas digitales de movilidad. La digitalización operativa sigue siendo una ventaja diferencial no explotada por la mayoría de los actores del sector.

#### 2. Actores Competitivos Relevantes

##### Competidores Directos en Transporte

| Actor | Posición | Relevancia Competitiva |
|---|---|---|
| **ETN / Turistar** | Premium nacional | Compite en segmento ejecutivo/lujo; presión en diferenciación de servicio |
| **Flixbus México** | Disruptor digital | Modelo asset-light, fuerte en datos y experiencia digital del pasajero |
| **Grupo IAMSA** (Omnibus, Futura) | Masivo nacional | Escala operativa similar; rezago tecnológico comparable |
| **Operadores regionales informales** | Precio bajo | Presionan márgenes en rutas cortas sin cumplir estándares regulatorios |

##### Proveedores de Tecnología de Gestión de Flotas

| Proveedor | Oferta | Posición en el Mercado |
|---|---|---|
| **Samsara** | Telemática + IA conductores | Líder global con presencia creciente en México; fuerte en datos en tiempo real |
| **Geotab** | Plataforma telemática abierta | Referente en análisis de datos de flota; integrable con ERP |
| **Omnitracs (Solera)** | Gestión de flota + cumplimiento | Presencia consolidada en transporte de carga; expansión a pasajeros |
| **Webfleet (Bridgestone)** | Telemática + eficiencia de combustible | Orientado a flotas medianas; precio competitivo |
| **Soluciones locales (Tracklink, GPSGratis MX)** | Rastreo básico GPS | Bajo costo, funcionalidad limitada; muy adoptadas por operadores medianos |

##### Plataformas de IA y Cloud Relevantes

| Proveedor | Oferta | Diferenciador |
|---|---|---|
| **AWS / Amazon Bedrock AgentCore** | Agentes IA autónomos en nube | Capacidad de orquestación multi-agente; escalabilidad enterprise |
| **Google Cloud (Vertex AI)** | ML para operaciones | Fuerte en predicción y análisis de datos estructurados |
| **Microsoft Azure AI** | Copilot + ML integrado | Ecosistema familiar para empresas con infraestructura Microsoft |
| **IBM Maximo + Watson** | Mantenimiento predictivo industrial | Trayectoria en activos físicos; costo elevado de implementación |

#### 3. Dinámicas Competitivas que Moldean la Percepción de ADO

**🔴 Presión desde abajo: el costo como arma:** Los operadores informales y regionales compiten exclusivamente por precio, sin cargas regulatorias equivalentes. Esto obliga a ADO a justificar su diferencial de valor en servicio y confiabilidad, lo que hace que **cada punto porcentual de eficiencia operativa sea estratégicamente crítico**.

**🟡 Presión desde arriba: la digitalización como estándar emergente:** Flixbus y plataformas similares han establecido una expectativa de experiencia digital fluida. Aunque no compiten directamente en telemática operativa, **elevan el estándar de lo que significa ser una empresa de transporte moderna**, generando presión indirecta para que ADO modernice su back-office operativo.

**🟠 Proveedores de telemática: soluciones parciales sin inteligencia autónoma:** Las soluciones disponibles en el mercado (Samsara, Geotab, Omnitracs) ofrecen **visibilidad de datos pero no decisión autónoma**. Generan dashboards y alertas, pero requieren intervención humana para actuar. Esto crea una brecha entre el dato y la acción que un sistema de agentes IA como el propuesto puede cerrar directamente.

**🟢 AWS Bedrock AgentCore: ventaja de diferenciación real:** No existe en el mercado mexicano de transporte de pasajeros un caso documentado de uso de **agentes IA autónomos para optimización de flota en tiempo real**. Esto posiciona la solución propuesta como una apuesta de liderazgo tecnológico, no como una adopción tardía.

#### 4. Cómo el Panorama Competitivo Influye en las Decisiones de ADO

**Percepción del riesgo tecnológico:** ADO observa que sus competidores directos (IAMSA, ETN) **no han adoptado masivamente IA operativa**, lo que genera una percepción ambivalente: por un lado, reduce la urgencia percibida; por otro, abre una ventana de ventaja competitiva si se actúa primero. La decisión se convierte en una apuesta de timing estratégico.

**Expectativa de ROI demostrable antes de escalar:** Al ver que proveedores como Samsara o Geotab ofrecen pruebas piloto con métricas claras, ADO **espera el mismo estándar de evidencia** de cualquier solución nueva.

**Sensibilidad al discurso de "vigilancia":** La resistencia interna al cambio tecnológico se amplifica cuando los equipos operativos perciben que la tecnología es para **monitorear conductores**, no para apoyarlos.

**Presión regulatoria como acelerador de decisión:** La agenda ambiental del gobierno mexicano está creando un contexto donde **tener datos de emisiones ya no es opcional**.

**Costo de no actuar: visible y creciente:** Con el precio del diésel sujeto a volatilidad y los márgenes por viaje bajo presión constante, **cada mes sin optimización es un costo medible**.

#### 5. Conclusión Estratégica del Contexto Competitivo

> ADO opera en un mercado donde la tecnología de flotas está disponible pero fragmentada, donde nadie ha dado el salto a la autonomía decisional con IA, y donde la presión de costos, regulación y competencia digital converge en un punto de inflexión. La solución propuesta no compite contra otros sistemas de telemática: **compite contra la inercia operativa y el costo de seguir tomando decisiones sin inteligencia autónoma**. El que llegue primero a este modelo en el segmento formal de pasajeros en México definirá el nuevo estándar operativo del sector.

---

### Chat with the Customer

**Human**: Pretend you are a character named [My name is...]. The user will now have a conversation with you. Consider also the information from [Who is the customer?] [What do we want to solve?] [What are the pain points, needs, and wants?][Social Context] [Economic Context] [Technology Context] [Cultural Context] [Regulatory Context] [Professional Context] [Social and environmental consciousness] [Competitive Context] to answer the questions.

**Assistant**: Hi! My name is [My name is...]! I'd be happy to chat with you so you can help me solve my problem.

---

## Key Customer Characteristics - Summary

**10 Características Clave de Mobility ADO — Perfil del Cliente**

### 1. Operador de Infraestructura Social Crítica

No es un negocio convencional: gestiona movilidad esencial para millones de mexicanos. Las decisiones operativas tienen impacto social directo, lo que genera responsabilidad percibida más allá de la rentabilidad.

### 2. Márgenes Comprimidos y Presión de Costos Estructural

El combustible consume 35-45% del costo operativo total. Cada peso ahorrado en eficiencia es rentabilidad directa. La inversión tecnológica compite con necesidades operativas inmediatas y debe justificarse con ROI medible en 18-24 meses.

### 3. Cultura Corporativa Jerárquica con Resistencia Operativa

Las decisiones estratégicas se concentran en niveles directivos, pero la ejecución enfrenta resistencia activa de conductores y supervisores que perciben el monitoreo como vigilancia, no como apoyo.

### 4. Madurez Tecnológica Intermedia con Brecha Analítica

Posee infraestructura digital funcional (GPS, app, web, ERP básico), pero **no explota analíticamente los datos generados**. Las decisiones operativas aún se toman por experiencia empírica, no por inteligencia de datos.

### 5. Pragmatismo Operativo sobre Innovación Teórica

Adopta tecnología cuando resuelve un problema concreto e inmediato, no por tendencia. Desconfía de soluciones "caja negra" y exige evidencia práctica antes de comprometerse.

### 6. Presión Regulatoria Ambiental Creciente y Verificable

México avanza en compromisos climáticos que impactan directamente al transporte. ADO necesita datos estructurados de emisiones para cumplir auditorías, acceder a incentivos fiscales y anticiparse a regulaciones más estrictas.

### 7. Confianza Basada en Relaciones Personales, No en Transacciones

El cliente mexicano compra a quien se la vende. La credibilidad se construye con presencia cercana, acompañamiento post-venta y validación por figuras de autoridad reconocidas internamente.

### 8. Necesidad de Estabilidad Operativa sobre Disrupción

El riesgo de afectar el servicio durante implementación es inaceptable. Requiere soluciones que se integren gradualmente, generen victorias tempranas visibles y no amenacen la dinámica de equipos establecida.

### 9. Responsabilidad Laboral y Social con Conductores

El conductor es figura clave en la operación y en comunidades locales. Cualquier sistema de monitoreo debe enmarcarse como desarrollo profesional y equidad en la evaluación, no como control punitivo.

### 10. Demanda de Visibilidad y Control en Entorno de Alta Variabilidad

Opera en contexto de volatilidad constante (combustible, tráfico, comportamiento de conductores, regulación). Busca reducir incertidumbre mediante datos en tiempo real, pero sin complejidad que requiera capacitación extensa.

**Síntesis Estratégica:** Mobility ADO es un **operador pragmático, jerárquico y socialmente responsable** que opera bajo presión económica y regulatoria creciente. Compra soluciones que demuestren valor rápido, se integren sin disruption y generen legitimidad ante múltiples stakeholders.

---

## Key Customer Pain Points - Summary

**10 Puntos Críticos de Dolor — Mobility ADO**

### 1. Opacidad Total en Consumo de Combustible

Sin visibilidad granular sobre qué genera el consumo (conducción, ruta, unidad, clima), es imposible implementar controles efectivos. Cada litro no medido es rentabilidad perdida.

### 2. Márgenes Operativos Comprimidos sin Palancas de Control

Con presión inflacionaria constante en diésel y refacciones, la única variable controlable es la eficiencia interna, pero carece de herramientas para gestionarla sistemáticamente.

### 3. Mantenimiento Reactivo que Destruye Rentabilidad

Las fallas no anticipadas generan costos correctivos 3-5 veces mayores, pérdida de ingresos por unidad fuera de servicio y daño reputacional. Sin predictibilidad, el presupuesto de mantenimiento es un agujero negro.

### 4. Variabilidad Incontrolable entre Conductores

Consumos que varían hasta 40% entre conductores en la misma ruta revelan falta de estándares de conducción eficiente. Sin métricas claras, no hay base para entrenar ni evaluar desempeño.

### 5. Incapacidad de Demostrar Cumplimiento Ambiental

Sin datos verificables de emisiones, ADO no puede acreditar avances ante reguladores, acceder a incentivos fiscales o responder a presión de stakeholders sobre sostenibilidad.

### 6. Resistencia Interna al Cambio Tecnológico

Los equipos operativos perciben herramientas de monitoreo como vigilancia, no como apoyo. Esta resistencia retrasa adopción, degrada calidad de datos y limita captura de valor.

### 7. Ciclos de Decisión Largos por Falta de Evidencia Local

Sin casos de éxito propios o pilotos demostrables, los ciclos de aprobación se extienden indefinidamente. La cultura corporativa exige certeza antes de invertir, pero el tiempo corre.

### 8. Desconexión entre Datos Operativos y Decisiones Estratégicas

Existe infraestructura de GPS y telemetría, pero no se explota analíticamente. Los datos generados no se traducen en inteligencia accionable para optimizar rutas, flota o conductores.

### 9. Presión Regulatoria Creciente sin Preparación Estructural

Normas ambientales (NOM-044), compromisos climáticos y auditorías de eficiencia avanzan más rápido que la capacidad interna de ADO para documentar y demostrar cumplimiento.

### 10. ROI Incierto en Inversión Tecnológica

Sin métricas claras de retorno, la inversión en IA y telemática compite con necesidades operativas inmediatas. Se requiere demostración rápida de valor (4-8 semanas) para vencer la aversión al riesgo corporativo.

**Síntesis Ejecutiva:** Mobility ADO necesita una solución que **mida lo invisible, controle lo variable y demuestre lo intangible** — todo simultáneamente.

---

## What the Customer Wants to Solve? - Summary

**Definición del Problema — Mobility ADO**

**Mobility ADO necesita un sistema autónomo de optimización de flotas impulsado por IA que mida y controle el consumo de combustible, anticipe el mantenimiento de unidades, estandarice la conducción eficiente y genere evidencia regulatoria verificable de reducción de emisiones — todo con ROI demostrable en 18-24 meses, sin disruption operativa ni resistencia interna, para preservar márgenes en un entorno de presión económica y regulatoria creciente.**

---

## STEP 2 - DEFINE THE PROBLEM

### Today...

*"Hoy son operadores de infraestructura de movilidad social crítica, jerárquicos y pragmáticos, que gestionan operaciones de alto impacto bajo presión constante de costos y regulación, con capacidad tecnológica instalada pero sin explotación analítica real, y donde la confianza se construye desde las relaciones y el cambio solo se legitima cuando genera evidencia visible sin amenazar la estabilidad operativa."*

### ...have to...

*tienen que operar flotas enteras en la oscuridad, sin visibilidad sobre consumo de combustible, sin control sobre la variabilidad entre conductores, sin mantenimiento predictivo y sin datos accionables, mientras los márgenes se comprimen y cada decisión estratégica se retrasa por falta de evidencia verificable.*

### When...

*"Cuando quieren operar cada unidad de su flota con la precisión de un bisturí —sabiendo en tiempo real cuánto consume cada bus, qué conductor está quemando márgenes, qué motor fallará antes de que falle, y poder demostrarle al regulador, al directivo y al accionista que cada decisión operativa está respaldada por evidencia irrefutable— sin detener un solo viaje ni alterar la operación que ya sostienen."*

### HMW - How Might We...?

*¿Cómo podríamos transformar cada kilómetro recorrido por una flota de transporte masivo en inteligencia operativa que haga visible lo invisible —el consumo, el conductor, el motor, el margen— convirtiendo la incertidumbre diaria en la ventaja competitiva más difícil de replicar?*

---

## STEP 3 - INVENT THE SOLUTION

### Ideas Clusters

**Las 4 Ideas de Mayor Impacto para Mobility ADO**

---

#### 🥇 IDEA 1: Motor de Inteligencia de Combustible en Tiempo Real

*Hacer visible el mayor costo invisible de la operación*

El combustible es el dolor número uno. Un sistema embebido en cada unidad captura telemetría continua de consumo por kilómetro, conductor y ruta. Un modelo de **IA generativa** procesa los datos en lenguaje natural, convirtiendo patrones complejos de consumo en narrativas accionables. La capa de **IA agéntica** opera de forma autónoma: monitorea en tiempo real las variables que generan desviaciones —velocidad, % de pedal de aceleración, % de pedal de freno, RPM, marcha, consumo de combustible, odómetro— y activa alertas inmediatas cuando una unidad supera el umbral de eficiencia definido.

> *"El agente no solo detecta que el Bus 247 está consumiendo 18% por encima del estándar en la ruta México-Puebla. Identifica que la causa es aceleración brusca en los primeros 40 km, genera la alerta al supervisor correspondiente y registra el patrón para refinamiento futuro — todo en segundos."*

| Dolor | Cómo lo resuelve |
|---|---|
| Opacidad en consumo de combustible | Visibilidad granular por unidad, conductor y ruta en tiempo real |
| Márgenes sin palancas de control | Cada litro se convierte en una decisión accionable |
| Desconexión datos-decisiones | La IA traduce telemetría en recomendaciones operativas inmediatas |
| ROI incierto | Ahorro medible desde las primeras semanas de operación |

---

#### 🥈 IDEA 2: Mantenimiento Predictivo Basado en Señales de Motor

*Convertir el mantenimiento reactivo en una variable planificable*

Un módulo de **IA agéntica** analiza continuamente las señales de diagnóstico de cada unidad — temperatura, presión de aceite, % de pedal de freno, % pedal aceleración, códigos OBD — comparándolas contra patrones históricos de fallas registradas en toda la flota. El sistema no solo detecta anomalías: un modelo de **IA generativa** produce órdenes de trabajo preliminares en lenguaje técnico comprensible para los talleres.

> *"El sistema detecta que el motor del Bus 089 muestra un patrón de temperatura que en 23 casos históricos similares precedió una falla de bomba de agua en un promedio de 11 días. Genera la orden de trabajo preventiva, la envía al taller y notifica al supervisor de flota — antes de que el conductor note cualquier síntoma."*

| Dolor | Cómo lo resuelve |
|---|---|
| Mantenimiento reactivo que destruye rentabilidad | Anticipa fallas antes de que ocurran con precisión estadística |
| Márgenes comprimidos sin control | El presupuesto de mantenimiento se vuelve planificable y controlable |
| Desconexión datos-decisiones | Los talleres reciben diagnósticos preliminares, no unidades averiadas |
| ROI incierto | Reducción de costos correctivos y pérdida de ingresos por unidad fuera de servicio |

---

#### 🥉 IDEA 3: Perfil de Conducción Adaptativo por Conductor

*Eliminar la variabilidad incontrolable entre conductores con inteligencia, no con vigilancia*

Una capa de **IA generativa** construye el perfil de eficiencia individual de cada conductor a partir de sus patrones reales de aceleración, frenado, uso de motor y velocidad en cada ruta asignada. El modelo genera retroalimentación personalizada en lenguaje natural — no datos crudos — que el conductor recibe como recomendaciones de desarrollo profesional. El componente de **IA agéntica** evoluciona el índice de eficiencia de cada conductor en tiempo real, ajustando comparaciones para garantizar equidad.

> *"El sistema detecta que los 3 conductores más eficientes en la ruta Veracruz-CDMX comparten un patrón de desaceleración anticipada en los últimos 200 metros antes de cada parada. La IA genera un módulo de capacitación específico sobre esta técnica y lo recomienda a los 47 conductores que operan ese corredor."*

| Dolor | Cómo lo resuelve |
|---|---|
| Variabilidad incontrolable entre conductores | Métricas objetivas y comparaciones justas por condición equivalente |
| Resistencia interna al cambio tecnológico | Enmarcado como desarrollo profesional, no como vigilancia |
| Opacidad en consumo de combustible | Identifica qué conductores generan desviaciones y por qué |
| Ciclos de decisión largos | Base verificable para incentivos y capacitación sin subjetividad |

---

## STEP 4 - REFINE

### Press Release

---

**PRESS RELEASE — MOBILITY ADO**

## Mobility ADO Lanza Sistema Integrado de Inteligencia Operativa que Transforma Flotas de Transporte en Infraestructura Autónoma Optimizada

**Cuatro motores de IA generativa convierten datos operativos en decisiones en tiempo real, reduciendo consumo de combustible hasta 15%, anticipando fallas mecánicas y estandarizando conducción eficiente sin disruption operativa.**

**MÉXICO CITY — EXPANSIÓN — 15 DE MARZO DE 2026** — Mobility ADO, el operador de transporte terrestre de pasajeros más grande de México con presencia en 32 estados y más de 2,000 unidades en operación diaria, anunció hoy el lanzamiento de **ADO Intelligence Platform**, un sistema integrado de optimización operativa impulsado por inteligencia artificial generativa que convierte cada kilómetro recorrido en inteligencia accionable.

La plataforma integra cuatro motores autónomos de IA que operan simultáneamente:

1. **Motor de Inteligencia de Combustible en Tiempo Real** — proporciona visibilidad granular sobre el mayor costo operativo
2. **Sistema de Mantenimiento Predictivo** — anticipa fallas antes de que interrumpan el servicio
3. **Perfil de Conducción Adaptativo** — estandariza eficiencia sin vigilancia punitiva
4. **Motor de Optimización Dinámica de Rutas** — calibra frecuencias según demanda real

**Resultados del piloto de 90 días con 340 unidades:**

- Reducción del **12% en consumo de combustible** (equivalente a 2.8 millones de pesos mensuales en ahorro directo)
- Anticipó el **78% de fallas mecánicas** antes de su manifestación en ruta
- Redujo la variabilidad de consumo entre conductores del **18% al 7%** en corredores equivalentes
- Reducción de **2,400 toneladas de CO₂**

---

#### Oportunidad / Problema

Mobility ADO opera bajo una contradicción estructural que destruye rentabilidad silenciosamente: gestiona una flota de cientos de unidades bajo presión constante de márgenes comprimidos, pero toma decisiones operativas con información fragmentada, tardía o inexistente. El combustible consume entre 35% y 42% del costo operativo total, pero sin visibilidad granular sobre qué genera ese consumo, es imposible implementar controles efectivos.

#### Solución

ADO Intelligence Platform resuelve esta contradicción mediante cuatro motores de inteligencia artificial generativa que operan de forma integrada y autónoma. La plataforma se integra sobre la infraestructura GPS existente de ADO sin requerir reemplazo de hardware, generando ROI verificable en las primeras 8 semanas de operación.

#### Cita del Líder

*"Hemos operado esta flota durante décadas con la mejor intención y experiencia acumulada, pero sin visibilidad real sobre lo que estaba ocurriendo en cada unidad, cada ruta, cada día. ADO Intelligence Platform no reemplaza la experiencia de nuestros equipos — la amplifica. En 90 días de piloto, hemos visto reducciones de combustible que se traducen en millones de pesos mensuales, anticipación de fallas que protege la continuidad del servicio, y una transformación cultural donde los datos, no la intuición, guían nuestras decisiones."*

— **Carlos Mendoza, Director de Operaciones, Mobility ADO**

#### Testimonio del Cliente

*"Valentina Herrera, nuestra supervisora de flota en la terminal de Querétaro, comenzó a usar ADO Intelligence Platform. Lo primero que notó fue que por primera vez podía ver exactamente qué estaba ocurriendo en cada unidad sin tener que esperar reportes de fin de mes. Cuando el sistema anticipó una falla en el Bus 156 tres días antes de que ocurriera, programamos la reparación en una ventana de baja demanda, el taller tuvo tiempo de prepararse, y evitamos una cancelación que habría afectado a 45 pasajeros y habría costado tres veces más en reparación correctiva."*

— **Valentina Herrera, Supervisora de Flota, Terminal Querétaro, Mobility ADO**

#### Llamada a la Acción

Para conocer cómo ADO Intelligence Platform puede transformar la operación de tu flota de transporte, accede a [**www.adointelligence.mx**](http://www.adointelligence.mx).

---

### FAQ — Customer

**1. ¿ADO Intelligence Platform requiere reemplazar el hardware GPS o los sistemas de telemetría que ya tenemos instalados en nuestra flota?**

No. La plataforma fue diseñada específicamente para integrarse sobre la infraestructura GPS existente sin requerir reemplazo de hardware.

**2. ¿En cuánto tiempo podemos esperar ver un retorno real sobre la inversión?**

Según los resultados del piloto interno de 90 días con 340 unidades, el sistema genera ROI verificable en las primeras 8 semanas de operación. La reducción del 12% en consumo de combustible se tradujo en 2.8 millones de pesos mensuales en ahorro directo.

**3. ¿Qué tan confiable es el sistema de mantenimiento predictivo?**

En el piloto de 90 días, el sistema anticipó el 78% de las fallas mecánicas antes de que se manifestaran en ruta. Los benchmarks del sistema indican una capacidad de anticipación de entre 75% y 85% de fallas históricas.

**4. ¿Cómo reaccionarán nuestros conductores a ser monitoreados?**

El Perfil de Conducción Adaptativo no compara a los conductores en condiciones desiguales ni genera reportes punitivos. Construye una huella de eficiencia individual controlando por variables de contexto y entrega retroalimentación personalizada en lenguaje natural que el conductor recibe como coaching profesional.

**5. ¿Qué nivel de capacitación técnica necesitan nuestros supervisores y operadores?**

La plataforma fue diseñada para ser operada por equipos sin formación técnica especializada en análisis de datos. La IA generativa actúa como traductor permanente entre la complejidad técnica de los datos y la capacidad operativa de los equipos humanos.

**6. ¿La plataforma funciona para flotas más pequeñas o está diseñada exclusivamente para operadores del tamaño de ADO?**

La arquitectura de la plataforma es escalable y se adapta al tamaño de la flota. Los cuatro motores de IA operan con la misma efectividad en flotas más pequeñas.

**7. ¿Cómo funciona exactamente el Motor de Optimización Dinámica de Rutas?**

El motor lee en tiempo real las señales de demanda de pasajeros y anticipa patrones de ocupación con un horizonte de 72 horas. Utiliza datos históricos de ocupación, eventos de lista de espera, frecuencias actuales y disponibilidad de unidades para recomendar ajustes precisos.

**8. ¿Qué sucede con la privacidad y seguridad de los datos operativos de nuestra flota?**

La plataforma opera bajo protocolos de seguridad de datos que garantizan que la información de telemetría, rutas, conductores y patrones operativos permanece bajo control exclusivo de tu organización.

**9. ¿Cuánto tiempo toma la implementación completa del sistema sin afectar la operación diaria?**

La plataforma fue diseñada explícitamente para implementarse sin disruption operativa, aprovechando la infraestructura GPS existente como base de integración.

**10. ¿Los ahorros en combustible del 12% son garantizados o son proyecciones?**

El 12% de reducción en consumo de combustible es un resultado verificado del piloto interno de 90 días con 340 unidades reales en operación, no una proyección teórica. Los benchmarks del sistema indican un rango de reducción de entre 8% y 15%.

**11. ¿Cómo ayuda la plataforma a cumplir con los compromisos de reducción de emisiones?**

La plataforma genera datos verificables de reducción de emisiones de CO₂ como consecuencia directa de la optimización operativa. En el piloto de 90 días, se documentó una reducción de 2,400 toneladas de CO₂ — datos estructurados, trazables y auditables.

**12. ¿Qué ocurre si el sistema genera una alerta de mantenimiento predictivo incorrecta?**

El sistema genera órdenes de trabajo preliminares con diagnóstico contextualizado, no órdenes de retiro inmediato de unidades. Cada alerta pasa por la validación del equipo técnico de taller antes de convertirse en una intervención.

**13. ¿La plataforma puede integrarse con nuestros sistemas de gestión de flota, ERP o software de boletaje existentes?**

La plataforma fue diseñada con capacidad de integración sobre infraestructura existente como principio central de su arquitectura.

**14. ¿Cómo se diferencia ADO Intelligence Platform de otros sistemas de monitoreo de flota?**

La diferencia central está en la capa de inteligencia artificial generativa. Los sistemas de monitoreo tradicionales capturan y presentan datos. ADO Intelligence Platform interpreta esos datos, identifica patrones complejos, genera narrativas operativas en lenguaje natural y recomienda acciones específicas.

**15. ¿Existe alguna demostración o período de prueba disponible?**

Sí. En [www.adointelligence.mx](http://www.adointelligence.mx) están disponibles demostraciones interactivas del sistema y la posibilidad de agendar una sesión de consultoría personalizada.

---

### FAQ — Internal

1. ¿Cuál es el modelo de negocio de ADO Intelligence Platform — es una licencia de software, un servicio por suscripción o un esquema de pago por resultados vinculado a los ahorros generados?
2. ¿Qué tan replicables son los resultados del piloto de 90 días con 340 unidades cuando se escale a la totalidad de la flota de más de 2,000 unidades en operación simultánea?
3. ¿Cuál es el costo total de implementación considerando integración, capacitación, soporte y mantenimiento de la plataforma, y en qué plazo se recupera esa inversión?
4. ¿Qué nivel de dependencia tecnológica genera esta plataforma con el proveedor, y qué ocurre con la continuidad operativa si la relación comercial se interrumpe?
5. ¿Cómo se garantiza la propiedad, confidencialidad y seguridad de los datos operativos de ADO que procesa la plataforma?
6. ¿Cuál es la estrategia de gestión del cambio para los conductores y supervisores que podrían percibir la plataforma como una herramienta de vigilancia?
7. ¿Los resultados presentados en el piloto fueron auditados por un tercero independiente?
8. ¿Qué infraestructura tecnológica mínima requiere la plataforma más allá del GPS existente?
9. ¿Cómo se comporta la plataforma en condiciones de conectividad limitada o intermitente, que son frecuentes en varios de los 32 estados donde opera ADO?
10. ¿Existe algún riesgo regulatorio o laboral asociado al uso de los datos de desempeño individual de conductores?
11. ¿Cuál es el plan de contingencia si los algoritmos de mantenimiento predictivo generan falsos positivos o falsos negativos a escala?
12. ¿Qué ventaja competitiva sostenible genera esta plataforma si la misma tecnología está disponible para otros operadores de transporte?
13. ¿Cuál es la hoja de ruta de evolución del producto en los próximos 24 a 36 meses?
14. ¿Cómo se integra ADO Intelligence Platform con los sistemas ERP, de nómina, de gestión de taller y de atención al cliente que ADO ya opera?
15. ¿Cuál es el impacto proyectado de esta plataforma sobre la estructura de personal operativo y de supervisión a mediano plazo?
