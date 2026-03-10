import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { MagnifyingGlassIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { searchIndex } from "../api/nlp";
import { getLibraries } from "../api/data";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { truncateText } from "../utils/helpers";
import type { SearchResult } from "../api/types";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [expandedResults, setExpandedResults] = useState<Set<number>>(
    new Set(),
  );
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

  const searchMutation = useMutation({
    mutationFn: () =>
      searchIndex({
        text: query,
        limit,
        project_name: selectedLibrary?.name,
      }),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate();
  };

  const toggleResult = (index: number) => {
    setExpandedResults((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const results: SearchResult[] = searchMutation.data?.Results || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
          Search
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Search through your indexed documents using semantic search
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col gap-3">
            <div className="relative max-w-sm">
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

            <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={selectedLibrary ? `Search ${selectedLibrary.name}...` : "Select a library first"}
              className="flex-1 px-4 py-3 bg-bg-primary border border-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500"
              disabled={!selectedLibrary}
            />
            <Button
              type="submit"
              isLoading={searchMutation.isPending}
              isDisabled={!query.trim() || !selectedLibrary}
            >
              <MagnifyingGlassIcon className="w-5 h-5" />
              Search
            </Button>
          </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Results Limit: {limit}
            </label>
            <input
              type="range"
              min={1}
              max={20}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="w-full"
            />
          </div>
        </form>
      </Card>

      {/* Results */}
      {searchMutation.isSuccess && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-text-primary">
              Search Results
            </h3>
            <span className="text-sm text-text-secondary">
              Found {results.length} results
            </span>
          </div>

          {results.map((result, index) => {
            const isExpanded = expandedResults.has(index);
            return (
              <Card key={index} className="animate-slide-up">
                <div
                  className="flex items-start justify-between cursor-pointer"
                  onClick={() => toggleResult(index)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium text-primary-400">
                        Result #{index + 1}
                      </span>
                      <span className="text-sm text-warning font-semibold">
                        Score: {result.score.toFixed(4)}
                      </span>
                    </div>
                    <p className="text-text-primary">
                      {isExpanded ?
                        result.text
                      : truncateText(result.text, 200)}
                    </p>
                  </div>
                  <button className="ml-4 text-text-muted hover:text-text-primary">
                    {isExpanded ? "▼" : "▶"}
                  </button>
                </div>

                {isExpanded && result.metadata && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <h4 className="text-sm font-medium text-text-secondary mb-2">
                      Metadata
                    </h4>
                    <pre className="bg-bg-primary p-3 rounded-lg text-xs text-text-secondary overflow-x-auto">
                      {JSON.stringify(result.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {searchMutation.isError && (
        <Card className="border-error/50">
          <p className="text-error">
            Error:{" "}
            {searchMutation.error instanceof Error ?
              searchMutation.error.message
            : "Search failed"}
          </p>
        </Card>
      )}
    </div>
  );
}
