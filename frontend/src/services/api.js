export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(path, options);
  } catch (networkError) {
    throw new ApiError(
      "Backend injoignable. Vérifiez que l'API FastAPI écoute sur le port 8000.",
      0,
      networkError
    );
  }

  if (!response.ok) {
    let detail = null;

    try {
      detail = await response.json();
    } catch {
      detail = null;
    }

    const message =
      detail && typeof detail === "object" && detail.detail
        ? typeof detail.detail === "string"
          ? detail.detail
          : JSON.stringify(detail.detail)
        : `${response.status} ${response.statusText}`;

    throw new ApiError(message, response.status, detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function apiGet(path) {
  return request(path, { headers: { Accept: "application/json" } });
}

export function apiPost(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body)
  });
}
