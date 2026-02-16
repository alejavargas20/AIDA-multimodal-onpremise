// aida-multimodal-onpremise/web-ui/components/UploadMenu.tsx

type UploadMenuProps = {
  onFile: (file: File) => void;
  onCamera: () => void;
};

export default function UploadMenu({ onFile, onCamera }: UploadMenuProps) {
  return (
    <div className="bg-white border rounded shadow w-40">
      <label className="block px-4 py-2 cursor-pointer hover:bg-slate-100">
        📎Adjuntar archivos
        <input
          type="file"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) onFile(e.target.files[0]);
          }}
        />
      </label>

      <button
        onClick={onCamera}
        className="w-full text-left px-4 py-2 hover:bg-slate-100"
      >
        📷 Cámara
      </button>
    </div>
  );
}
