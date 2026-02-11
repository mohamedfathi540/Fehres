import { useState, useRef, useCallback } from "react";
import { analyzePrescription } from "../api/prescription";
import type { MedicineInfo } from "../api/types";
import { Button } from "../components/ui/Button";

export function PrescriptionPage() {
    const [file, setFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [ocrText, setOcrText] = useState<string>("");
    const [medicines, setMedicines] = useState<MedicineInfo[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [showOcr, setShowOcr] = useState(false);
    const [signal, setSignal] = useState<string>("");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleFile = useCallback((f: File) => {
        setFile(f);
        setError(null);
        setMedicines([]);
        setOcrText("");
        setSignal("");

        // Create preview
        const url = URL.createObjectURL(f);
        setPreviewUrl(url);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setIsDragging(false);
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile) handleFile(droppedFile);
        },
        [handleFile]
    );

    const handleAnalyze = async () => {
        if (!file) return;
        setIsAnalyzing(true);
        setProgress(0);
        setError(null);
        setMedicines([]);
        setOcrText("");
        setSignal("");

        try {
            const result = await analyzePrescription(file, setProgress);
            setOcrText(result.ocr_text || "");
            setMedicines(result.medicines || []);
            setSignal(result.signal || "");
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : "Analysis failed";
            setError(message);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
        setMedicines([]);
        setOcrText("");
        setError(null);
        setSignal("");
        setShowOcr(false);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-text-primary">
                    💊 Prescription Analyzer
                </h1>
                <p className="text-text-secondary mt-1">
                    Upload a prescription image to extract medicine names, active
                    ingredients, and pictures.
                </p>
            </div>

            {/* Upload Zone */}
            <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer ${isDragging
                        ? "border-primary-500 bg-primary-500/10"
                        : previewUrl
                            ? "border-border bg-bg-secondary"
                            : "border-border hover:border-primary-600 hover:bg-bg-secondary/50"
                    }`}
                onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => !previewUrl && fileInputRef.current?.click()}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    className="hidden"
                    onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFile(f);
                    }}
                />

                {previewUrl ? (
                    <div className="space-y-4">
                        <img
                            src={previewUrl}
                            alt="Prescription preview"
                            className="max-h-64 mx-auto rounded-lg shadow-lg"
                        />
                        <div className="flex items-center justify-center gap-3">
                            <p className="text-sm text-text-secondary">
                                📄 {file?.name}{" "}
                                <span className="text-text-muted">
                                    ({((file?.size || 0) / 1024).toFixed(1)} KB)
                                </span>
                            </p>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleReset();
                                }}
                                className="text-xs text-red-400 hover:text-red-300 underline"
                            >
                                Remove
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <div className="text-5xl">📋</div>
                        <p className="text-text-secondary font-medium">
                            Drop your prescription image here
                        </p>
                        <p className="text-sm text-text-muted">
                            or click to browse · JPG, PNG, WebP, PDF
                        </p>
                    </div>
                )}
            </div>

            {/* Analyze Button */}
            {file && (
                <div className="flex gap-3">
                    <Button
                        onPress={handleAnalyze}
                        isLoading={isAnalyzing}
                        variant="primary"
                    >
                        {isAnalyzing
                            ? progress < 100
                                ? `Uploading... ${progress}%`
                                : "Analyzing prescription..."
                            : "🔍 Analyze Prescription"}
                    </Button>
                    {!isAnalyzing && (
                        <Button onPress={handleReset} variant="ghost">
                            Clear
                        </Button>
                    )}
                </div>
            )}

            {/* Loading Indicator */}
            {isAnalyzing && (
                <div className="bg-bg-secondary rounded-xl p-6 border border-border">
                    <div className="flex items-center gap-3">
                        <div className="animate-spin w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full" />
                        <div>
                            <p className="text-text-primary font-medium">
                                Processing prescription...
                            </p>
                            <p className="text-sm text-text-muted mt-0.5">
                                Running OCR → Extracting medicines → Searching for info
                            </p>
                        </div>
                    </div>
                    {progress > 0 && progress < 100 && (
                        <div className="mt-3 w-full bg-bg-tertiary rounded-full h-2">
                            <div
                                className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                    <p className="text-red-400 font-medium">⚠️ Error</p>
                    <p className="text-red-300 text-sm mt-1">{error}</p>
                </div>
            )}

            {/* Results */}
            {medicines.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-text-primary">
                            🏥 Medicines Found ({medicines.length})
                        </h2>
                        <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">
                            {signal}
                        </span>
                    </div>

                    <div className="grid gap-4">
                        {medicines.map((med, idx) => (
                            <div
                                key={idx}
                                className="bg-bg-secondary border border-border rounded-xl p-5 flex gap-5 items-start hover:border-primary-600/50 transition-colors"
                            >
                                {/* Medicine Image */}
                                <div className="shrink-0">
                                    {med.image_url ? (
                                        <img
                                            src={med.image_url}
                                            alt={med.name}
                                            className="w-24 h-24 object-cover rounded-lg border border-border shadow-md"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = "none";
                                            }}
                                        />
                                    ) : (
                                        <div className="w-24 h-24 bg-bg-tertiary rounded-lg flex items-center justify-center text-3xl border border-border">
                                            💊
                                        </div>
                                    )}
                                </div>

                                {/* Medicine Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2">
                                        <h3 className="text-lg font-bold text-text-primary">
                                            <span className="text-primary-400 mr-1.5">
                                                {idx + 1}.
                                            </span>
                                            {med.name}
                                        </h3>
                                    </div>
                                    <div className="mt-2">
                                        <p className="text-xs font-medium text-text-muted uppercase tracking-wider">
                                            Active Ingredient
                                        </p>
                                        <p className="text-text-secondary mt-0.5">
                                            {med.active_ingredient || "Not found"}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Signal when no medicines found */}
            {signal && medicines.length === 0 && !isAnalyzing && !error && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                    <p className="text-yellow-400 font-medium">ℹ️ {signal}</p>
                    <p className="text-yellow-300/80 text-sm mt-1">
                        The OCR was performed but no medicine names could be extracted. Try
                        a clearer image.
                    </p>
                </div>
            )}

            {/* OCR Text (collapsible) */}
            {ocrText && (
                <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
                    <button
                        onClick={() => setShowOcr(!showOcr)}
                        className="w-full px-5 py-3 flex items-center justify-between hover:bg-bg-hover transition-colors"
                    >
                        <span className="text-sm font-medium text-text-secondary">
                            📝 Raw OCR Text
                        </span>
                        <span className="text-text-muted text-xs">
                            {showOcr ? "▲ Hide" : "▼ Show"}
                        </span>
                    </button>
                    {showOcr && (
                        <div className="px-5 pb-4 border-t border-border pt-3">
                            <pre className="text-sm text-text-muted whitespace-pre-wrap font-mono leading-relaxed">
                                {ocrText}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
