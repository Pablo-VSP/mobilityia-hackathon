"""
Limpia los datos de demo de DynamoDB después de cada presentación.

Borra todos los items de:
- ado-telemetria-live (telemetría simulada)
- ado-alertas (alertas generadas por los agentes)

Ejecutar: python scripts/cleanup_demo_data.py
"""

import boto3

REGION = "us-east-2"
TABLES = ["ado-telemetria-live", "ado-alertas"]


def delete_all_items(table_name, session):
    """Borra todos los items de una tabla DynamoDB."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    # Obtener las keys del schema
    key_schema = table.key_schema
    key_names = [k["AttributeName"] for k in key_schema]

    print(f"  Escaneando {table_name}...")
    scan_kwargs = {"ProjectionExpression": ", ".join(key_names)}

    total_deleted = 0
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        if not items:
            break

        with table.batch_writer() as batch:
            for item in items:
                key = {k: item[k] for k in key_names}
                batch.delete_item(Key=key)
                total_deleted += 1

        if total_deleted % 100 == 0 and total_deleted > 0:
            print(f"    ...{total_deleted} items eliminados")

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return total_deleted


def main():
    print("=" * 50)
    print("LIMPIEZA DE DATOS DE DEMO")
    print("=" * 50)

    session = boto3.Session(profile_name="mobilityadods")

    for table in TABLES:
        deleted = delete_all_items(table, session)
        print(f"  ✅ {table}: {deleted} items eliminados")

    print("\n¡Limpieza completada! DynamoDB listo para nueva demo.")


if __name__ == "__main__":
    main()
