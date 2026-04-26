# Requirements Document

## Introduction

This document defines the requirements for the 9 AWS Lambda functions that power the ADO MobilityIA MVP — a fleet optimization platform for Mobility ADO's hackathon project (AWS Builders League 2026). The system ingests simulated SPN-based telemetry from S3, pivots it into consolidated bus state in DynamoDB, and exposes tool functions for two Bedrock AgentCore agents (Fuel Intelligence and Predictive Maintenance) plus a dashboard API. All data is simulated (C-004), responses use fuzzy language without specific numeric metrics (C-003), and scope is limited to a 5-day hackathon MVP (C-001).

## Glossary

- **Simulator**: The `ado-simulador-telemetria` Lambda function that reads simulated telemetry from S3, pivots SPN records, and writes consolidated bus state to DynamoDB
- **SPN**: Suspect Parameter Number — a standardized identifier for each vehicle sensor variable (e.g., SPN 84 = Vehicle Speed, SPN 190 = RPM). The project uses a catalog of 36 confirmed SPNs
- **SPN_Catalog**: The `motor_spn` reference dataset containing 36 SPN definitions with id, name, unit, minimo, maximo, delta, and variable_tipo fields. Loaded from S3 at `catalogo/motor_spn.json`
- **Telemetry_Pivot**: The process of transforming multiple per-SPN telemetry records (one row per sensor reading) into a single consolidated bus state object with flat fields and a `spn_valores` map
- **DynamoDB_Telemetria**: The `ado-telemetria-live` DynamoDB table with PK `autobus` (S) and SK `timestamp` (S), storing consolidated bus state with TTL of 24 hours
- **DynamoDB_Alertas**: The `ado-alertas` DynamoDB table with PK `alerta_id` (S) and SK `timestamp` (S), storing maintenance recommendations and alerts
- **Fuel_Agent_Tool**: A Lambda function invoked as an Action Group tool by the Bedrock AgentCore Fuel Intelligence Agent (`ado-agente-combustible`)
- **Maintenance_Agent_Tool**: A Lambda function invoked as an Action Group tool by the Bedrock AgentCore Predictive Maintenance Agent (`ado-agente-mantenimiento`)
- **Dashboard_API**: The `ado-dashboard-api` Lambda function serving consolidated fleet data through API Gateway for QuickSight or Streamlit
- **Common_Layer**: The `ado-common-layer` Lambda layer containing shared modules: `spn_catalog.py`, `telemetry_pivot.py`, `dynamo_utils.py`, `s3_utils.py`, `constants.py`, `response.py`
- **Data_Fault**: The `data_fault` dataset in S3 containing simulated fault history with fields including codigo, severidad, modelo, marca_comercial, zona, region, and descripcion
- **Consumption_State**: A classification of fuel efficiency for a bus: `EFICIENTE`, `ALERTA_MODERADA`, or `ALERTA_SIGNIFICATIVA`, derived from SPN 185 (Rendimiento km/L) or SPN 183 (Tasa de combustible L/h)
- **Risk_Level**: A qualitative classification of mechanical event risk: `BAJO`, `MODERADO`, `ELEVADO`, or `CRITICO`, expressed without numeric probabilities per constraint C-003
- **SageMaker_Endpoint**: The `ado-prediccion-eventos` SageMaker endpoint for ML-based event prediction, with a heuristic fallback when unavailable
- **Autobus**: The bus economic number (bigint) used as the primary key in DynamoDB_Telemetria, sourced from the `autobus` field in telemetry-data

## Requirements

### Requirement 1: Shared Lambda Layer

**User Story:** As a developer, I want a shared Lambda layer with common utilities, so that all 9 Lambda functions reuse the same SPN catalog logic, DynamoDB helpers, S3 helpers, and response formatting without code duplication.

#### Acceptance Criteria

