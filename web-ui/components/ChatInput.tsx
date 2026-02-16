// aida-multimodal-onpremise/web-ui/components/ChatInput.tsx

"use client";

import { useState, useRef } from "react";
import UploadMenu from "./UploadMenu";
import CameraModal from "./CameraModal";

type Props = {
  // onSend ahora recibe texto y opcionalmente el archivo
  onSend: (text: string, file?: File, kind?: "file" | "image") => void;
  // Nuevos props para grabación de audio
  onRecordStart: () => void;
  onRecordStop: (audioBlob: Blob) => void;
  disabled: boolean;
  isRecording: boolean;
};

export default function ChatInput({ 
  onSend, 
  onRecordStart, 
  onRecordStop, 
  disabled, 
  isRecording 
}: Props) {
  const [message, setMessage] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  
  // Estado para guardar el archivo temporalmente antes de enviar
  const [attachedFile, setAttachedFile] = useState<{ file: File; kind: "file" | "image" } | null>(null);

  // Referencia para la grabación
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const handleAttach = (file: File, kind: "file" | "image") => {
    setAttachedFile({ file, kind });
    setMenuOpen(false);
  };

  const removeAttachment = () => {
    setAttachedFile(null);
  };

  const send = () => {
    // Evitar enviar si está vacío Y no hay archivo
    if (!message.trim() && !attachedFile) return;
    
    // Enviamos todo junto
    onSend(message, attachedFile?.file, attachedFile?.kind);
    
    // Limpiamos
    setMessage("");
    setAttachedFile(null);
  };

  const toggleRecording = async () => {
    if (isRecording) {
      // Detener grabación
      mediaRecorderRef.current?.stop();
    } else {
      // Iniciar grabación
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        const chunks: Blob[] = [];

        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: "audio/webm" });
          onRecordStop(blob);
          stream.getTracks().forEach(track => track.stop()); // Apagar micro
        };

        mediaRecorderRef.current = recorder;
        recorder.start();
        onRecordStart();
      } catch (e) {
        console.error("Error accediendo al micrófono:", e);
        alert("No se pudo acceder al micrófono.");
      }
    }
  };

  return (
    <>
      <div className="border-t border-slate-300 bg-white p-4 flex flex-col gap-2">
        
        {/* --- ÁREA DE PREVISUALIZACIÓN --- */}
        {attachedFile && (
          <div className="flex items-center gap-2 bg-blue-50 px-3 py-2 rounded-lg w-fit animate-fade-in border border-blue-100">
            <span className="text-xl">
              {attachedFile.kind === "image" ? "📷" : "📎"}
            </span>
            <span className="text-sm text-slate-700 truncate max-w-[250px] font-medium">
              {attachedFile.file.name}
            </span>
            <button 
              onClick={removeAttachment}
              className="ml-2 text-slate-400 hover:text-red-500 font-bold px-1"
              title="Quitar archivo"
            >
              ✕
            </button>
          </div>
        )}

        <div className="flex gap-3 items-center">
          {/* BOTÓN + MENU ADJUNTAR */}
          <div className="relative">
            <button
              disabled={disabled || isRecording}
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-10 h-10 border border-slate-500 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-600 text-2xl pb-1"
              title="Adjuntar"
            >
              +
            </button>

            {menuOpen && (
              <div className="absolute bottom-12 left-0 z-50">
                <UploadMenu
                  onFile={(file) => handleAttach(file, "file")}
                  onCamera={() => {
                    setCameraOpen(true);
                    setMenuOpen(false);
                  }}
                />
              </div>
            )}
          </div>

          {/* INPUT DE TEXTO O VISUALIZADOR DE GRABACIÓN */}
          {isRecording ? (
             <div className="flex-1 h-10 px-4 flex items-center bg-red-50 text-red-600 rounded-full border border-red-200 animate-pulse font-medium">
                🔴 Grabando nota de voz... (Clic en el micro para enviar)
             </div>
          ) : (
            <input
              value={message}
              disabled={disabled}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              className="flex-1 h-10 px-4 border border-slate-300 rounded-full 
                        bg-slate-100 text-slate-900
                        focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-slate-400"
              placeholder={attachedFile ? "Añade un comentario sobre el archivo..." : "Escribe un mensaje..."}
            />
          )}

          {/* BOTÓN MICRÓFONO */}
          <button
             onClick={toggleRecording}
             disabled={disabled || !!attachedFile} // Deshabilitar si hay archivo adjunto
             className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200
               ${isRecording 
                 ? "bg-red-500 text-white hover:bg-red-600 scale-110 shadow-md" 
                 : "text-slate-500 hover:bg-slate-100"
               }`}
             title={isRecording ? "Detener y enviar" : "Grabar voz"}
          >
             {/* Icono simple de micro o stop */}
             {isRecording ? (
               <div className="w-3 h-3 bg-white rounded-sm" />
             ) : (
               <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
             )}
          </button>

          {/* BOTÓN ENVIAR */}
          <button
            onClick={send}
            disabled={disabled || isRecording || (!message.trim() && !attachedFile)}
            className="
              px-6 h-10 rounded-full
              bg-[#0f2a44] text-white
              hover:bg-[#1a3b5a]
              disabled:opacity-50 disabled:cursor-not-allowed
              transition font-medium shadow-sm
            "
          >
            Enviar
          </button>
        </div>
      </div>

      {cameraOpen && (
        <CameraModal
          onCapture={(file) => {
            handleAttach(file, "image");
            setCameraOpen(false);
          }}
          onClose={() => setCameraOpen(false)}
        />
      )}
    </>
  );
}