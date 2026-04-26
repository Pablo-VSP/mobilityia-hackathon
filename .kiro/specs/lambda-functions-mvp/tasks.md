# Implementation Plan: Lambda Functions MVP

## Overview

Implement the 9 AWS Lambda functions and shared layer for the ADO MobilityIA fleet optimization platform. The implementation follows the design's 4-group structure: Common Layer first, then Simulator, Fuel Agent Tools, Maintenance Agent Tools, and Dashboard API. Each task builds incrementally so that downstream Lambdas can use the shared layer and the simulator populates DynamoDB before the agent tools query it.

## Tasks

- [x] 1. Create project structure and shared Lambda layer
  - [x] 1.1 Create directory structure and layer scaffolding
    - Create the `lambda-functions/` root directory with all 9 Lambda subdirectories and the `layers/ado-common/python/ado_common/` package structure
    - Create `__init__.py` for the `ado_common` package
    - _Requirements: 1.1_

  - [x] 1.2 Implement `constants.py` with SPN ID constants and functional groupings
    - Define all 36 SPN ID constants (SPN_VELOCIDAD=84, SPN_RPM=190, etc.)
    - Define `SPNS_COMBUSTIBLE` (15 IDs), `SPNS_MANTENIMIENTO` (19 IDs), and `SPNS_DEMO_PRIORITARIOS` (21 IDs) sets
    - _Requirements: 1.5_

  - [x] 1.3 Implement `spn_catalog.py` — SPN catalog loader and validation functions
    - Implement `cargar_catalogo_spn(bucket, key)` with `lru_cache` for cross-invocation caching
    - Implement `obtener_spn(catalogo, spn_id)` for single SPN lookup returning name, unidad, minimo, maximo, delta, variable_tipo
    - Implement `valor_fuera_de_rango(catalogo, spn_id, valor)` checking against minimo/maximo from catalog
    - Implement `variacion_anomala(catalogo, spn_id, valor_anterior, valor_actual)` using 2x delta threshold
    - _Requirements: 1.2, 1.3, 1.4, 1.9_

  - [x] 1.4 Implement `telemetry_pivot.py` — SPN record pivot to consolidated bus state
    - Define `SPN_NOMBRE_CORTO` dictionary mapping all 28 SPN IDs to short field names (84→"velocidad_kmh", 190→"rpm", etc.)
    - Implement `pivotar_telemetria(registros, catalogo_spn, solo_prioritarios=True)` that transforms per-SPN records into consolidated dict with flat fields, `spn_valores` map, `alertas_spn` list, and trip context (autobus, viaje_id, operador_cve, operador_desc, viaje_ruta, viaje_ruta_origen, viaje_ruta_destino, latitud, longitud)
    - _Requirements: 1.6, 1.7_

  - [x] 1.5 Implement `dynamo_utils.py` — DynamoDB query and write helpers
    - Implement `query_latest_records(table_name, autobus, limit=10)` with ScanIndexForward=False
    - Implement `batch_write_items(table_name, items)` with retry on unprocessed items
    - Implement `put_item(table_name, item)`
    - Implement `scan_recent(table_name, timestamp_limit)` with FilterExpression on timestamp
    - Implement `query_gsi(table_name, index_name, pk_value, sk_condition)` for GSI queries
    - _Requirements: 1.1_

  - [x] 1.6 Implement `s3_utils.py` — S3 read helpers
    - Implement `read_json_from_s3(bucket, key)` for JSON files
    - Implement `read_parquet_from_s3(bucket, key)` with fallback to JSON if pandas unavailable
    - Implement `list_objects(bucket, prefix)` for listing S3 keys
    - _Requirements: 1.1_

  - [x] 1.7 Implement `response.py` — Standard response formatting
    - Implement `build_agent_response(body, status="success")` compatible with Bedrock AgentCore Action Group format
    - Implement `build_error_response(message, status_code=500)` for error responses
    - Implement `build_api_response(body, status_code=200)` with CORS headers for API Gateway
    - _Requirements: 1.8, 11.4_

