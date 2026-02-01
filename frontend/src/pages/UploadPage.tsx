import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowUpTrayIcon,
  DocumentIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useSettingsStore } from "../stores/settingsStore";
import { uploadFile, processFiles } from "../api/data";
import { pushToIndex } from "../api/nlp";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { StatusBadge } from "../components/ui/StatusBadge";
import { formatFileSize, generateId } from "../utils/helpers";
import type { UploadedFile } from "../api/types";

export function UploadPage() {
  const { projectId } = useSettingsStore();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [chunkSize, setChunkSize] = useState(512);
  const [overlapSize, setOverlapSize] = useState(50);
  const [doReset, setDoReset] = useState(false);
  const [resetIndex, setResetIndex] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const fileId = generateId();
      setFiles((prev) => [
        ...prev,
        { id: fileId, name: file.name, size: file.size, status: "uploading" },
      ]);
      try {
        const result = await uploadFile(projectId, file, () => {
          // Progress tracking could be added here
        });
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileId ?
              { ...f, status: "uploaded", id: result.file_id }
            : f,
          ),
        );
        return result;
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileId ?
              { ...f, status: "error", error: String(error) }
            : f,
          ),
        );
        throw error;
      }
    },
  });

  const processMutation = useMutation({
    mutationFn: () =>
      processFiles(projectId, {
        chunk_size: chunkSize,
        overlap_size: overlapSize,
        Do_reset: doReset ? 1 : 0,
      }),
  });

  const indexMutation = useMutation({
    mutationFn: () => pushToIndex(projectId, { do_reset: resetIndex }),
  });

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const droppedFiles = Array.from(e.dataTransfer.files);
      droppedFiles.forEach((file) => uploadMutation.mutate(file));
    },
    [uploadMutation],
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    selectedFiles.forEach((file) => uploadMutation.mutate(file));
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
          Upload & Process
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Upload documents, process them into chunks, and index to vector database
        </p>
      </div>

      {/* Upload Area */}
      <Card title="Upload Documents">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            dragOver ?
              "border-primary-500 bg-primary-500/5"
            : "border-border hover:border-border-hover"
          }`}
        >
          <ArrowUpTrayIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-primary font-medium mb-2">
            Drop files here or click to browse
          </p>
          <p className="text-text-muted text-sm mb-4">
            Supported formats: PDF, TXT, DOCX, MD
          </p>
          <label className="cursor-pointer">
            <input
              type="file"
              multiple
              accept=".pdf,.txt,.docx,.md"
              onChange={handleFileSelect}
              className="hidden"
            />
            <span className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors bg-bg-tertiary border border-border text-text-primary hover:bg-bg-hover">
              Select Files
            </span>
          </label>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 space-y-2">
            <h4 className="text-sm font-medium text-text-secondary">
              Uploaded Files
            </h4>
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 p-3 bg-bg-primary rounded-lg border border-border"
              >
                <DocumentIcon className="w-5 h-5 text-primary-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-text-muted">
                    {formatFileSize(file.size)}
                  </p>
                </div>
                {file.status === "uploading" && (
                  <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                )}
                {file.status === "uploaded" && (
                  <StatusBadge status="success" text="Done" />
                )}
                {file.status === "error" && (
                  <StatusBadge status="error" text="Error" />
                )}
                <button
                  onClick={() => removeFile(file.id)}
                  className="p-1 text-text-muted hover:text-error transition-colors"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Processing Configuration */}
      <Card title="Processing Configuration">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Chunk Size: {chunkSize}
            </label>
            <input
              type="range"
              min={100}
              max={2000}
              step={50}
              value={chunkSize}
              onChange={(e) => setChunkSize(parseInt(e.target.value))}
              className="w-full h-2 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <p className="text-xs text-text-muted mt-1">
              Number of characters per chunk
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Overlap Size: {overlapSize}
            </label>
            <input
              type="range"
              min={0}
              max={200}
              step={10}
              value={overlapSize}
              onChange={(e) => setOverlapSize(parseInt(e.target.value))}
              className="w-full h-2 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <p className="text-xs text-text-muted mt-1">
              Overlap between consecutive chunks
            </p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <input
            type="checkbox"
            id="doReset"
            checked={doReset}
            onChange={(e) => setDoReset(e.target.checked)}
            className="w-4 h-4 rounded border-border bg-bg-primary text-primary-500 focus:ring-primary-500"
          />
          <label htmlFor="doReset" className="text-sm text-text-secondary">
            Reset existing chunks before processing
          </label>
        </div>

        <div className="mt-6">
          <Button
            onPress={() => processMutation.mutate()}
            isLoading={processMutation.isPending}
            isDisabled={files.length === 0}
          >
            Process Files
          </Button>

          {processMutation.isSuccess && (
            <div className="mt-4 p-4 bg-success/10 border border-success/30 rounded-lg">
              <StatusBadge status="success" text="Processing Complete" />
              <p className="text-sm text-text-primary mt-2">
                Inserted {processMutation.data.Inserted_chunks} chunks from{" "}
                {processMutation.data.processed_files} files
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Index to Vector DB */}
      <Card title="Index to Vector Database">
        <div className="flex items-center gap-2 mb-4">
          <input
            type="checkbox"
            id="resetIndex"
            checked={resetIndex}
            onChange={(e) => setResetIndex(e.target.checked)}
            className="w-4 h-4 rounded border-border bg-bg-primary text-primary-500 focus:ring-primary-500"
          />
          <label htmlFor="resetIndex" className="text-sm text-text-secondary">
            Reset existing index before pushing
          </label>
        </div>

        <Button
          onPress={() => indexMutation.mutate()}
          isLoading={indexMutation.isPending}
          isDisabled={!processMutation.isSuccess}
        >
          Push to Vector DB
        </Button>

        {indexMutation.isSuccess && (
          <div className="mt-4 p-4 bg-success/10 border border-success/30 rounded-lg">
            <StatusBadge status="success" text="Indexing Complete" />
            <p className="text-sm text-text-primary mt-2">
              Indexed {indexMutation.data.InsertedItemsCount} items
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
