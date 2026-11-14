"""Pruebas exploratorias de APIs para Fonoflow 1.0.

Instalación: python -m pip install requests
Ejecución:    python prueba_apis.py

Este programa no garantiza que una transcripción sea estadounidense ni que
una traducción sea correcta: señala las limitaciones de las fuentes.
"""

import re
from urllib.parse import quote

import requests

DICCIONARIO_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
TRADUCCION_URL = "https://api.mymemory.translated.net/get"
TIMEOUT = 10


def consultar_diccionario(palabra):
    """Devuelve IPA, URL de audio y observaciones de la API del diccionario."""
    respuesta = requests.get(DICCIONARIO_URL.format(quote(palabra)), timeout=TIMEOUT)
    if respuesta.status_code == 404:
        return {"error": "La palabra no aparece en Free Dictionary API."}
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, list) or not datos:
        return {"error": "Formato inesperado en la respuesta del diccionario."}

    entrada = datos[0]
    pronunciaciones = entrada.get("phonetics", [])
    if not isinstance(pronunciaciones, list):
        pronunciaciones = []

    # Esta API no garantiza etiquetas de región. La terminación /oʊ/ en
    # "hello" sugiere inglés estadounidense, pero no identifica todos los casos.
    candidatas = [p for p in pronunciaciones if isinstance(p, dict) and p.get("text")]
    ipa = None
    nota_ipa = "No hay transcripción IPA disponible."
    for p in candidatas:
        if "us" in str(p.get("audio", "")).lower().split("/")[-1]:
            ipa = p["text"]
            nota_ipa = "IPA asociado a un audio etiquetado US (verificar acento)."
            break
    if ipa is None and candidatas:
        # No se etiqueta como US si la fuente no lo garantiza.
        ipa = candidatas[0]["text"]
        nota_ipa = "La API no confirma que este IPA sea estadounidense."

    audios = [p.get("audio") for p in pronunciaciones
              if isinstance(p, dict) and isinstance(p.get("audio"), str) and p["audio"]]
    audio_us = next((url for url in audios if re.search(r"(?:-|_)us(?:\.|-|_)", url, re.I)), None)
    audio = audio_us or (audios[0] if audios else None)
    nota_audio = "Audio con etiqueta US (su disponibilidad debe verificarse)." if audio_us else (
        "Hay audio, pero no está identificado como estadounidense." if audio else
        "No se proporciona URL de audio.")

    # Comprueba el recurso real: una URL presente en el JSON puede devolver 404.
    if audio:
        try:
            prueba = requests.get(audio, timeout=TIMEOUT, stream=True)
            prueba.raise_for_status()
            tipo = prueba.headers.get("Content-Type", "")
            prueba.close()
            if "audio" not in tipo and "octet-stream" not in tipo:
                nota_audio += f" Advertencia: Content-Type inesperado ({tipo or 'sin tipo'})."
        except requests.RequestException as exc:
            nota_audio += f" No se pudo acceder al archivo ({exc})."
            audio = None

    return {"ipa": ipa, "nota_ipa": nota_ipa, "audio": audio, "nota_audio": nota_audio}


def consultar_traduccion(palabra):
    """Consulta MyMemory. Una coincidencia alta no prueba calidad."""
    respuesta = requests.get(
        TRADUCCION_URL,
        params={"q": palabra, "langpair": "en|es"},
        timeout=TIMEOUT,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    traduccion = datos.get("responseData", {}).get("translatedText")
    if not isinstance(traduccion, str) or not traduccion.strip():
        return {"traduccion": None, "nota": "La API no devolvió una traducción."}
    sospechosa = traduccion.strip().lower() in {"testvalue", "null", "undefined"}
    nota = ("ADVERTENCIA: traducción sospechosa; no debe mostrarse como válida."
            if sospechosa else
            "Traducción automática: revisar significado y variante regional (es-MX).")
    return {"traduccion": traduccion, "nota": nota}


def main():
    print("=== Fonoflow 1.0 | Prueba de APIs ===")
    print("Escribe 'salir' para terminar.\n")
    while True:
        palabra = input("Palabra en inglés: ").strip()
        if palabra.lower() == "salir":
            print("Fin de las pruebas.")
            break
        if not palabra or not re.fullmatch(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", palabra):
            print("Ingresa una sola palabra en inglés (puede contener guion o apóstrofo).\n")
            continue

        print(f"\n--- Resultado: {palabra} ---")
        try:
            diccionario = consultar_diccionario(palabra)
            if "error" in diccionario:
                print("Diccionario:", diccionario["error"])
            else:
                print("IPA:", diccionario["ipa"] or "No disponible")
                print("Nota IPA:", diccionario["nota_ipa"])
                print("Audio:", diccionario["audio"] or "No disponible")
                print("Nota audio:", diccionario["nota_audio"])
        except (requests.RequestException, ValueError, TypeError) as exc:
            print("Error consultando el diccionario:", exc)

        try:
            traduccion = consultar_traduccion(palabra)
            print("Traducción:", traduccion["traduccion"] or "No disponible")
            print("Nota traducción:", traduccion["nota"])
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            print("Error consultando MyMemory:", exc)
        print()


if __name__ == "__main__":
    main()
