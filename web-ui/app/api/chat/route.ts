import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const payload = await req.json();

  // Aquí irá el orquestador real
  // const res = await fetch("http://localhost:8000/orchestrate", ...)

  return NextResponse.json({
    content: "AIDA recibió tu mensaje correctamente.",
  });
}
