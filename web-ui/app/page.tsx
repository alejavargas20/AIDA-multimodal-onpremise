// // // aida-multimodal-onpremise/web-ui/app/page.tsx
// // "use client";

// // import { useEffect, useState } from "react";
// // import TopBar from "@/components/TopBar";
// // import Sidebar from "@/components/Sidebar";
// // import Chat from "@/components/Chat";
// // import { Message } from "@/types/chat";
// // import { User } from "@/types/user";
// // import { loadUser } from "@/utils/session";

// // type ChatSession = {
// //   session_id: string;
// //   started_at: string;
// // };

// // export default function Page() {
// //   const [user, setUser] = useState<User | null>(null);
// //   const [messages, setMessages] = useState<Message[]>([]);
// //   const [sessionId, setSessionId] = useState<string | null>(null);
// //   const [sessions, setSessions] = useState<ChatSession[]>([]);

// //   //  Cargar usuario

// //   useEffect(() => {
// //       const stored = loadUser();
// //       if (stored) setUser(stored);
// //     }, []);

// //     // Crear sesión inicial

// //     useEffect(() => {
// //     if (!user) return;

// //     const currentUser = user;

// //     async function loadSessions() {
// //       const res = await fetch(
// //         `http://localhost:8001/chat/sessions/${currentUser.user_id}`
// //       );
// //       const data = await res.json();
// //       setSessions(data);

// //       // abrir la más reciente automáticamente
// //       if (data.length > 0) {
// //         openSession(data[0].session_id);
// //       }
// //     }

// //     loadSessions();
// //   }, [user]);


// //   // Cargar sesiones del usuario
  
// //   useEffect(() => {
// //     if (!user) return;

// //     fetch(`http://localhost:8001/chat/sessions/${user.user_id}`)
// //       .then((res) => res.json())
// //       .then(setSessions);
// //   }, [user]);

// //   //   Nuevo chat

// //   const newChat = async () => {
// //     if (!user) return;

// //     const res = await fetch("http://localhost:8001/chat/session", {
// //       method: "POST",
// //       headers: { "Content-Type": "application/json" },
// //       body: JSON.stringify({ user_id: user.user_id }),
// //     });

// //     const data = await res.json();

// //     setSessionId(data.session_id);
// //     setMessages([]);

// //     setSessions(prev => [
// //       {
// //         session_id: data.session_id,
// //         started_at: new Date().toISOString(),
// //       },
// //       ...prev,
// //     ]);
// //   };


// //   //  Abrir sesión existente

// //   const openSession = async (sessionId: string) => {
// //     const res = await fetch(
// //       `http://localhost:8001/chat/history/${sessionId}`
// //     );
// //     const data = await res.json();

// //     setSessionId(sessionId);
// //     setMessages(
// //       data.map((m: any) => ({
// //         id: crypto.randomUUID(),
// //         role: m.role,
// //         content: m.content,
// //       }))
// //     );
// //   };

// //   if (!user || !sessionId) {
// //     return <p className="p-6 text-slate-500">Cargando sesión…</p>;
// //   }

// //   return (
// //     <div className="h-full flex flex-col">
// //       <TopBar user={user} setUser={setUser} />

// //       <div className="flex flex-1 overflow-hidden">
// //         <Sidebar
// //           sessions={sessions}
// //           activeSessionId={sessionId}
// //           onNewChat={newChat}
// //           onSelectSession={openSession}
// //           disabled={!user}
// //         />

// //         <main className="flex-1 flex flex-col bg-slate-50">
// //           <Chat
// //             user={user}
// //             sessionId={sessionId}
// //             messages={messages}
// //             setMessages={setMessages}
// //           />
// //         </main>
// //       </div>
// //     </div>
// //   );
// // }


// "use client";

// import { useEffect, useState } from "react";
// import TopBar from "@/components/TopBar";
// import Sidebar from "@/components/Sidebar";
// import Chat from "@/components/Chat";
// import LoginModal from "@/components/LoginModal"; // Importado para evitar el bloqueo
// import { Message } from "@/types/chat";
// import { User } from "@/types/user";
// import { loadUser, saveUser, removeUser } from "@/utils/session"; // Helpers para persistencia

