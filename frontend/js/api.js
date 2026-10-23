const baseUrl = (window.RECIPES_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, details = [], status = 0) {
    super(message);
    this.name = "ApiError";
    this.details = details;
    this.status = status;
  }
}

async function request(path = "", { method = "GET", body } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(`${baseUrl}/api/recipes${path}`, {
      method,
      headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    if (response.status === 204) return null;
    let data;
    try {
      data = await response.json();
    } catch {
      throw new ApiError("Сервер вернул ответ в неожиданном формате", [], response.status);
    }
    if (!response.ok) {
      const details = Array.isArray(data.details) ? data.details.filter(value => typeof value === "string") : [];
      throw new ApiError(data.error || "Не удалось выполнить запрос", details, response.status);
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error.name === "AbortError") throw new ApiError("Сервер долго не отвечает. Попробуйте ещё раз.");
    throw new ApiError("Не удалось соединиться с сервером. Проверьте, что API запущен и его адрес указан правильно.");
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  list: () => request(),
  get: id => request(`/${id}`),
  create: body => request("", { method: "POST", body }),
  replace: (id, body) => request(`/${id}`, { method: "PUT", body }),
  patch: (id, body) => request(`/${id}`, { method: "PATCH", body }),
  remove: id => request(`/${id}`, { method: "DELETE" }),
};
