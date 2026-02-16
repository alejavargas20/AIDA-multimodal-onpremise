// aida-multimodal-onpremise/web-ui/components/LoginModal.tsx

"use client";

import { useState } from "react";
import { User } from "@/types/user";

type Props = {
  onClose: () => void;
  onLogin: (user: User) => void; 
};

export default function LoginModal({ onClose, onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!username || !password) return;

    try {
      setLoading(true);

      const res = await fetch("http://localhost:8001/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        alert("Usuario o contraseña incorrectos");
        return;
      }

      const user: User = await res.json();
      onLogin(user); 
    } catch (err) {
      console.error("Error login:", err);
      alert("Error al conectar con el servidor");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-80 text-slate-900 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Iniciar sesión</h2>

        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Usuario"
          className="
            w-full mb-3 px-3 py-2
            border border-slate-300 rounded-md
            focus:outline-none focus:ring-2 focus:ring-brand
          "
        />

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Contraseña"
          className="
            w-full mb-4 px-3 py-2
            border border-slate-300 rounded-md
            focus:outline-none focus:ring-2 focus:ring-brand
          "
        />

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="text-slate-600 hover:text-slate-800"
            disabled={loading}
          >
            Cancelar
          </button>

          <button
            onClick={submit}
            disabled={loading}
            className="
              px-4 py-2 rounded-md
              border border-brand
              text-brand
              bg-white
              hover:bg-blue-50
              transition
              disabled:opacity-50
            "
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
