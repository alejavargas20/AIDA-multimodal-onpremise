// aida-multimodal-onpremise/web-ui/components/Sidebar.tsx

type ChatSession = {
  session_id: string;
  started_at: string;
};

type SidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  disabled: boolean;
};

export default function Sidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  disabled,
}: SidebarProps) {
  return (
    <aside className="w-64 bg-slate-100 border-r border-slate-300 p-4 flex flex-col gap-4">
      
      {/* Nuevo chat */}
      <button
        onClick={onNewChat}
        disabled={disabled}
        className="
          w-full px-4 py-3 rounded-md border border-slate-400 text-sm
          hover:bg-slate-200 transition
          disabled:opacity-50 disabled:cursor-not-allowed
        "
      >
        + Nuevo chat
      </button>

      {/* Historial */}
      <div className="flex-1 overflow-y-auto">
        <p className="text-xs font-semibold text-slate-500 mb-2">
          Historial
        </p>

        {sessions.length === 0 && (
          <p className="text-xs text-slate-400">
            No hay chats todavía
          </p>
        )}

        <ul className="space-y-1">
          {sessions.map((s) => {
            const isActive = s.session_id === activeSessionId;

            return (
              <li key={s.session_id}>
                <button
                  onClick={() => onSelectSession(s.session_id)}
                  className={`
                    w-full text-left px-3 py-2 rounded-md text-sm
                    transition
                    ${
                      isActive
                        ? "bg-blue-100 text-blue-800 font-medium"
                        : "hover:bg-slate-200 text-slate-700"
                    }
                  `}
                >
                  {" "}
                  {new Date(s.started_at).toLocaleString("es-ES", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
