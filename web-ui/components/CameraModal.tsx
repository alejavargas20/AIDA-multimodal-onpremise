// aida-multimodal-onpremise/web-ui/components/CameraModal.tsx
"use client";

import { useEffect, useRef } from "react";

type CameraModalProps = {
  onCapture: (file: File) => void;
  onClose: () => void;
};

export default function CameraModal({ onCapture, onClose }: CameraModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    async function startCamera() {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    }

    startCamera();

    return () => stopCamera();
  }, []);

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const takePhoto = () => {
    const video = videoRef.current!;
    const canvas = document.createElement("canvas");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d")!;
    
    ctx.drawImage(video, 0, 0);

    // Guardamos con calidad máxima (1.0) para que el OCR no falle
    canvas.toBlob((blob) => {
      if (!blob) return;

      const file = new File([blob], "foto.jpg", { type: "image/jpeg" });
      onCapture(file);
      stopCamera();
      onClose();
    }, "image/jpeg", 1.0);
  };

  // return (
  //   <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
  //     <div className="bg-white rounded-lg p-4 space-y-4">
  //       <video ref={videoRef} autoPlay playsInline className="w-96 rounded" />

  //       <div className="flex justify-between">
  //         <button
  //           onClick={() => {
  //             stopCamera();
  //             onClose();
  //           }}
  //           className="px-4 py-2 border rounded"
  //         >
  //           Cancelar
  //         </button>

  //         <button
  //           onClick={takePhoto}
  //           className="px-4 py-2 bg-blue-600 text-white rounded"
  //         >
  //           Tomar foto
  //         </button>
  //       </div>
  //     </div>
  //   </div>
  // );


  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-4 space-y-4 shadow-xl">
        <div className="relative">
          {/* 🚨 EL TRUCO DEL ESPEJO: 
            Usamos transform: scaleX(-1) para que el video funcione como un espejo real. 
            El texto se verá al revés para ti, ¡pero es normal! Esto hace que cuadrar la hoja sea súper fácil.
          */}
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            className="w-[500px] max-w-full rounded bg-slate-900"
            style={{ transform: "scaleX(-1)" }} 
          />
          <div className="absolute top-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
            Modo Espejo (El texto se lee al revés)
          </div>
        </div>

        <div className="flex justify-between mt-4">
          <button
            onClick={() => {
              stopCamera();
              onClose();
            }}
            className="px-6 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 font-medium transition-colors"
          >
            Cancelar
          </button>

          <button
            onClick={takePhoto}
            className="px-6 py-2 bg-[#0f2a44] text-white rounded font-medium hover:bg-[#1a3b5a] shadow-sm transition-colors"
          >
            Tomar foto
          </button>
        </div>
      </div>
    </div>
  );
}
