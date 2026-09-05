import { useCallback, useState } from "react";

interface Props {
  onFileSelected: (file: File) => void;
  disabled: boolean;
}

export function ImageUpload({ onFileSelected, disabled }: Props) {
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      setFileName(file.name);
      setPreview(URL.createObjectURL(file));
      onFileSelected(file);
    },
    [onFileSelected],
  );

  return (
    <div
      className="dropzone p-6 text-center"
      data-over={dragOver}
      style={disabled ? { pointerEvents: "none" } : undefined}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => !disabled && document.getElementById("file-input")?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
        disabled={disabled}
      />

      {preview ? (
        <div className="flex flex-col items-center gap-3">
          <img
            src={preview}
            alt="Uploaded face"
            className="max-h-56 img-frame img-frame-lg"
            style={{ objectFit: "contain" }}
          />
          <p className="mono-break m-0">{fileName}</p>
        </div>
      ) : (
        <div className="py-8">
          <p
            className="m-0 mb-2"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl2)" }}
          >
            Drop a face image
          </p>
          <p className="eyebrow m-0">jpg · png · webp — max 10 mb — one face</p>
        </div>
      )}
    </div>
  );
}
