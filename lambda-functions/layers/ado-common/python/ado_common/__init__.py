"""
ado_common — Capa compartida para las Lambda functions de ADO MobilityIA.

Esta capa contiene los módulos utilitarios reutilizados por las 9 funciones
Lambda de la plataforma de optimización de flota:

Módulos:
    spn_catalog       Carga y validación del catálogo de 36 SPNs desde S3.
    telemetry_pivot   Pivoteo de registros por-SPN a estado consolidado de autobús.
    dynamo_utils      Helpers de lectura/escritura para DynamoDB.
    s3_utils          Helpers de lectura para Amazon S3.
    constants         Constantes de SPN IDs y agrupaciones funcionales.
    response          Formato estándar de respuesta para Bedrock AgentCore y API Gateway.
"""

__version__ = "0.1.0"