1. THE Common_Layer SHALL include the modules `spn_catalog.py`, `telemetry_pivot.py`, `dynamo_utils.py`, `s3_utils.py`, `constants.py`, and `response.py`
2. THE `spn_catalog.py` module SHALL load the SPN_Catalog from S3 and cache it in memory using `lru_cache` across warm Lambda invocations
3. THE `spn_catalog.py` module SHALL expose a function to check whether a given SPN value is outside the `minimo`/`maximo` range defined in the SPN_Catalog
4. THE `spn_catalog.py` module SHALL expose a function to detect anomalous variation between two consecutive SPN readings using the `delta` field from the SPN_Catalog with a threshold of 2x the expected delta
5. THE `spn_catalog.py` module SHALL define constant sets `SPNS_COMBUSTIBLE`, `SPNS_MANTENIMIENTO`, and `SPNS_DEMO_PRIORITARIOS` grouping the 36 confirmed SPN IDs by functional classification
6. THE `telemetry_pivot.py` module SHALL transform a list of per-SPN telemetry records into a consolidated bus state dict containing flat fields (e.g., `velocidad_kmh`, `rpm`), a `spn_valores` map, an `alertas_spn` list, and trip context fields (autobus, viaje_id, operador_cve, operador_desc, viaje_ruta, viaje_ruta_origen, viaje_ruta_destino, latitud, longitud)
7. THE `telemetry_pivot.py` module SHALL map each SPN ID to a short field name using the `SPN_NOMBRE_CORTO` dictionary for flat DynamoDB attributes
8. THE `response.py` module SHALL provide a standard response format compatible with Bedrock AgentCore Action Group invocations
9. FOR ALL valid SPN_Catalog entries, loading then querying by SPN ID SHALL return the original entry with name, unidad, minimo, maximo, delta, and variable_tipo fields (round-trip property)

### Requirement 2: Telemetry Simulator Lambda

**User Story:** As a platform operator, I want a Lambda that simulates real-time telemetry ingestion, so that DynamoDB always has fresh consolidated bus state for the agents and dashboard to query during the demo.

#### Acceptance Criteria

1. WHEN triggered by EventBridge Scheduler at a 10-second interval, THE Simulator SHALL read simulated telemetry records from S3 at prefix `telemetria-simulada/` for up to 20 buses
2. WHEN processing telemetry records for a bus, THE Simulator SHALL group records by Autobus and temporal window, then pivot the per-SPN records into a consolidated bus state using the Telemetry_Pivot module and the SPN_Catalog
3. WHEN pivoting SPN records, THE Simulator SHALL verify each SPN value against the `minimo`/`maximo` range from the SPN_Catalog and populate the `alertas_spn` list with any out-of-range SPNs
4. WHEN writing to DynamoDB_Telemetria, THE Simulator SHALL include both flat fields (velocidad_kmh, rpm, temperatura_motor_c, etc.) for direct queries and the full `spn_valores` map for detailed agent analysis
5. WHEN computing the Consumption_State, THE Simulator SHALL use SPN 185 (Rendimiento km/L) as the primary metric with fallback to SPN 183 (Tasa de combustible L/h) when rendimiento is unavailable
6. THE Simulator SHALL use a stateless offset calculation `(int(time.time()) // 10 + bus_index) % total_records` to cycle through S3 records without maintaining external state
7. THE Simulator SHALL write all bus states using `batch_write_item` with a TTL of 24 hours (86400 seconds added to current Unix timestamp)
8. THE Simulator SHALL use concurrency of 1 to avoid duplicate writes from parallel invocations
9. IF the SPN_Catalog fails to load from S3, THEN THE Simulator SHALL log the error in JSON structured format and skip the current invocation without crashing
10. IF S3 telemetry data is unavailable for a bus, THEN THE Simulator SHALL skip that bus and continue processing the remaining buses

### Requirement 3: Query Telemetry Tool

**User Story:** As the Fuel Intelligence Agent, I want a tool that retrieves the latest consolidated telemetry for a bus, so that I can analyze current driving patterns and fuel consumption.

#### Acceptance Criteria

1. WHEN invoked by Bedrock AgentCore with an `autobus` parameter, THE Fuel_Agent_Tool `tool-consultar-telemetria` SHALL query DynamoDB_Telemetria for the most recent N records (default 10, maximum 50) sorted by timestamp descending
2. WHEN returning results, THE Fuel_Agent_Tool SHALL translate each SPN ID in `spn_valores` to its human-readable name and unit using the SPN_Catalog
3. WHEN returning results, THE Fuel_Agent_Tool SHALL include for each SPN variable: the SPN ID, name, current value, unit, catalog range (minimo-maximo), and an out-of-range status indicator
4. THE Fuel_Agent_Tool SHALL include trip context in the response: viaje_ruta, viaje_ruta_origen, viaje_ruta_destino, and operador information
5. THE Fuel_Agent_Tool SHALL include a `historial_reciente` array summarizing each record's timestamp, estado_consumo, rendimiento_kml, and count of out-of-range SPNs
6. IF no records are found for the given Autobus, THEN THE Fuel_Agent_Tool SHALL return a response indicating no telemetry data is available for that bus

