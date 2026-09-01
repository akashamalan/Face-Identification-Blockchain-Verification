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
      const url = URL.createObjectURL(file);
      setPreview(url);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      className={`glass-card p-8 text-center transition-all duration-300 cursor-pointer
        ${dragOver ? "border-accent-cyan glow-blue scale-[1.01]" : "hover:border-accent-blue/40"}
        ${disabled ? "opacity-50 pointer-events-none" : ""}`}
      onDrop={onDrop}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => !disabled && document.getElementById("file-input")?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={onInputChange}
        disabled={disabled}
      />

      {preview ? (
        <div className="space-y-4">
          <img
            src={preview}
            alt="Preview"
            className="mx-auto max-h-48 rounded-xl object-cover border border-glass-border"
          />
          <p className="text-sm text-gray-400">{fileName}</p>
        </div>
      ) : (
        <div className="space-y-3 py-6">
          <div className="text-5xl">📸</div>
          <p className="text-lg font-medium text-gray-300">
            Drop an image here or click to upload
          </p>
          <p className="text-sm text-gray-500">
            JPG, PNG, or WEBP · Max 10 MB · Must contain a face
          </p>
        </div>
      )}
    </div>
  );
}
