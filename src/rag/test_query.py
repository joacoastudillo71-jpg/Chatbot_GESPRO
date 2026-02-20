from src.rag.query_engine import rag_search

while True:
    pregunta = input("\nPregunta: ")
    if pregunta.lower() in ["salir", "exit"]:
        break

    resultado = rag_search(pregunta)
    print("\nRespuesta:", resultado["answer"])