### Requirement 4: Deviation Calculation Tool

**User Story:** As the Fuel Intelligence Agent, I want a tool that calculates fuel consumption deviation and identifies probable causes, so that I can generate actionable recommendations for fleet supervisors.

#### Acceptance Criteria

1. WHEN invoked with `autobus` and `viaje_ruta` parameters, THE Fuel_Agent_Tool `tool-calcular-desviacion` SHALL query the last 10 records from DynamoDB_Telemetria and compute average values for fuel efficiency SPNs (185 Rendimiento, 183 Tasa de combustible, 184 Ahorro instantáneo)
2. THE Fuel_Agent_Tool SHALL classify deviation into categories: `DENTRO_DE_RANGO` (rendimiento >= 3.0 km/L), `DESVIACION_LEVE` (2.5-3.0), `DESVIACION_MODERADA` (2.0-2.5), or `DESVIACION_SIGNIFICATIVA` (< 2.0)
3. WHEN a deviation is detected, THE Fuel_Agent_Tool SHALL analyze correlated SPNs to identify probable causes: SPN 190 RPM average above 2200, SPN 91 accelerator average above 65%, SPN 84 speed average above 100 km/h, SPN 521 brake average above 25%, SPN 513 torque average above 75%, SPN 523 frequent gear changes, and SPN 527/596 cruise control not active
4. THE Fuel_Agent_Tool SHALL return each probable cause with the SPN ID, name, finding description, average value, unit, and catalog range
5. IF no records are found for the given Autobus, THEN THE Fuel_Agent_Tool SHALL return a response indicating insufficient data for deviation analysis

### Requirement 5: Active Buses Listing Tool

**User Story:** As the Fuel Intelligence Agent, I want a tool that lists all buses with recent telemetry, so that I can identify which buses are currently active and prioritize those with alerts.

#### Acceptance Criteria

1. WHEN invoked, THE Fuel_Agent_Tool `tool-listar-buses-activos` SHALL return all buses with telemetry records in DynamoDB_Telemetria from the last 5 minutes
2. WHERE a `viaje_ruta` filter is provided, THE Fuel_Agent_Tool SHALL query the GSI `viaje_ruta-timestamp-index` to filter by route
3. WHILE no `viaje_ruta` filter is provided, THE Fuel_Agent_Tool SHALL perform a Scan with a FilterExpression on timestamp (acceptable for approximately 20 buses in MVP scope)
4. THE Fuel_Agent_Tool SHALL return each bus with: autobus, viaje_ruta, operador name, ultimo_timestamp, estado_consumo, count of out-of-range SPNs, and a summary of active alerts
5. THE Fuel_Agent_Tool SHALL sort results by severity: `ALERTA_SIGNIFICATIVA` first, then by count of out-of-range SPNs descending

### Requirement 6: OBD Diagnostic Query Tool

**User Story:** As the Predictive Maintenance Agent, I want a tool that retrieves mechanical diagnostic signals and recent fault history for a bus, so that I can assess its mechanical health.

#### Acceptance Criteria

1. WHEN invoked with an `autobus` parameter, THE Maintenance_Agent_Tool `tool-consultar-obd` SHALL query the last 20 records from DynamoDB_Telemetria and extract maintenance-relevant SPNs defined in `SPNS_MANTENIMIENTO` (temperature, pressure, oil levels, coolant, battery voltage, retarder, odometer, engine hours, urea level, and 6 brake pad SPNs)
2. THE Maintenance_Agent_Tool SHALL calculate trends for each maintenance SPN by comparing the first half versus the second half of the 20 records, classifying each as `estable`, `ascendente`, or `descendente`
3. THE Maintenance_Agent_Tool SHALL detect anomalous variations between consecutive readings using the `delta` field from the SPN_Catalog (threshold: 2x delta)
4. THE Maintenance_Agent_Tool SHALL return brake pad status for all 6 positions (SPNs 1099-1104) with percentage remaining and a status classification: `aceptable` (>= 30%), `REQUIERE_ATENCION` (< 30%)
5. WHEN querying fault history, THE Maintenance_Agent_Tool SHALL read the Data_Fault dataset from S3, filter by the given Autobus, and return the 5 most recent faults including codigo, severidad, descripcion, modelo, marca_comercial, and zona
6. THE Maintenance_Agent_Tool SHALL return a `resumen_salud` text summarizing the overall mechanical health of the bus based on all signals, trends, brake pad status, and recent faults

