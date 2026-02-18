// aida-multimodal-onpremise/web-ui/app/page.tsx

"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import LoginModal from "@/components/LoginModal";
import { Message } from "@/types/chat";
import { User } from "@/types/user";
import { loadUser, saveUser } from "@/utils/session";

type ChatSession = {
  session_id: string;
  started_at: string;
};

export default function Page() {
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // 1. Cargar usuario al montar el componente
  useEffect(() => {
    const stored = loadUser();
    if (stored) setUser(stored);
  }, []);

  // 2. Cargar sesiones cuando el usuario existe
  useEffect(() => {
    if (!user) return;

    async function loadSessions() {
      try {
        const res = await fetch(`http://localhost:8001/chat/sessions/${user!.user_id}`);
        const data = await res.json();
        setSessions(data);

        if (data.length > 0) {
          openSession(data[0].session_id);
        } else {
          await newChat(); 
        }
      } catch (e) {
        console.error("Error al cargar sesiones:", e);
      }
    }
    loadSessions();
  }, [user]);

  // --- FUNCIONES DE LÓGICA ---

  const newChat = async () => {
    if (!user) return;
    try {
      const res = await fetch("http://localhost:8001/chat/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id }),
      });
      const data = await res.json();

      setSessionId(data.session_id);
      setMessages([]);
      setSessions((prev) => [
        { session_id: data.session_id, started_at: new Date().toISOString() },
        ...prev,
      ]);
    } catch (e) {
      console.error("Error creando chat:", e);
    }
  };

  const openSession = async (sid: string) => {
    try {
      const res = await fetch(`http://localhost:8001/chat/history/${sid}`);
      const data = await res.json();
      setSessionId(sid);
      setMessages(
        data.map((m: any) => ({
          id: crypto.randomUUID(),
          role: m.role,
          content: m.content,
        }))
      );
    } catch (e) {
      console.error("Error abriendo sesión:", e);
    }
  };

  const handleLogin = (newUser: User) => {
    saveUser(newUser);
    setUser(newUser);
  };

  // --- RENDERIZADO ---

  // Si no hay usuario, mostramos el LoginModal para evitar la pantalla de carga infinita
  if (!user) {
    return <LoginModal onClose={() => {}} onLogin={handleLogin} />;
  }

  // Si hay usuario pero la sesión está cargando
  if (!sessionId) {
    return (
      <div className="h-full flex flex-col bg-slate-50">
        {/* CORRECCIÓN: Usamos setUser como pide tu componente TopBar */}
        <TopBar user={user} setUser={setUser} />
        <div className="flex-1 flex items-center justify-center text-slate-500 italic">
          Iniciando entorno de chat para {user.username}...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* CORRECCIÓN: Pasamos el objeto 'user' completo y la función 'setUser' */}
      <TopBar user={user} setUser={setUser} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          sessions={sessions}
          activeSessionId={sessionId}
          onNewChat={newChat}
          onSelectSession={openSession}
          disabled={!user}
        />

        <main className="flex-1 flex flex-col bg-slate-50">
          <Chat
            user={user}
            sessionId={sessionId}
            messages={messages}
            setMessages={setMessages}
          />
        </main>
      </div>
    </div>
  );
}