- [x] 2. Checkpoint — Verify shared layer
  - Ensure all layer modules are complete and internally consistent, ask the user if questions arise.

- [x] 3. Implement Telemetry Simulator Lambda (`ado-simulador-telemetria`)
  - [x] 3.1 Implement `clasificar_consumo(spn_valores)` helper function
    - SPN 185 (Rendimiento km/L): ≥3.0→EFICIENTE, 2.0–3.0→ALERTA_MODERADA, <2.0→ALERTA_SIGNIFICATIVA
    - Fallback to SPN 183 (Tasa combustible L/h): ≤30→EFICIENTE, 30–50→ALERTA_MODERADA, >50→ALERTA_SIGNIFICATIVA
    - Return `SIN_DATOS` if neither SPN available
    - _Requirements: 2.5_

  - [x] 3.2 Implement main `lambda_handler` for the simulator
    - Load SPN catalog from S3 using `cargar_catalogo_spn()` (cached via lru_cache)
    - Read `NUM_BUSES`, `S3_BUCKET`, `S3_TELEMETRIA_PREFIX`, `S3_CATALOGO_KEY`, `DYNAMODB_TABLE` from environment variables
    - For each of 20 buses: compute stateless offset `(int(time.time()) // 10 + bus_index) % total_records`, read telemetry block from S3, group by temporal window (~30s), call `pivotar_telemetria()`, compute `estado_consumo` via `clasificar_consumo()`, set `ttl_expiry` = now + 86400
    - Write all 20 bus states via `batch_write_items()` to DynamoDB
    - Handle SPN catalog load failure: log error in JSON structured format, skip invocation without crashing
    - Handle missing S3 telemetry for a bus: skip that bus, continue with remaining
    - Log summary in JSON structured format
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8, 2.9, 2.10, 11.3, 11.5_

  - [x] 3.3 Write unit tests for the simulator
    - Test `clasificar_consumo` with all classification thresholds and SIN_DATOS fallback
    - Test stateless offset calculation produces expected cycling behavior
    - Test error handling when catalog fails to load
    - Test error handling when S3 telemetry is unavailable for a bus
    - _Requirements: 2.5, 2.6, 2.9, 2.10_

- [x] 4. Checkpoint — Verify simulator
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Fuel Agent Tools (3 Lambdas)
  - [x] 5.1 Implement `tool-consultar-telemetria` Lambda
    - Parse `autobus` and optional `ultimos_n_registros` (default 10, max 50) from Bedrock AgentCore event
    - Query DynamoDB for latest N records using `query_latest_records()`
    - For each record, translate `spn_valores` entries to human-readable names using SPN catalog
    - Build `variables_actuales` array with SPN ID, name, value, unit, catalog range (minimo-maximo), and out-of-range status
    - Build `historial_reciente` array with timestamp, estado_consumo, rendimiento_kml, and count of out-of-range SPNs
    - Include trip context: viaje_ruta, viaje_ruta_origen, viaje_ruta_destino, operador info
    - Return empty-data response if no records found for the given autobus
    - Use `build_agent_response()` for response formatting
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.4, 11.6_

  - [x] 5.2 Implement `tool-calcular-desviacion` Lambda
    - Parse `autobus` and `viaje_ruta` from Bedrock AgentCore event
    - Query last 10 records from DynamoDB, compute averages for SPNs 185, 183, 184
    - Classify deviation: DENTRO_DE_RANGO (≥3.0), DESVIACION_LEVE (2.5–3.0), DESVIACION_MODERADA (2.0–2.5), DESVIACION_SIGNIFICATIVA (<2.0)
    - Analyze correlated SPNs for probable causes: SPN 190 avg>2200 rpm, SPN 91 avg>65%, SPN 84 avg>100 km/h, SPN 521 avg>25%, SPN 513 avg>75%, SPN 523 frequent gear changes, SPN 527/596 cruise control inactive
    - Return each probable cause with SPN ID, name, finding, average value, unit, and catalog range
    - Return insufficient-data response if no records found
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 11.4, 11.6_

  - [x] 5.3 Implement `tool-listar-buses-activos` Lambda
    - Compute `timestamp_limit` = now - 5 minutes
    - If `viaje_ruta` provided: query GSI `viaje_ruta-timestamp-index`
    - If no filter: scan with FilterExpression on timestamp
    - For each bus: extract autobus, viaje_ruta, operador, estado_consumo, count of alertas_spn
    - Sort: ALERTA_SIGNIFICATIVA first, then by count of out-of-range SPNs descending
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 11.4, 11.6_

  - [x] 5.4 Write unit tests for Fuel Agent Tools
    - Test `tool-consultar-telemetria` with valid bus data and empty results
    - Test `tool-calcular-desviacion` deviation classification thresholds and probable cause detection
    - Test `tool-listar-buses-activos` sorting logic and route filtering
    - _Requirements: 3.1, 3.6, 4.1, 4.2, 4.5, 5.1, 5.5_