### Requirement 7: Event Prediction Tool

**User Story:** As the Predictive Maintenance Agent, I want a tool that predicts the risk of a mechanical event for a bus, so that I can recommend preventive interventions before failures occur.

#### Acceptance Criteria

1. WHEN invoked with an `autobus` parameter, THE Maintenance_Agent_Tool `tool-predecir-evento` SHALL query the last 20 records from DynamoDB_Telemetria and build a feature vector from maintenance SPNs (averages, maximums, minimums, count of out-of-range SPNs, and recent fault count)
2. THE Maintenance_Agent_Tool SHALL attempt to invoke the SageMaker_Endpoint `ado-prediccion-eventos` with the feature vector for ML-based prediction
3. IF the SageMaker_Endpoint is unavailable or returns an error, THEN THE Maintenance_Agent_Tool SHALL fall back to a heuristic scoring algorithm that evaluates maintenance SPNs against catalog ranges and recent faults from Data_Fault
4. THE heuristic fallback SHALL evaluate: SPN 110 temperature motor (score +3 if avg > 120°C, +2 if max > 140°C), SPN 175 oil temperature (+2 if avg > 130°C), SPN 100 oil pressure (+3 if min < 150 kPa, +1 if avg < 250 kPa), SPN 98 oil level (+2 if avg < 30%), SPN 111 coolant (+2 if avg < 40%), SPN 168 battery voltage (+1 if min < 22V), SPN 1761 urea (+1 if avg < 15%), brake pad SPNs (+2 if avg < 15%, +1 if avg < 30%), and recent fault severity as direct score addition
5. THE Maintenance_Agent_Tool SHALL classify the Risk_Level as: `BAJO` (score <= 2), `MODERADO` (score 3-5), `ELEVADO` (score 6-8), or `CRITICO` (score > 8), with corresponding urgency: `PROXIMO_SERVICIO`, `PROXIMO_SERVICIO`, `ESTA_SEMANA`, or `INMEDIATA`
6. THE Maintenance_Agent_Tool SHALL return the risk level, description, urgency, list of contributing factors, and list of at-risk components (sistema_refrigeracion, bomba_agua, circuito_aceite, sistema_frenos, sistema_electrico, sistema_escape)
7. THE Maintenance_Agent_Tool SHALL indicate whether the prediction used the ML model or the heuristic fallback via a `metodo_prediccion` field

### Requirement 8: Historical Pattern Search Tool

**User Story:** As the Predictive Maintenance Agent, I want a tool that searches historical fault data for similar patterns, so that I can contextualize current signals with past events by model, brand, and zone.

#### Acceptance Criteria

1. WHEN invoked with a `codigo` parameter, THE Maintenance_Agent_Tool `tool-buscar-patrones-historicos` SHALL read the Data_Fault dataset from S3 and filter faults matching the given fault code (exact or partial match)
2. WHERE `modelo` and `marca_comercial` parameters are provided, THE Maintenance_Agent_Tool SHALL prioritize matching faults from the same bus model and brand without excluding other results
3. THE Maintenance_Agent_Tool SHALL return the top 10 most recent matching events sorted by fecha_hora descending
4. THE Maintenance_Agent_Tool SHALL compute pattern statistics: average severity, most affected models, most affected zones/regions, average event duration (fecha_hora_fin minus fecha_hora), and affected service types
5. THE Maintenance_Agent_Tool SHALL return each matching event with: id, autobus, fecha_hora, codigo, severidad, descripcion, modelo, marca_comercial, zona, region, servicio, and computed duration
6. IF no matching faults are found for the given code, THEN THE Maintenance_Agent_Tool SHALL return a response indicating no historical patterns were found

### Requirement 9: Recommendation Generation Tool

**User Story:** As the Predictive Maintenance Agent, I want a tool that creates preventive maintenance recommendations in DynamoDB, so that work orders are tracked and visible in the dashboard.

