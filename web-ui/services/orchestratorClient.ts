//aida-multimodal-onpremise/web-ui/services/orchestratorClient.ts

import { User } from "@/types/user";

console.log("orchestratorClient LOADED");

type OrchestratorResponse = {
  output_type: "text" | "json";
  content: string;
};

export async function sendToOrchestrator(
  user: User,
  sessionId: string,
  inputType: "text" | "image" | "pdf" | "audio",
  content: string | File,
  extraMetadata: Record<string, any> = {} // NUEVO PARÁMETRO
): Promise<OrchestratorResponse> {

  let payloadContent = content;

  // Si es archivo o imagen convertimos a base64 (Mantenemos tu lógica actual)
  if (content instanceof File) {
    const buffer = await content.arrayBuffer();
    // Truco para evitar stack overflow en archivos grandes con spread operator
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    payloadContent = btoa(binary);
  } else {
    payloadContent = content as string;
  }

  const payload = {
    user_id: user.user_id,
    session_id: sessionId,
    input_type: inputType,
    content: payloadContent, // Base64 si es archivo, texto si es texto
    metadata: {
        language: "es",
        timestamp: new Date().toISOString(),
        user_role: user.role.toLowerCase(), 
        client_id: user.client_id || "",
        encoding: content instanceof File ? "base64" : "plain",
        ...extraMetadata // Agregamos los metadatos extra aquí
    }
  };

  try {
      const res = await fetch("http://localhost:8000/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            tool_name: "orchestrator.entry", 
            payload
        })
      });

      if (!res.ok) {
        // Intentar leer el error del backend si existe
        const errText = await res.text();
        throw new Error(`Error del orquestador (${res.status}): ${errText}`);
      }

      const data = await res.json();

      // Transformamos la respuesta a un formato limpio
      let finalContent = "";
      
      // Lógica para extraer el contenido final
      if (data.result?.final_text) {
          finalContent = data.result.final_text;
      } else if (typeof data.result?.content?.output === "string") {
          finalContent = data.result.content.output;
      } else if (typeof data.result === "string") {
          finalContent = data.result;
      } else {
          finalContent = JSON.stringify(data.result);
      }

      return {
        output_type: "text",
        content: finalContent
      };

  } catch (error) {
      console.error("Error en sendToOrchestrator:", error);
      throw error;
  }
}