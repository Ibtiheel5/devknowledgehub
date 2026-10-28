import json
from unittest.mock import patch

from app.agents.ollama_client import OllamaChatClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps({"message": {"content": "  réponse  "}}).encode()


def test_ollama_chat_returns_model_response():
    client = OllamaChatClient("http://localhost:11434/", "test-model")

    with patch("app.agents.ollama_client.urlopen", return_value=FakeResponse()) as urlopen:
        result = client.chat("system", "question")

    assert result == "réponse"
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:11434/api/chat"
    payload = json.loads(request.data)
    assert payload["model"] == "test-model"
    assert payload["options"]["num_predict"] == 640
    assert urlopen.call_args.kwargs["timeout"] == 300
