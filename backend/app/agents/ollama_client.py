import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    status_code = 503


class OllamaChatClient:
    def __init__(self, base_url: str, model: str, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, system_prompt: str, user_prompt: str, num_predict: int = 640) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": num_predict},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(
                f"Ollama a renvoyé une erreur HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except TimeoutError as exc:
            raise OllamaError(
                f"La génération Ollama a dépassé le délai de {self.timeout} secondes. "
                "Essayez une question plus courte ou un modèle plus léger."
            ) from exc
        except URLError as exc:
            raise OllamaError(
                f"Ollama est injoignable à {self.base_url}. Démarrez Ollama puis réessayez."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OllamaError("Ollama a renvoyé une réponse JSON invalide.") from exc

        try:
            content = payload["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaError("La réponse d'Ollama ne contient pas de texte.") from exc
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama a renvoyé une réponse vide.")
        return content.strip()
