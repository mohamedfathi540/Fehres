import { useState, useRef, useCallback } from "react";
import { analyzePrescription } from "../api/prescription";
import type { MedicineInfo } from "../api/types";
import { Button } from "../components/ui/Button";
import { useSettingsStore } from "../stores/settingsStore";

/** Convert a File to a data URL so it survives page switches */
function fileToDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

export function PrescriptionPage() {
    const { prescriptionResult, setPrescriptionResult } = useSettingsStore();

    const [file, setFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(
        prescriptionResult?.previewDataUrl ?? null
    );
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [ocrText, setOcrText] = useState<string>(
        prescriptionResult?.ocrText ?? ""
    );
    const [medicines, setMedicines] = useState<MedicineInfo[]>(
        prescriptionResult?.medicines ?? []
    );
    const [error, setError] = useState<string | null>(null);
    const [showOcr, setShowOcr] = useState(false);
    const [signal, setSignal] = useState<string>(
        prescriptionResult?.signal ?? ""
    );
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleFile = useCallback(async (f: File) => {
        setFile(f);
        setError(null);
        // Don't clear previous results until new analysis is run
        const dataUrl = await fileToDataUrl(f);
        setPreviewUrl(dataUrl);
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
            const newOcrText = result.ocr_text || "";
            const newMedicines = result.medicines || [];
            const newSignal = result.signal || "";
            const newProjectId = result.project_id ?? null;

            setOcrText(newOcrText);
            setMedicines(newMedicines);
            setSignal(newSignal);

            // Persist to store so results survive page switches
            setPrescriptionResult({
                ocrText: newOcrText,
                medicines: newMedicines,
                signal: newSignal,
                previewDataUrl: previewUrl,
                projectId: newProjectId,
            });
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
        setPreviewUrl(null);
        setMedicines([]);
        setOcrText("");
        setError(null);
        setSignal("");
        setShowOcr(false);
        setPrescriptionResult(null);
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
                className={`relative border-2 border-dashed rounded-xl p-4 sm:p-8 text-center transition-all duration-200 cursor-pointer ${isDragging
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
                                📄 {file?.name ?? "Previous prescription"}{" "}
                                {file && (
                                    <span className="text-text-muted">
                                        ({((file.size || 0) / 1024).toFixed(1)} KB)
                                    </span>
                                )}
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
            {(file || (previewUrl && !medicines.length)) && (
                <div className="flex gap-3">
                    <Button
                        onPress={handleAnalyze}
                        isLoading={isAnalyzing}
                        variant="primary"
                        isDisabled={!file}
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
                                Running OCR → Extracting medicines → Indexing for chat
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
                        <div className="flex items-center gap-2">
                            <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">
                                {signal}
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onPress={handleReset}
                            >
                                New Analysis
                            </Button>
                        </div>
                    </div>

                    <div className="grid gap-4">
                        {medicines.map((med, idx) => (
                            <div
                                key={idx}
                                className="bg-bg-secondary border border-border rounded-xl p-5 hover:border-primary-600/50 transition-colors"
                            >
                                {/* Medicine Info */}
                                <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-lg font-bold text-text-primary">
                                            <span className="text-primary-400 mr-1.5">
                                                {idx + 1}.
                                            </span>
                                            {med.name}
                                        </h3>
                                        <div className="mt-2">
                                            <p className="text-xs font-medium text-text-muted uppercase tracking-wider">
                                                Active Ingredient
                                            </p>
                                            <p className="text-text-secondary mt-0.5">
                                                {med.active_ingredient || "Not found"}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Google Image Search Link */}
                                    {med.image_url && (
                                        <a
                                            href={med.image_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="shrink-0 self-start flex items-center gap-2 px-4 py-2.5 bg-primary-600/20 hover:bg-primary-600/30 text-primary-400 rounded-lg border border-primary-600/30 transition-all duration-200 hover:scale-105 text-sm font-medium"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            🔍 View Images
                                        </a>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Tip to use Chat */}
                    {prescriptionResult?.projectId && (
                        <div className="bg-primary-600/10 border border-primary-600/30 rounded-xl p-4">
                            <p className="text-primary-400 font-medium">💬 Chat Available</p>
                            <p className="text-primary-300/80 text-sm mt-1">
                                Go to the <strong>Chat</strong> page to ask questions about these
                                medicines — find replacements, check interactions, and more.
                            </p>
                        </div>
                    )}
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
