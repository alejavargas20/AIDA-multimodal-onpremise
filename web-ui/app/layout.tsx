import "./globals.css";

export const metadata = {
  title: "AIDA",
  description: "Asistente Inteligente para Análisis Financiero",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="h-full">
        {children}
      </body>
    </html>
  );
}