- [x] 6. Checkpoint — Verify Fuel Agent Tools
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Maintenance Agent Tools (4 Lambdas)
  - [x] 7.1 Implement `tool-consultar-obd` Lambda
    - Parse `autobus` from Bedrock AgentCore event
    - Query last 20 records from DynamoDB, extract maintenance-relevant SPNs (`SPNS_MANTENIMIENTO`)
    - Calculate trends for each SPN: compare first-half vs second-half averages → `estable`, `ascendente`, `descendente`
    - Detect anomalous variations using `variacion_anomala()` (2x delta threshold)
    - Build brake pad status for all 6 positions (SPNs 1099–1104): ≥30%→`aceptable`, <30%→`REQUIERE_ATENCION`
    - Read Data_Fault from S3, filter by autobus, return 5 most recent faults with codigo, severidad, descripcion, modelo, marca_comercial, zona
    - Build `resumen_salud` text summary
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 11.4, 11.6_

  - [x] 7.2 Implement `tool-predecir-evento` Lambda
    - Parse `autobus` from event, query last 20 records, build feature vector (averages, max, min per maintenance SPN)
    - Attempt SageMaker endpoint `ado-prediccion-eventos` invocation
    - On SageMaker failure: use heuristic scoring algorithm:
      - SPN 110 temp motor: +3 if avg>120°C, +2 if max>140°C
      - SPN 175 oil temp: +2 if avg>130°C
      - SPN 100 oil pressure: +3 if min<150 kPa, +1 if avg<250 kPa
      - SPN 98 oil level: +2 if avg<30%
      - SPN 111 coolant: +2 if avg<40%
      - SPN 168 battery: +1 if min<22V
      - SPN 1761 urea: +1 if avg<15%
      - Brake pads: +2 if avg<15%, +1 if avg<30%
      - Recent fault severity added directly to score
    - Classify: BAJO (≤2), MODERADO (3–5), ELEVADO (6–8), CRITICO (>8)
    - Map urgency: BAJO→PROXIMO_SERVICIO, MODERADO→PROXIMO_SERVICIO, ELEVADO→ESTA_SEMANA, CRITICO→INMEDIATA
    - Return risk level, description, urgency, contributing factors, at-risk components, and `metodo_prediccion` field
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 11.4, 11.6_

  - [x] 7.3 Implement `tool-buscar-patrones-historicos` Lambda
    - Parse `codigo`, optional `modelo`, optional `marca_comercial` from event
    - Read Data_Fault from S3 (JSON or Parquet via `read_json_from_s3` / `read_parquet_from_s3`)
    - Filter by `codigo` (exact or partial match)
    - If `modelo`/`marca_comercial` provided: prioritize matches without excluding others
    - Sort by `fecha_hora` descending, limit to top 10
    - Compute statistics: average severity, most affected models, most affected zones/regions, average event duration, affected service types
    - Return each event with: id, autobus, fecha_hora, codigo, severidad, descripcion, modelo, marca_comercial, zona, region, servicio, duration
    - Return no-patterns-found response if no matches
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.4_

  - [x] 7.4 Implement `tool-generar-recomendacion` Lambda
    - Parse autobus, diagnostico, nivel_riesgo, urgencia, componentes from event
    - Generate `alerta_id` = UUID v4, `numero_referencia` = `OT-{YYYY}-{MMDD}-{autobus}`
    - Query DynamoDB for latest bus record to enrich with viaje_ruta, operador_desc
    - Build alert item: tipo_alerta=MANTENIMIENTO, estado=ACTIVA, agente_origen=ado-agente-mantenimiento
    - PutItem to `ado-alertas` table
    - Return confirmation with alerta_id, numero_referencia, autobus, nivel_riesgo, urgencia, and human-readable message
    - Handle DynamoDB write failure: return error response, log error in JSON structured format
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 11.4, 11.7_

  - [x] 7.5 Write unit tests for Maintenance Agent Tools
    - Test `tool-consultar-obd` trend calculation (estable, ascendente, descendente) and brake pad status thresholds
    - Test `tool-predecir-evento` heuristic scoring with various SPN combinations and risk level classification
    - Test `tool-buscar-patrones-historicos` filtering, prioritization, and statistics computation
    - Test `tool-generar-recomendacion` alert creation and error handling
    - _Requirements: 6.2, 6.4, 7.4, 7.5, 8.1, 8.4, 9.2, 9.6_