// type ChatSession = {
//   session_id: string;
//   started_at: string;
// };

// export default function Page() {
//   const [user, setUser] = useState<User | null>(null);
//   const [messages, setMessages] = useState<Message[]>([]);
//   const [sessionId, setSessionId] = useState<string | null>(null);
//   const [sessions, setSessions] = useState<ChatSession[]>([]);

//   // 1. Cargar usuario al montar el componente
//   useEffect(() => {
//     const stored = loadUser();
//     if (stored) setUser(stored);
//   }, []);

//   // 2. Cargar sesiones cuando el usuario está logueado
//   useEffect(() => {
//     if (!user) return;

//     async function loadSessions() {
//       try {
//         const res = await fetch(`http://localhost:8001/chat/sessions/${user!.user_id}`);
//         const data = await res.json();
//         setSessions(data);

//         // Abrir la más reciente automáticamente si existe
//         if (data.length > 0) {
//           openSession(data[0].session_id);
//         } else {
//           await newChat(); // Crear una si es un usuario nuevo
//         }
//       } catch (e) {
//         console.error("Error cargando sesiones:", e);
//       }
//     }
//     loadSessions();
//   }, [user]);

//   // --- TUS FUNCIONES IMPORTANTES RECUPERADAS ---

//   const newChat = async () => {
//     if (!user) return;
//     try {
//       const res = await fetch("http://localhost:8001/chat/session", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ user_id: user.user_id }),
//       });
//       const data = await res.json();

//       setSessionId(data.session_id);
//       setMessages([]);
//       setSessions((prev) => [
//         {
//           session_id: data.session_id,
//           started_at: new Date().toISOString(),
//         },
//         ...prev,
//       ]);
//     } catch (e) {
//       console.error("Error al crear nuevo chat:", e);
//     }
//   };

//   const openSession = async (sid: string) => {
//     try {
//       const res = await fetch(`http://localhost:8001/chat/history/${sid}`);
//       const data = await res.json();

//       setSessionId(sid);
//       setMessages(
//         data.map((m: any) => ({
//           id: crypto.randomUUID(),
//           role: m.role,
//           content: m.content,
//         }))
//       );
//     } catch (e) {
//       console.error("Error al abrir sesión:", e);
//     }
//   };

//   // --- MANEJO DE AUTENTICACIÓN ---

//   const handleLogin = (newUser: User) => {
//     saveUser(newUser);
//     setUser(newUser);
//   };

//   const handleLogout = () => {
//     removeUser();
//     setUser(null);
//     setSessionId(null);
//     setMessages([]);
//     setSessions([]);
//   };

//   // --- LÓGICA DE RENDERIZADO ---

//   // Si no hay usuario, mostramos el Modal (Evita el bucle de "Cargando sesión")
//   if (!user) {
//     return <LoginModal onClose={() => {}} onLogin={handleLogin} />;
//   }

//   // Si hay usuario pero la sesión está en camino
//   if (!sessionId) {
//     return (
//       <div className="h-full flex flex-col bg-slate-50">
//         <TopBar user={user.username} onLogout={handleLogout} />
//         <div className="flex-1 flex items-center justify-center text-slate-500">
//           Iniciando entorno de chat...
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div className="h-full flex flex-col">
//       {/* Pasamos el username real al TopBar */}
//       <TopBar user={user.username} onLogout={handleLogout} />

//       <div className="flex flex-1 overflow-hidden">
//         <Sidebar
//           sessions={sessions}
//           activeSessionId={sessionId}
//           onNewChat={newChat}
//           onSelectSession={openSession}
//           disabled={!user}
//         />

//         <main className="flex-1 flex flex-col bg-slate-50">
//           <Chat
//             user={user}
//             sessionId={sessionId}
//             messages={messages}
//             setMessages={setMessages}
//           />
//         </main>
//       </div>
//     </div>
//   );
// }

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