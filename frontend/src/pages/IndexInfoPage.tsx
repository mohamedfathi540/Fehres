import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { getIndexInfo } from "../api/nlp";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";

export function IndexInfoPage() {
  const [showJson, setShowJson] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["indexInfo"],
    queryFn: () => getIndexInfo(),
    enabled: false, // Don't fetch automatically
  });

  const collectionInfo = data?.CollectionInfo;
  const vectorsCount =
    collectionInfo?.vectors_count ??
    collectionInfo?.points_count ??
    collectionInfo?.record_count ??
    null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
            Index Information
          </h2>
          <p className="text-text-secondary mt-1">
            View vector database statistics for your project
          </p>
        </div>
        <Button
          onPress={() => refetch()}
          isLoading={isLoading}
          variant="secondary"
        >
          <ArrowPathIcon className="w-5 h-5" />
          Refresh
        </Button>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="text-center">
          <div className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-2">
            Collection Status
          </div>
          <div className="text-4xl font-bold text-success">
            {data ? "Active" : "-"}
          </div>
        </Card>

        <Card className="text-center">
          <div className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-2">
            Total Vectors
          </div>
          <div className="text-4xl font-bold text-primary-400">
            {typeof vectorsCount === "number" ?
              vectorsCount.toLocaleString()
            : "-"}
          </div>
        </Card>

      </div>

      {/* Error State */}
      {isError && (
        <Card className="border-error/50">
          <StatusBadge status="error" text="Error" />
          <p className="text-error mt-2">
            {error instanceof Error ?
              error.message
            : "Failed to fetch index info"}
          </p>
        </Card>
      )}

      {/* Raw JSON */}
      {data && (
        <Card
          title="Raw Response"
          actions={
            <Button
              variant="ghost"
              size="sm"
              onPress={() => setShowJson(!showJson)}
            >
              {showJson ? "Hide" : "Show"}
            </Button>
          }
        >
          {showJson && (
            <pre className="bg-bg-primary p-4 rounded-lg text-xs text-text-secondary overflow-x-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </Card>
      )}

      {/* Empty State */}
      {!data && !isLoading && !isError && (
        <Card className="text-center py-12">
          <p className="text-text-muted mb-4">
            Click refresh to load index information
          </p>
          <Button onPress={() => refetch()}>Load Index Info</Button>
        </Card>
      )}
    </div>
  );
}
