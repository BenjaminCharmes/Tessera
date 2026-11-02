import { request, send } from "./http";

const JSON_HEADERS = { "Content-Type": "application/json" };

/** POST a JSON body and decode the JSON answer. */
export async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

/** PUT a JSON body and decode the JSON answer. */
export async function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

/** PATCH a JSON body and decode the JSON answer. */
export async function patch_<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

/** DELETE a resource; the answer carries nothing to read. */
export async function del(path: string): Promise<void> {
  await send(path, { method: "DELETE" });
}
