"""
build_index.py — Genera el índice FAISS y el archivo de documentos para RAG.

Se ejecuta UNA VEZ localmente (o en Cloud Shell) antes del deploy.
Lee los documentos de la Knowledge Base, los fragmenta, genera embeddings
con Gemini text-embedding-004, y guarda:
  - faiss_index.bin  → índice vectorial para búsqueda semántica
  - documents.json   → textos originales asociados a cada vector

Luego sube ambos a GCS para que los agentes los carguen en memoria al arrancar.

Uso:
    pip install google-generativeai faiss-cpu numpy
    export GOOGLE_API_KEY="tu-api-key"
    python build_index.py
"""

import json
import os
import time

import numpy as np
import faiss
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
GCS_BUCKET = os.environ.get("GCS_BUCKET", "proy-ado-telemetria-dev-data-v1")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "aws_bl_hackathon/knowledge-base")
EMBEDDING_MODEL = "models/text-embedding-004"
CHUNK_SIZE = 800       # caracteres por chunk
CHUNK_OVERLAP = 100    # solapamiento entre chunks

# Documentos locales a indexar (los mismos que subimos a GCS)
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "manuales")
EXTRA_FILES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "motor_spn.JSON"),
]

# Output local
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

genai.configure()  # usa GOOGLE_API_KEY del environment


# ---------------------------------------------------------------------------
# Paso 1: Leer y fragmentar documentos
# ---------------------------------------------------------------------------

def read_documents() -> list[dict]:
    """Lee todos los documentos y retorna lista de {source, text}."""
    documents = []

    # Leer manuales .md
    if os.path.exists(DOCS_DIR):
        for filename in os.listdir(DOCS_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(DOCS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                documents.append({"source": filename, "text": text})
                print(f"  📄 {filename} ({len(text)} chars)")

    # Leer archivos extra (JSON de catálogo, etc.)
    for filepath in EXTRA_FILES:
        if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            documents.append({"source": filename, "text": text})
            print(f"  📄 {filename} ({len(text)} chars)")

    return documents


def chunk_document(doc: dict) -> list[dict]:
    """Fragmenta un documento en chunks con solapamiento."""
    text = doc["text"]
    source = doc["source"]
    chunks = []

    # Intentar dividir por secciones (## o ###)
    sections = []
    current_section = ""
    for line in text.split("\n"):
        if line.startswith("## ") or line.startswith("### "):
            if current_section.strip():
                sections.append(current_section.strip())
            current_section = line + "\n"
        else:
            current_section += line + "\n"
    if current_section.strip():
        sections.append(current_section.strip())

    # Si las secciones son muy grandes, subdividir por tamaño
    for section in sections:
        if len(section) <= CHUNK_SIZE:
            chunks.append({"source": source, "text": section})
        else:
            # Dividir por tamaño con overlap
            for i in range(0, len(section), CHUNK_SIZE - CHUNK_OVERLAP):
                chunk_text = section[i : i + CHUNK_SIZE]
                if len(chunk_text.strip()) > 50:  # ignorar chunks muy pequeños
                    chunks.append({"source": source, "text": chunk_text.strip()})

    return chunks


# ---------------------------------------------------------------------------
# Paso 2: Generar embeddings
# ---------------------------------------------------------------------------

def generate_embeddings(chunks: list[dict]) -> np.ndarray:
    """Genera embeddings para todos los chunks usando Gemini."""
    all_embeddings = []
    batch_size = 20  # Gemini acepta hasta 100, pero vamos de a 20 para no exceder rate limit

    print(f"\n  Generando embeddings para {len(chunks)} chunks...")

    for i in range(0, len(chunks), batch_size):
        batch_texts = [c["text"] for c in chunks[i : i + batch_size]]

        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch_texts,
            task_type="retrieval_document",
        )

        all_embeddings.extend(result["embedding"])

        # Rate limiting
        if i + batch_size < len(chunks):
            time.sleep(1)  # 1 segundo entre batches

        print(f"    Batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size} done")

    return np.array(all_embeddings, dtype=np.float32)


# ---------------------------------------------------------------------------
# Paso 3: Construir índice FAISS
# ---------------------------------------------------------------------------

def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Construye un índice FAISS L2 (flat, exacto)."""
    dimension = embeddings.shape[1]  # 768 para text-embedding-004
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    print(f"\n  Índice FAISS creado: {index.ntotal} vectores, dimensión {dimension}")
    return index


# ---------------------------------------------------------------------------
# Paso 4: Guardar y subir
# ---------------------------------------------------------------------------

def save_locally(index: faiss.Index, chunks: list[dict]):
    """Guarda el índice y documentos localmente."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Guardar FAISS index
    index_path = os.path.join(OUTPUT_DIR, "faiss_index.bin")
    faiss.write_index(index, index_path)
    print(f"  💾 {index_path} ({os.path.getsize(index_path) / 1024:.1f} KB)")

    # Guardar documentos (textos asociados a cada vector)
    docs_path = os.path.join(OUTPUT_DIR, "documents.json")
    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  💾 {docs_path} ({os.path.getsize(docs_path) / 1024:.1f} KB)")


def upload_to_gcs():
    """Sube los archivos generados a GCS."""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    for filename in ["faiss_index.bin", "documents.json"]:
        local_path = os.path.join(OUTPUT_DIR, filename)
        blob_path = f"{GCS_PREFIX}/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_path)
        print(f"  ☁️  gs://{GCS_BUCKET}/{blob_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("ADO MobilityIA — Generador de índice FAISS para RAG")
    print("=" * 60)

    # 1. Leer documentos
    print("\n📂 Leyendo documentos...")
    documents = read_documents()
    print(f"   Total: {len(documents)} documentos")

    # 2. Fragmentar
    print("\n✂️  Fragmentando en chunks...")
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
    print(f"   Total: {len(all_chunks)} chunks")

    # 3. Embeddings
    print("\n🧠 Generando embeddings con Gemini...")
    embeddings = generate_embeddings(all_chunks)
    print(f"   Shape: {embeddings.shape}")

    # 4. FAISS index
    print("\n📊 Construyendo índice FAISS...")
    index = build_faiss_index(embeddings)

    # 5. Guardar
    print("\n💾 Guardando localmente...")
    save_locally(index, all_chunks)

    # 6. Subir a GCS
    print("\n☁️  Subiendo a Cloud Storage...")
    try:
        upload_to_gcs()
    except Exception as e:
        print(f"   ⚠️  No se pudo subir a GCS: {e}")
        print(f"   Sube manualmente:")
        print(f"   gcloud storage cp {OUTPUT_DIR}/faiss_index.bin gs://{GCS_BUCKET}/{GCS_PREFIX}/")
        print(f"   gcloud storage cp {OUTPUT_DIR}/documents.json gs://{GCS_BUCKET}/{GCS_PREFIX}/")

    print("\n✅ Listo! El índice está preparado para los agentes.")
    print(f"   Los agentes cargarán estos archivos al arrancar desde:")
    print(f"   gs://{GCS_BUCKET}/{GCS_PREFIX}/faiss_index.bin")
    print(f"   gs://{GCS_BUCKET}/{GCS_PREFIX}/documents.json")


if __name__ == "__main__":
    main()
