"""
response — Formato estándar de respuesta para Bedrock AgentCore y API Gateway.

Provee funciones para construir respuestas consistentes en tres contextos:

  build_agent_response   Respuesta para Bedrock AgentCore Action Groups.
  build_error_response   Respuesta de error genérica (agente o API).
  build_api_response     Respuesta para API Gateway con headers CORS.

Requisitos: 1.8, 11.4
"""

import json


def build_agent_response(body: dict, status: str = "success") -> dict:
    """
    Construye una respuesta compatible con el formato de Bedrock AgentCore
    Action Group.

    El formato sigue la estructura esperada por AgentCore para que el
    agente pueda interpretar el resultado de la herramienta.

    Args:
        body: Diccionario con los datos de respuesta de la herramienta.
        status: Estado de la operación ('success' o 'error').

    Returns:
        Diccionario con la estructura de respuesta de Action Group:
        {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "...",
                "function": "...",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "<json string>"
                        }
                    }
                }
            }
        }
    """
    response_payload = {
        "status": status,
        "data": body,
    }

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "",
            "function": "",
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(response_payload, ensure_ascii=False, default=str),
                    }
                }
            },
        },
    }


def build_error_response(message: str, status_code: int = 500) -> dict:
    """
    Construye una respuesta de error compatible con Bedrock AgentCore
    Action Group.

    Args:
        message: Mensaje descriptivo del error.
        status_code: Código HTTP de referencia (500, 400, 404, etc.).

    Returns:
        Diccionario con la estructura de respuesta de error de Action Group.
    """
    error_payload = {
        "status": "error",
        "error": {
            "message": message,
            "status_code": status_code,
        },
    }

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "",
            "function": "",
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(error_payload, ensure_ascii=False, default=str),
                    }
                }
            },
        },
    }


def build_api_response(body: dict | list, status_code: int = 200) -> dict:
    """
    Construye una respuesta para API Gateway con headers CORS.

    Incluye los headers necesarios para que el dashboard (QuickSight
    o Streamlit) pueda consumir la API sin problemas de CORS.

    Args:
        body: Diccionario o lista con los datos de respuesta.
        status_code: Código HTTP de la respuesta (default 200).

    Returns:
        Diccionario con la estructura de respuesta de API Gateway:
        {
            "statusCode": 200,
            "headers": { CORS headers },
            "body": "<json string>"
        }
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
