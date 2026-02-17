import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowPathIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { getIndexInfo } from "../api/nlp";
import { getLibraries } from "../api/data";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";

export function IndexInfoPage() {
  const [showJson, setShowJson] = useState(false);
  const [selectedLibraryId, setSelectedLibraryId] = useState<number | null>(null);

  const { data: librariesData } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const libraries = librariesData?.libraries || [];
  const selectedLibrary = libraries.find((lib) => lib.id === selectedLibraryId);

  useEffect(() => {
    if (!selectedLibraryId && libraries.length > 0) {
      setSelectedLibraryId(libraries[0].id);
    }
  }, [libraries, selectedLibraryId]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["indexInfo", selectedLibrary?.name],
    queryFn: () => getIndexInfo(selectedLibrary?.name),
    enabled: false, // Don't fetch automatically
  });

  const collectionInfo = data?.CollectionInfo;
  const vectorsCount =
    collectionInfo?.record_count ??
    collectionInfo?.vectors_count ??
    collectionInfo?.points_count ??
    null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
            Index Information
          </h2>
          <p className="text-text-secondary mt-1">
            View vector database statistics for your project
          </p>
        </div>
        <div className="relative w-64">
          <label className="block text-xs font-medium text-text-secondary mb-1">
            Select Library
          </label>
          <div className="relative">
            <select
              value={selectedLibraryId || ""}
              onChange={(e) => setSelectedLibraryId(Number(e.target.value))}
              className="w-full appearance-none bg-bg-primary border border-border text-text-primary px-4 py-2 pr-8 rounded-lg focus:outline-none focus:border-primary-500 cursor-pointer"
              disabled={libraries.length === 0}
            >
              {libraries.length === 0 ? (
                <option value="">No libraries available</option>
              ) : (
                libraries.map((lib) => (
                  <option key={lib.id} value={lib.id}>
                    {lib.name}
                  </option>
                ))
              )}
            </select>
            <ChevronDownIcon className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          </div>
        </div>
        <Button
          onPress={() => refetch()}
          isLoading={isLoading}
          variant="secondary"
          isDisabled={!selectedLibrary}
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

        <Card className="text-center">
          <div className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-2">
            Collection Name
          </div>
          <div className="text-base font-semibold text-text-primary">
            {collectionInfo?.table_info?.table_name ?? "-"}
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
