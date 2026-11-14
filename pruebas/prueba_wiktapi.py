"""Prueba mínima de WiktApi para Fonoflow 1.0.

Instalación: python -m pip install requests
Ejecución:    python pruebas/prueba_wiktapi.py
"""

import requests

BASE_URL = "https://api.wiktapi.dev/v1/en/word"
TIMEOUT = 12


def consultar(palabra: str, recurso: str) -> dict:
    """Consulta WiktApi y devuelve el JSON o informa del error."""
    url = f"{BASE_URL}/{palabra}/{recurso}"
    respuesta = requests.get(url, params={"lang": "en"}, timeout=TIMEOUT)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, dict):
        raise ValueError("La API devolvió un formato inesperado.")
    return datos


def extraer_pronunciaciones(datos: dict) -> list[dict]:
    """Recupera solo pronunciaciones etiquetadas General-American."""
    encontrados = []
    vistos = set()

    # Recorremos la estructura sin asumir un nivel fijo de anidación.
    def recorrer(nodo):
        if isinstance(nodo, dict):
            if "ipa" in nodo and "General-American" in (nodo.get("tags") or []):
                ipa = nodo.get("ipa")
                if ipa and ipa not in vistos:
                    vistos.add(ipa)
                    encontrados.append({"ipa": ipa, "audio": nodo.get("audio")})
            for valor in nodo.values():
                recorrer(valor)
        elif isinstance(nodo, list):
            for elemento in nodo:
                recorrer(elemento)

    recorrer(datos)

    return encontrados


def extraer_traducciones(datos: dict) -> list[dict]:
    """Filtra el español y conserva significado, categoría y región."""
    resultados = []
    vistos = set()

    for grupo in datos.get("translations", []):
        categoria = grupo.get("pos", "sin categoría")
        for item in grupo.get("translations", []):
            if item.get("lang_code") != "es":
                continue
            palabra = item.get("word")
            if not palabra:
                continue
            significado = item.get("sense", "")
            etiquetas = item.get("tags") or []
            clave = (categoria, palabra.casefold(), significado)
            if clave in vistos:
                continue
            vistos.add(clave)
            resultados.append({
                "traduccion": palabra,
                "categoria": categoria,
                "significado": significado,
                "etiquetas": etiquetas,
            })

    # Primero sentidos generales, luego variantes de México y otras alternativas.
    def prioridad(item):
        etiquetas = item["etiquetas"]
        sentido = item["significado"].lower()
        if not etiquetas and sentido in {"greeting", "", "salutation"}:
            return 0
        if "Mexico" in etiquetas:
            return 1
        if not etiquetas:
            return 2
        return 3

    return sorted(resultados, key=prioridad)


def mostrar(palabra: str) -> None:
    print(f"\n--- Fonoflow | {palabra} ---")

    try:
        datos_ipa = consultar(palabra, "pronunciations")
        pronunciaciones = extraer_pronunciaciones(datos_ipa)
        if pronunciaciones:
            print("\nIPA estadounidense:")
            for item in pronunciaciones[:5]:
                print(f"  • {item['ipa']}")
                if item["audio"]:
                    print(f"    Audio: {item['audio']}")
            if not any(item["audio"] for item in pronunciaciones):
                print("  Audio: no proporcionado para estas pronunciaciones")
        else:
            print("\nIPA estadounidense: no disponible o sin etiqueta General-American")
    except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
        print(f"\nError consultando pronunciaciones: {error}")

    try:
        datos_traducciones = consultar(palabra, "translations")
        traducciones = extraer_traducciones(datos_traducciones)
        if traducciones:
            principal = traducciones[0]
            print(f"\nTraducción sugerida: {principal['traduccion']}")
            print(f"  Categoría: {principal['categoria']}")
            if principal["significado"]:
                print(f"  Sentido: {principal['significado']}")
            print("\nOtras traducciones (máximo 5):")
            for item in traducciones[1:6]:
                region = ", ".join(item["etiquetas"]) or "sin etiqueta regional"
                print(f"  • {item['traduccion']} — {item['significado'] or 'sin contexto'} ({region})")
        else:
            print("\nTraducción al español: no disponible")
    except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
        print(f"\nError consultando traducciones: {error}")

    print("\nNota: las traducciones son datos léxicos, no equivalencias garantizadas para cada contexto.")


def main() -> None:
    print("=== Fonoflow 1.0 | Prueba de WiktApi ===")
    print("Escribe 'salir' para terminar.")
    while True:
        palabra = input("\nPalabra en inglés: ").strip().lower()
        if palabra in {"salir", "exit", "quit"}:
            break
        if not palabra or not palabra.isascii() or not palabra.isalpha():
            print("Introduce una sola palabra en inglés (letras a-z).")
            continue
        mostrar(palabra)


if __name__ == "__main__":
    main()
