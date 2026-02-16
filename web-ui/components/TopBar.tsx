// aida-multimodal-onpremise/web-ui/components/TopBar.tsx
"use client";

import { useState } from "react";
import LoginModal from "./LoginModal";
import { User } from "@/types/user";
import { saveUser, clearUser } from "@/utils/session";

type Props = {
  user: User | null;
  setUser: (user: User | null) => void;
};

export default function TopBar({ user, setUser }: Props) {
  const [open, setOpen] = useState(false);
  const [showLogin, setShowLogin] = useState(false);

  return (
    <header className="h-14 bg-slate-900 text-white flex items-center justify-between px-6 border-b border-slate-700">
      <div>
        <h1 className="font-semibold">AIDA Finanzas</h1>
        <p className="text-xs text-slate-400">
          Asistente Inteligente para Análisis Financiero
        </p>
      </div>

      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="text-sm flex items-center gap-1"
        >
          {user ? user.username : "Iniciar sesión"} ▾
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-44 bg-white text-black rounded shadow">
            {!user ? (
              <button
                onClick={() => {
                  setShowLogin(true);
                  setOpen(false);
                }}
                className="block w-full text-left px-4 py-2 hover:bg-slate-100"
              >
                Iniciar sesión
              </button>
            ) : (
              <button
                onClick={() => {
                  clearUser();
                  setUser(null);
                  setOpen(false);
                }}
                className="block w-full text-left px-4 py-2 hover:bg-slate-100"
              >
                Cerrar sesión
              </button>
            )}
          </div>
        )}
      </div>

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onLogin={(user: User) => {
            setUser(user);
            saveUser(user);
            setShowLogin(false);
          }}
        />
      )}
    </header>
  );
}
