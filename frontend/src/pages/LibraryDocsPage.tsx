import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { GlobeAltIcon, PlusIcon, BookOpenIcon } from "@heroicons/react/24/outline";
import { scrapeDocumentation, getLibraries } from "../api/data";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import type { Library } from "../api/types";

export function LibraryDocsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newLibraryName, setNewLibraryName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [doReset, setDoReset] = useState(false);

  // Fetch Libraries
  const { data: librariesData, refetch: refetchLibraries } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const scrapeMutation = useMutation({
    mutationFn: () =>
      scrapeDocumentation({
        base_url: baseUrl,
        library_name: newLibraryName,
        Do_reset: doReset ? 1 : 0,
      }),
    onSuccess: () => {
      setNewLibraryName("");
      setBaseUrl("");
      setIsModalOpen(false);
      refetchLibraries(); // Refresh list after adding
    }
  });

  const handleScrape = (e: React.FormEvent) => {
    e.preventDefault();
    if (!baseUrl.trim() || !newLibraryName.trim()) return;
    scrapeMutation.mutate();
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
            Libraries
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Manage your documentation libraries.
          </p>
        </div>
        <Button onPress={() => setIsModalOpen(true)}>
          <PlusIcon className="w-5 h-5 mr-2" />
          Add Library
        </Button>
      </div>

      {/* Library List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {librariesData?.libraries?.map((lib: Library) => (
          <Card key={lib.id} title={lib.name} className="hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-primary-50 rounded-lg">
                <BookOpenIcon className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <p className="text-xs text-text-secondary">Project ID: {lib.id}</p>
              </div>
            </div>
            <div className="text-sm text-text-muted">
              Ready to chat.
            </div>
          </Card>
        ))}
        {librariesData?.libraries?.length === 0 && (
          <div className="col-span-full text-center py-10 text-text-muted">
            No libraries found. Add one to get started.
          </div>
        )}
      </div>


      {/* Add Library Modal (Simple Overlay) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-bg-primary rounded-xl shadow-xl max-w-md w-full p-6 border border-border">
            <h3 className="text-xl font-semibold text-text-primary mb-4">Add New Library</h3>

            <form onSubmit={handleScrape} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Library Name
                </label>
                <input
                  type="text"
                  value={newLibraryName}
                  onChange={(e) => setNewLibraryName(e.target.value)}
                  placeholder="e.g. FastAPI, React"
                  className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-text-primary focus:outline-none focus:border-primary-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Documentation URL
                </label>
                <div className="relative">
                  <GlobeAltIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                  <input
                    type="url"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://..."
                    className="w-full pl-9 pr-3 py-2 bg-bg-primary border border-border rounded-lg text-text-primary focus:outline-none focus:border-primary-500"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="doReset"
                  checked={doReset}
                  onChange={(e) => setDoReset(e.target.checked)}
                />
                <label htmlFor="doReset" className="text-sm text-text-secondary">
                  Reset content if exists
                </label>
              </div>

              {scrapeMutation.isError && (
                <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm text-error">
                  {scrapeMutation.error instanceof Error ? scrapeMutation.error.message : "Failed to start scraping"}
                </div>
              )}

              <div className="flex justify-end gap-3 mt-6">
                <Button variant="secondary" onPress={() => setIsModalOpen(false)} type="button">
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={scrapeMutation.isPending}
                  isDisabled={!baseUrl.trim() || !newLibraryName.trim() || !isValidUrl(baseUrl)}
                >
                  Start Scraping
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Scraping Status Toast/Banner - Simplified */}
      {scrapeMutation.isPending && (
        <div className="fixed bottom-4 right-4 bg-bg-primary border border-border shadow-lg p-4 rounded-lg flex items-center gap-3 z-50">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-500 border-t-transparent"></div>
          <div>
            <p className="text-sm font-medium text-text-primary">Scraping in progress...</p>
            <p className="text-xs text-text-muted">This may take a while.</p>
          </div>
        </div>
      )}
      {scrapeMutation.isSuccess && (
        <div className="fixed bottom-4 right-4 bg-success/10 border border-success/30 shadow-lg p-4 rounded-lg z-50">
          <p className="text-sm font-medium text-success">Scraping Started/Completed!</p>
        </div>
      )}

    </div>
  );
}
