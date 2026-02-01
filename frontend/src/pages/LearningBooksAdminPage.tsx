import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowPathIcon,
  CubeIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
} from "@heroicons/react/24/outline";
import { processFiles } from "../api/data";
import { pushToIndex } from "../api/nlp";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

const LEARNING_BOOKS_PROJECT_ID = 10;

type Status = "idle" | "success" | "error";
type Message = { type: Status; text: string } | null;

export function LearningBooksAdminPage() {
  const [resetChunks, setResetChunks] = useState(false);
  const [resetIndex, setResetIndex] = useState(false);
  const [processMessage, setProcessMessage] = useState<Message>(null);
  const [indexMessage, setIndexMessage] = useState<Message>(null);
  const [resetMessage, setResetMessage] = useState<Message>(null);

  const processMutation = useMutation({
    mutationFn: () =>
      processFiles(LEARNING_BOOKS_PROJECT_ID, {
        chunk_size: 2000,
        overlap_size: 200,
        Do_reset: resetChunks ? 1 : 0,
      }),
    onSuccess: () => {
      setProcessMessage({ type: "success", text: "Processing complete." });
      setIndexMessage(null);
    },
    onError: (err) => {
      setProcessMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Processing failed.",
      });
    },
  });

  const indexMutation = useMutation({
    mutationFn: () =>
      pushToIndex(LEARNING_BOOKS_PROJECT_ID, { do_reset: resetIndex }),
    onSuccess: (data) => {
      setIndexMessage({
        type: "success",
        text:
          data.InsertedItemsCount != null ?
            `Indexing complete. ${data.InsertedItemsCount} items indexed.`
          : "Indexing complete.",
      });
      setProcessMessage(null);
    },
    onError: (err) => {
      setIndexMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Indexing failed.",
      });
    },
  });

  const runReset = async () => {
    setResetMessage(null);
    try {
      await processFiles(LEARNING_BOOKS_PROJECT_ID, {
        chunk_size: 2000,
        overlap_size: 200,
        Do_reset: 1,
      });
      await pushToIndex(LEARNING_BOOKS_PROJECT_ID, { do_reset: true });
      setResetMessage({ type: "success", text: "Reset complete." });
      setProcessMessage(null);
      setIndexMessage(null);
    } catch (err) {
      setResetMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Reset failed.",
      });
      throw err;
    }
  };

  const resetMutation = useMutation({
    mutationFn: runReset,
    onError: (err) => {
      setResetMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Reset failed.",
      });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">
          Learning Books
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Process and index the reference corpus. Upload files first from Upload
          & Process with project ID 10.
        </p>
      </div>

      <Card
        title="Actions"
        subtitle="Process uploaded files, then index for search and chat."
      >
        <div className="space-y-6">
          {/* Process */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="resetChunks"
                checked={resetChunks}
                onChange={(e) => setResetChunks(e.target.checked)}
              />
              <label
                htmlFor="resetChunks"
                className="text-sm text-text-secondary"
              >
                Reset chunks before processing
              </label>
            </div>
            <Button
              onPress={() => processMutation.mutate()}
              isLoading={processMutation.isPending}
              variant="secondary"
            >
              <CubeIcon className="w-5 h-5" />
              Process
            </Button>
            {processMessage && (
              <span
                className={`inline-flex items-center gap-1.5 text-sm ${
                  processMessage.type === "success" ?
                    "text-success"
                  : "text-error"
                }`}
              >
                {processMessage.type === "success" ?
                  <CheckCircleIcon className="w-4 h-4" />
                : <XCircleIcon className="w-4 h-4" />}
                {processMessage.text}
              </span>
            )}
          </div>

          {/* Index */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="resetIndex"
                checked={resetIndex}
                onChange={(e) => setResetIndex(e.target.checked)}
              />
              <label
                htmlFor="resetIndex"
                className="text-sm text-text-secondary"
              >
                Reset index before pushing
              </label>
            </div>
            <Button
              onPress={() => indexMutation.mutate()}
              isLoading={indexMutation.isPending}
              variant="secondary"
            >
              <ArrowPathIcon className="w-5 h-5" />
              Index
            </Button>
            {indexMessage && (
              <span
                className={`inline-flex items-center gap-1.5 text-sm ${
                  indexMessage.type === "success" ?
                    "text-success"
                  : "text-error"
                }`}
              >
                {indexMessage.type === "success" ?
                  <CheckCircleIcon className="w-4 h-4" />
                : <XCircleIcon className="w-4 h-4" />}
                {indexMessage.text}
              </span>
            )}
          </div>

          {/* Reset */}
          <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-border">
            <Button
              onPress={() => resetMutation.mutate()}
              isLoading={resetMutation.isPending}
              variant="danger"
            >
              <TrashIcon className="w-5 h-5" />
              Reset
            </Button>
            <span className="text-sm text-text-muted">
              Clear all chunks and index for this corpus.
            </span>
            {resetMessage && (
              <span
                className={`inline-flex items-center gap-1.5 text-sm ${
                  resetMessage.type === "success" ?
                    "text-success"
                  : "text-error"
                }`}
              >
                {resetMessage.type === "success" ?
                  <CheckCircleIcon className="w-4 h-4" />
                : <XCircleIcon className="w-4 h-4" />}
                {resetMessage.text}
              </span>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
