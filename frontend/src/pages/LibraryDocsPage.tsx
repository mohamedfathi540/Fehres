import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { GlobeAltIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { scrapeDocumentation, cancelScrapeDocumentation, processScrapeCache } from "../api/data";
import { pushToIndex } from "../api/nlp";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { StatusBadge } from "../components/ui/StatusBadge";

export function LibraryDocsPage() {
  const [baseUrl, setBaseUrl] = useState("");
  const [doReset, setDoReset] = useState(false);
  const [resetIndex, setResetIndex] = useState(false);

  const scrapeMutation = useMutation({
    mutationFn: () =>
      scrapeDocumentation({
        base_url: baseUrl,
        Do_reset: doReset ? 1 : 0,
      }),
  });

  const indexMutation = useMutation({
    mutationFn: () => pushToIndex({ do_reset: resetIndex ? 1 : 0 }),
  });

  const processCacheMutation = useMutation({
    mutationFn: () => processScrapeCache(baseUrl.trim()),
  });

  const handleScrape = (e: React.FormEvent) => {
    e.preventDefault();
    if (!baseUrl.trim()) return;
    scrapeMutation.mutate();
  };

  const handleCancelScrape = async () => {
    await cancelScrapeDocumentation();
    scrapeMutation.reset();
  };

  const isValidUrl = (url: string) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
          Library Documentation
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Scrape library documentation from a URL and index it for search
        </p>
      </div>

      {/* Scraping Configuration */}
      <Card title="Scrape Documentation">
        <form onSubmit={handleScrape} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Documentation Base URL
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <GlobeAltIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="url"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://docs.example.com"
                  className="w-full pl-10 pr-4 py-3 bg-bg-primary border border-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500"
                />
              </div>
              <Button
                type="submit"
                isLoading={scrapeMutation.isPending}
                isDisabled={!baseUrl.trim() || !isValidUrl(baseUrl)}
              >
                <ArrowPathIcon className="w-5 h-5" />
                Scrape
              </Button>
              {scrapeMutation.isPending && (
                <Button
                  type="button"
                  onPress={handleCancelScrape}
                  variant="secondary"
                >
                  Cancel
                </Button>
              )}
            </div>
            <p className="text-xs text-text-muted mt-2">
              Enter the base URL of the library documentation (e.g., https://python.langchain.com)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="doReset"
              checked={doReset}
              onChange={(e) => setDoReset(e.target.checked)}
            />
            <label htmlFor="doReset" className="text-sm text-text-secondary">
              Reset existing content before scraping
            </label>
          </div>

          {scrapeMutation.isSuccess && scrapeMutation.data.signal === "cancelled" && (
            <div className="mt-4 p-4 bg-warning/10 border border-warning/30 rounded-lg">
              <StatusBadge status="warning" text="Scrape cancelled" />
              <p className="text-sm text-text-primary mt-2">
                Cancelled. {(scrapeMutation.data as { partial_pages_scraped?: number }).partial_pages_scraped ?? 0} pages were scraped before cancel.
              </p>
            </div>
          )}
          {scrapeMutation.isSuccess && scrapeMutation.data.signal !== "cancelled" && (
            <div className="mt-4 p-4 bg-success/10 border border-success/30 rounded-lg">
              <StatusBadge status="success" text="Scraping Complete" />
              <p className="text-sm text-text-primary mt-2">
                Scraped {scrapeMutation.data.total_pages_scraped} pages and created{" "}
                {scrapeMutation.data.Inserted_chunks} chunks from{" "}
                {scrapeMutation.data.processed_pages} pages
              </p>
            </div>
          )}

          {scrapeMutation.isError && (
            <div className="mt-4 p-4 bg-error/10 border border-error/30 rounded-lg">
              <StatusBadge status="error" text="Scraping Failed" />
              <p className="text-sm text-text-primary mt-2">
                {scrapeMutation.error instanceof Error
                  ? scrapeMutation.error.message
                  : "Failed to scrape documentation"}
              </p>
            </div>
          )}
        </form>
      </Card>

      {/* Complete from cache (after frontend timeout) */}
      <Card title="Complete chunking from cache (no refetch)">
        <p className="text-sm text-text-secondary mb-3">
          If the scrape finished on the backend but the frontend timed out, the last scrape is cached.
          Enter the same base URL and run this to run chunking only, then push to index below.
        </p>
        <div className="flex gap-2 items-center">
          <input
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://docs.flet.dev"
            className="flex-1 px-4 py-2 bg-bg-primary border border-border rounded-lg text-text-primary"
          />
          <Button
            onPress={() => processCacheMutation.mutate()}
            isLoading={processCacheMutation.isPending}
            isDisabled={!baseUrl.trim()}
          >
            Complete from cache
          </Button>
        </div>
        {processCacheMutation.isSuccess && (
          <p className="text-sm text-success mt-2">
            Chunking done: {processCacheMutation.data.Inserted_chunks} chunks from{" "}
            {processCacheMutation.data.processed_pages} pages. Now click &quot;Push to Vector DB&quot; below.
          </p>
        )}
        {processCacheMutation.isError && (
          <p className="text-sm text-error mt-2">
            {processCacheMutation.error instanceof Error
              ? processCacheMutation.error.message
              : "No cache or error"}
          </p>
        )}
      </Card>

      {/* Index to Vector DB */}
      <Card title="Index to Vector Database">
        <p className="text-sm text-text-secondary mb-2">
          If the frontend timed out but the backend had already finished scraping, you can push
          existing chunks to the vector DB without re-scraping.
        </p>
        <div className="flex items-center gap-2 mb-4">
          <input
            type="checkbox"
            id="resetIndex"
            checked={resetIndex}
            onChange={(e) => setResetIndex(e.target.checked)}
          />
          <label htmlFor="resetIndex" className="text-sm text-text-secondary">
            Reset existing index before pushing
          </label>
        </div>

        <Button
          onPress={() => indexMutation.mutate()}
          isLoading={indexMutation.isPending}
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