- [x] 8. Checkpoint — Verify Maintenance Agent Tools
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement Dashboard API Lambda (`ado-dashboard-api`)
  - [x] 9.1 Implement path-based router and `/dashboard/flota-status` endpoint
    - Implement single Lambda handler with path-based routing via event `path` or `resource` field
    - `/dashboard/flota-status`: Scan DynamoDB_Telemetria for latest record per bus, aggregate by estado_consumo, translate SPNs to readable names
    - Return: total buses, active count, summary by Consumption_State, list of buses with autobus, viaje_ruta, origin, destination, operador, estado_consumo, out-of-range SPN count, last update timestamp
    - Use `build_api_response()` with CORS headers
    - _Requirements: 10.1, 10.5, 11.6_

  - [x] 9.2 Implement `/dashboard/alertas-activas` endpoint
    - Query DynamoDB_Alertas for records with estado=ACTIVA
    - Sort by urgency: INMEDIATA first, then ESTA_SEMANA, then PROXIMO_SERVICIO
    - _Requirements: 10.2, 11.7_

  - [x] 9.3 Implement `/dashboard/resumen-consumo` endpoint
    - Query DynamoDB_Telemetria via GSI `viaje_ruta-timestamp-index` by route
    - Compute average rendimiento per route, aggregate efficiency summaries
    - _Requirements: 10.3, 11.6_

  - [x] 9.4 Implement `/dashboard/co2-estimado` endpoint
    - Return qualitative CO₂ reduction descriptions using fuzzy language per C-003
    - No specific numeric values — use terms like "reducción notable", "mejora significativa"
    - _Requirements: 10.4_

  - [x] 9.5 Implement error handling for all dashboard endpoints
    - Return appropriate HTTP error status codes with descriptive error messages when DynamoDB queries fail
    - _Requirements: 10.6_

  - [x] 9.6 Write unit tests for Dashboard API
    - Test path-based routing dispatches to correct handler
    - Test `/flota-status` aggregation logic
    - Test `/alertas-activas` urgency sorting
    - Test error handling returns proper HTTP status codes
    - _Requirements: 10.1, 10.2, 10.6_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- All Lambda functions use Python 3.12 runtime in `us-east-1`
- The implementation order follows the design's dependency chain: Layer → Simulator → Fuel Tools → Maintenance Tools → Dashboard
- Environment variables `DYNAMODB_TABLE_TELEMETRIA` and `DYNAMODB_TABLE_ALERTAS` are used consistently across all Lambdas (Requirements 11.6, 11.7)
- All responses from agent tools use the standard `response.py` format for Bedrock AgentCore compatibility (Requirement 11.4)
- All logging uses JSON structured format for CloudWatch (Requirement 11.3)
- Checkpoints are placed after each major group to validate incrementally
