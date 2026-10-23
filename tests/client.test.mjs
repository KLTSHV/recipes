// Проверка HTTP-контрактов клиента. Node.js нужен только для этих тестов.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

globalThis.window = { RECIPES_CONFIG: { API_BASE_URL: "http://localhost:9000/" } };
const source = await readFile(new URL("../frontend/js/api.js", import.meta.url), "utf8");
const { api, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
let calls = [];

function mockResponse(status, data) {
  calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options });
    return { status, ok: status >= 200 && status < 300, json: async () => data };
  };
}

test("все шесть операций отправляют нужный метод, URL и JSON", async () => {
  const operations = [
    [() => api.list(), "GET", "", undefined],
    [() => api.get(5), "GET", "/5", undefined],
    [() => api.create({ title: "Суп" }), "POST", "", { title: "Суп" }],
    [() => api.replace(5, { title: "Суп" }), "PUT", "/5", { title: "Суп" }],
    [() => api.patch(5, { is_favorite: true }), "PATCH", "/5", { is_favorite: true }],
    [() => api.remove(5), "DELETE", "/5", undefined],
  ];
  for (const [operation, method, path, body] of operations) {
    mockResponse(method === "DELETE" ? 204 : 200, {});
    await operation();
    assert.equal(calls[0].method, method);
    assert.equal(calls[0].url, `http://localhost:9000/api/recipes${path}`);
    assert.equal(calls[0].body, body === undefined ? undefined : JSON.stringify(body));
    if (body !== undefined) assert.equal(calls[0].headers["Content-Type"], "application/json");
  }
});

test("204 обрабатывается без чтения JSON", async () => {
  globalThis.fetch = async () => ({ status: 204, ok: true, json: () => { throw new Error("must not parse"); } });
  assert.equal(await api.remove(1), null);
});

test("400 передаёт понятные детали серверной валидации", async () => {
  mockResponse(400, { error: "Validation failed", details: ["Название обязательно", 123] });
  await assert.rejects(api.create({}), error => error instanceof ApiError && error.status === 400 && error.details.join() === "Название обязательно");
});

test("404 и 500 не считаются успешным запросом", async () => {
  for (const status of [404, 500]) {
    mockResponse(status, { error: "Server error", details: ["Попробуйте снова"] });
    await assert.rejects(api.get(1), error => error.status === status);
  }
});

test("ошибка соединения получает сообщение на русском", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(api.list(), error => error instanceof ApiError && error.message.includes("соединиться с сервером"));
});

test("прерывание запроса получает сообщение о таймауте", async () => {
  globalThis.fetch = async () => { throw Object.assign(new Error(), { name: "AbortError" }); };
  await assert.rejects(api.list(), error => error.message.includes("долго не отвечает"));
});

test("неожиданный не-JSON ответ отображается как ошибка", async () => {
  globalThis.fetch = async () => ({ status: 200, ok: true, json: async () => { throw new SyntaxError(); } });
  await assert.rejects(api.list(), error => error instanceof ApiError && error.message.includes("неожиданном формате"));
});
