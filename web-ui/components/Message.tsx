export default function TopBar({ user, onLogout }: any) {
  return (
    <header className="h-16 bg-white border-b flex items-center justify-between px-6">
      <div>
        <h1 className="text-xl font-semibold text-[#0f2a44]">
          AIDA
        </h1>
        <p className="text-xs text-slate-500">
          Asistente Inteligente para Análisis Financiero
        </p>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-600">
          Usuario: <b>{user}</b>
        </span>
        <button
          onClick={onLogout}
          className="text-sm border px-3 py-1 rounded hover:bg-slate-100"
        >
          Cerrar sesión
        </button>
      </div>
    </header>
  );
}
