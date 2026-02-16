
// aida-multimodal-onpremise/web-ui/components/chat.tsx

"use client";

import { Message } from "@/types/chat";
import ChatInput from "./ChatInput";
import { User } from "@/types/user";
import { sendToOrchestrator } from "@/services/orchestratorClient";
import { useState, useRef, useEffect } from "react";

type ChatProps = {
  user: User | null;
  sessionId: string;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
};

export default function Chat({
  user,
  sessionId,
  messages,
  setMessages,
}: ChatProps) {
  
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false); // Estado para saber si graba audio
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // LÓGICA DE ENVÍO UNIFICADA (TEXTO + ARCHIVO)
  const handleSend = async (text: string, file?: File, fileKind?: "file" | "image") => {
    if (!user) return;

    // 1. UI Optimista: Construimos el mensaje para mostrarlo inmediatamente
    const tempId = crypto.randomUUID();
    let displayContent = text;
    
    // Si hay archivo, agregamos un indicador visual al texto del chat
    if (file) {
        const icon = fileKind === "image" ? "📷" : "📎";
        // Si hay texto: "📷 [foto.jpg] Mira esto"
        // Si no hay texto: "📷 [foto.jpg]"
        displayContent = text 
            ? `${icon} [${file.name}]\n${text}`
            : `${icon} [${file.name}]`;
    }

    // Actualizamos estado visual
    setMessages((prev) => [
      ...prev,
      { id: tempId, role: "user", content: displayContent, kind: fileKind || "text" },
    ]);

    setIsLoading(true);

    try {
        // Determinar tipo de input para el backend
        let inputType: "text" | "image" | "pdf" = "text";
        if (file) {
            // Si el archivo nativo es una imagen (JPG, PNG, etc), es "image"
            if (file.type.startsWith("image/")) {
                inputType = "image";
            } else {
                // Si no es imagen, asumimos que es "pdf"
                inputType = "pdf";
            }
        }

        // Guardar mensaje USER en BD
        await fetch("http://localhost:8001/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                user_id: user.user_id,
                role: "user",
                input_type: inputType,
                content: displayContent, 
            }),
        }).catch(e => console.error("Error guardando msg user", e));

        // 2. ENVIAR AL ORQUESTADOR
        // - Si hay archivo, 'content' es el archivo.
        // - La pregunta (texto) va en 'metadata' para que el orquestador la use.
        
        let contentForOrchestrator: string = text;

        //let contentForOrchestrator: string | File = text;
        
        // Si no hay texto pero hay archivo, el texto implícito es "Analiza esto" (o vacío)
        // pero lo mandamos en metadata de todas formas.
        const metadata = { user_query: text }; 

        // if (file) {
        //     contentForOrchestrator = file;
        // }

        if (file) {
            // Convertimos el archivo a Base64 con Promise para esperar el resultado
            contentForOrchestrator = await new Promise<string>((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file); // Extrae el archivo preservando sus bytes perfectos
                reader.onload = () => resolve(reader.result as string);
                reader.onerror = (error) => reject(error);
            });
        }

        const res = await sendToOrchestrator(
            user, 
            sessionId, 
            inputType, 
            contentForOrchestrator, 
            metadata 
        );

        // 3. Procesar respuesta del Orquestador
        let cleanContent = res.content;
        try {
            // Intentamos parsear por si el orquestador devuelve un JSON string
            const parsed = JSON.parse(res.content);
            if (parsed.final_text) cleanContent = parsed.final_text;
            else if (parsed.content) cleanContent = parsed.content;
        } catch (e) {
            // Si falla el parseo, usamos el contenido tal cual
        }

        // Guardar respuesta AI en BD
        let aiMessageId = crypto.randomUUID();
        try {
            const aiRes = await fetch("http://localhost:8001/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_id: user.user_id,
                    role: "assistant",
                    input_type: "text",
                    content: cleanContent,
                    agent_chain: "multimodal",
                }),
            });
            const data = await aiRes.json();
            if (data.message_id) aiMessageId = data.message_id;
        } catch (e) { console.error("Error saving AI msg", e); }

        // Mostrar respuesta AI en UI
        setMessages((prev) => [
            ...prev,
            { id: aiMessageId, role: "assistant", content: cleanContent },
        ]);

    } catch (error) {
        console.error("Error en chat:", error);
        setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "assistant", content: "Lo siento, hubo un error procesando tu solicitud." },
        ]);
    } finally {
        setIsLoading(false);
    }
  };

  // LÓGICA DE AUDIO
  const handleAudioStop = async (audioBlob: Blob) => {
      setIsRecording(false);
      if (!user) return;

      // 1. UI update
      setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: "user",
          content: "🎤 [Nota de voz]",
          kind: "audio"
      }]);
      setIsLoading(true);

      try {
          // Convertir Blob a File para el orquestador
          const audioFile = new File([audioBlob], "voice_note.webm", { type: "audio/webm" });

          // Guardar User Msg en BD (Audio)
          await fetch("http://localhost:8001/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                user_id: user.user_id,
                role: "user",
                input_type: "audio",
                content: "🎤 [Nota de voz]", 
            }),
          }).catch(e => console.error("Error saving user audio msg", e));

          // Enviar audio al orquestador
          const res = await sendToOrchestrator(user, sessionId, "audio", audioFile);
          
          let cleanContent = res.content;
          try {
             const p = JSON.parse(res.content);
             if(p.final_text) cleanContent = p.final_text;
             else if (p.content) cleanContent = p.content;
          } catch(e){}

          // Guardar AI Msg en BD
          let aiMessageId = crypto.randomUUID();
          const aiRes = await fetch("http://localhost:8001/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_id: user.user_id,
                    role: "assistant",
                    input_type: "text",
                    content: cleanContent,
                    agent_chain: "voice -> nlp",
                }),
          });
          const data = await aiRes.json();
          if (data.message_id) aiMessageId = data.message_id;

          setMessages(prev => [...prev, {
              id: aiMessageId, role: "assistant", content: cleanContent
          }]);

      } catch (e) {
          console.error(e);
          setMessages(prev => [...prev, {
            id: crypto.randomUUID(), role: "assistant", content: "⚠️ Error procesando el audio."
          }]);
      } finally {
          setIsLoading(false);
      }
  };

  // FUNCIONES DE FEEDBACK
  const sendFeedback = async (messageId: string, rating: 1 | -1) => {
    if (!user) return;
    
    // UI Update Optimista
    setMessages((prev) =>
      prev.map((m) => m.id === messageId ? { ...m, feedback: rating } : m)
    );

    // Fetch protegido
    try {
        await fetch("http://localhost:8001/chat/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message_id: messageId, user_id: user.user_id, rating }),
        });
    } catch (e) {
        console.error("Error enviando feedback:", e);
    }
  };

  const shouldShowFeedback = (msg: Message) =>
    msg.role === "assistant" && Boolean(msg.content?.trim());

  // COMPONENTES VISUALES SOBRIOS
  const TypingIndicator = () => (
    <div className="mr-auto bg-blue-50 border border-blue-100 rounded-2xl rounded-bl-none px-4 py-3 w-fit">
      <div className="flex space-x-1 h-5 items-center">
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
      </div>
    </div>
  );

  const ThumbIcon = ({ className, up }: { className?: string, up: boolean }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      {up ? (
        <>
            <path d="M7 10v12" /><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z" />
        </>
      ) : (
        <>
            <path d="M17 14V2" /><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z" />
        </>
      )}
    </svg>
  );

  // RENDER
  return (
    <div className="flex flex-col h-full bg-slate-50/30">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
             <p>Envía un mensaje para comenzar…</p>
          </div>
        )}

        {/* Renderizado de mensajes */}
        {messages.map((msg, index) => (
          <div key={msg.id ?? `msg-${index}`} className="flex flex-col space-y-1">
            <div
              className={`px-5 py-4 rounded-2xl shadow-sm text-[15px] whitespace-pre-wrap ${
                msg.role === "user"
                  ? "max-w-[75%] ml-auto border border-[#0f2a44] bg-white text-slate-900 rounded-br-none"
                  : "max-w-[90%] xl:max-w-[85%] mr-auto bg-blue-50 text-slate-900 border border-blue-100 rounded-bl-none"
              }`}
            >
              {msg.content}
            </div>

            {/* SECCIÓN DE FEEDBACK */}
            {shouldShowFeedback(msg) && (
              <div className="mr-auto flex items-center gap-2 px-1 mt-1">
                {/* LIKE */}
                <button
                  type="button"
                  onClick={() => sendFeedback(msg.id, 1)}
                  disabled={msg.feedback !== undefined}
                  className={`
                    flex items-center justify-center w-8 h-8 rounded-full border transition-colors duration-200
                    ${
                      msg.feedback === 1
                        ? "bg-slate-800 border-slate-800 text-white" 
                        : "bg-white border-slate-200 text-slate-400 hover:border-slate-400 hover:text-slate-600"
                    }
                    ${msg.feedback === -1 ? "opacity-20" : ""}
                  `}
                  title="Útil"
                >
                  <ThumbIcon up={true} className={msg.feedback === 1 ? "fill-current" : ""} />
                </button>

                {/* DISLIKE */}
                <button
                  type="button"
                  onClick={() => sendFeedback(msg.id, -1)}
                  disabled={msg.feedback !== undefined}
                  className={`
                    flex items-center justify-center w-8 h-8 rounded-full border transition-colors duration-200
                    ${
                      msg.feedback === -1
                        ? "bg-slate-800 border-slate-800 text-white"
                        : "bg-white border-slate-200 text-slate-400 hover:border-slate-400 hover:text-slate-600"
                    }
                    ${msg.feedback === 1 ? "opacity-20" : ""}
                  `}
                  title="No útil"
                >
                  <ThumbIcon up={false} className={msg.feedback === -1 ? "fill-current" : ""} />
                </button>
                
                {msg.feedback && (
                  <span className="text-xs text-slate-500 ml-2 animate-fade-in">
                    Gracias
                  </span>
                )}
              </div>
            )}
          </div>
        ))}

        {isLoading && (
            <div className="animate-fade-in-up">
                <TypingIndicator />
            </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSend={handleSend}
        onRecordStart={() => setIsRecording(true)}
        onRecordStop={handleAudioStop}
        isRecording={isRecording}
        disabled={!user || isLoading}
      />
    </div>
  );
}