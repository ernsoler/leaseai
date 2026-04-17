import { useRef, useState } from 'react';

interface UploadZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export default function UploadZone({ onFile, disabled }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  function validateAndAccept(file: File) {
    setValidationError(null);
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setValidationError('Only PDF files are accepted');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setValidationError('File is too large. Maximum size is 20MB');
      return;
    }
    onFile(file);
  }

  return (
    <div>
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files[0];
          if (file) validateAndAccept(file);
        }}
        className={[
          'border-2 border-dashed rounded-2xl p-12 text-center transition-all',
          dragOver ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50',
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
        ].join(' ')}
      >
        <div className="text-5xl mb-4">📄</div>
        <p className="text-lg font-semibold text-gray-700 mb-2">Drop your lease PDF here</p>
        <p className="text-sm text-gray-400">or click to browse &middot; PDF only &middot; max 20MB</p>
      </div>
      {validationError && (
        <p className="mt-3 text-sm text-red-600 text-center">{validationError}</p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) validateAndAccept(file);
        }}
      />
    </div>
  );
}