#### Acceptance Criteria

1. WHEN invoked with autobus, diagnostico, nivel_riesgo, urgencia, and componentes parameters, THE Maintenance_Agent_Tool `tool-generar-recomendacion` SHALL create a new record in DynamoDB_Alertas
2. THE Maintenance_Agent_Tool SHALL generate a unique `alerta_id` using UUID v4 and a `numero_referencia` in the format `OT-{YYYY}-{MMDD}-{autobus}`
3. THE Maintenance_Agent_Tool SHALL set `tipo_alerta` to `MANTENIMIENTO`, `estado` to `ACTIVA`, and `agente_origen` to `ado-agente-mantenimiento`
4. THE Maintenance_Agent_Tool SHALL enrich the alert with bus context (viaje_ruta, operador_desc) by performing a quick query to DynamoDB_Telemetria for the latest record of the given Autobus
5. THE Maintenance_Agent_Tool SHALL return a confirmation with the alerta_id, numero_referencia, autobus, nivel_riesgo, urgencia, and a human-readable success message
6. IF the DynamoDB write fails, THEN THE Maintenance_Agent_Tool SHALL return an error response with a descriptive message and log the error in JSON structured format

### Requirement 10: Dashboard API Lambda

**User Story:** As a dashboard consumer (QuickSight or Streamlit), I want an API that serves consolidated fleet status, active alerts, consumption summaries, and CO₂ estimates, so that the jury can see the platform's value in real time.

#### Acceptance Criteria

1. WHEN a GET request is received at `/dashboard/flota-status`, THE Dashboard_API SHALL return the current state of all buses including: total buses, active buses count, summary by Consumption_State, and a list of buses with autobus, viaje_ruta, origin, destination, operador, estado_consumo, count of out-of-range SPNs, and last update timestamp
2. WHEN a GET request is received at `/dashboard/alertas-activas`, THE Dashboard_API SHALL query DynamoDB_Alertas for records with `estado` equal to `ACTIVA` and return them sorted by urgency (INMEDIATA first)
3. WHEN a GET request is received at `/dashboard/resumen-consumo`, THE Dashboard_API SHALL aggregate consumption data by viaje_ruta and return efficiency summaries per route
4. WHEN a GET request is received at `/dashboard/co2-estimado`, THE Dashboard_API SHALL return estimated CO₂ reduction metrics using fuzzy language descriptions without specific numeric values, consistent with constraint C-003
5. THE Dashboard_API SHALL translate SPN IDs to human-readable names using the SPN_Catalog for all responses that include SPN data
6. IF DynamoDB queries fail, THEN THE Dashboard_API SHALL return an appropriate HTTP error status code with a descriptive error message

### Requirement 11: Cross-Cutting Constraints

**User Story:** As a developer, I want all Lambda functions to follow consistent conventions, so that the codebase is maintainable and the demo runs reliably within the hackathon timeframe.

#### Acceptance Criteria

1. THE Common_Layer SHALL be compatible with Python 3.12 runtime in the `us-east-1` region
2. THE Simulator SHALL be configured with 512 MB memory and 30-second timeout; all Fuel_Agent_Tool and Maintenance_Agent_Tool functions SHALL be configured with 256 MB memory and 10-second timeout, except `tool-predecir-evento` (256 MB, 30s) and `tool-buscar-patrones-historicos` (512 MB, 30s)
3. WHEN any Lambda function logs an event, THE function SHALL use JSON structured format for CloudWatch compatibility
4. WHEN any Fuel_Agent_Tool or Maintenance_Agent_Tool returns a response, THE response SHALL use the standard format from the `response.py` module compatible with Bedrock AgentCore Action Group invocations
5. THE Simulator SHALL use environment variables for configuration: `DYNAMODB_TABLE`, `S3_BUCKET`, `S3_TELEMETRIA_PREFIX`, `S3_CATALOGO_KEY`, and `NUM_BUSES`
6. WHEN any Lambda function accesses DynamoDB_Telemetria, THE function SHALL use the table name from the `DYNAMODB_TABLE_TELEMETRIA` environment variable (value: `ado-telemetria-live`)
7. WHEN any Lambda function accesses DynamoDB_Alertas, THE function SHALL use the table name from the `DYNAMODB_TABLE_ALERTAS` environment variable (value: `ado-alertas`)
