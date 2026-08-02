import { login } from "./app/auth";

export function handleLogin(req: Request): Response {
    return new Response("ok");
}

export class ApiServer {
    start() {}
}
