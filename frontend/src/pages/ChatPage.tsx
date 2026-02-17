import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PaperAirplaneIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSettingsStore } from "../stores/settingsStore";
import { getAnswer } from "../api/nlp";
import { getLibraries } from "../api/data";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { generateId, formatDate } from "../utils/helpers";
import type { ChatMessage } from "../api/types";

export function ChatPage() {
  const { chatHistory, addMessage, clearHistory } = useSettingsStore();
  const [question, setQuestion] = useState("");
  const [selectedLibraryId, setSelectedLibraryId] = useState<number | null>(null);
  const contextLimit = 10;
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Fetch Libraries
  const { data: librariesData } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const libraries = librariesData?.libraries || [];

  // Auto-select first library if none selected and libraries exist
  useEffect(() => {
    if (!selectedLibraryId && libraries.length > 0) {
      setSelectedLibraryId(libraries[0].id);
    }
  }, [libraries, selectedLibraryId]);

  const selectedLibrary = libraries.find(l => l.id === selectedLibraryId);

  const answerMutation = useMutation({
    mutationFn: (text: string) =>
      getAnswer({
        text,
        limit: contextLimit,
        project_name: selectedLibrary?.name,
        chat_history: chatHistory
          .slice(-10)
          .filter((m): m is typeof m & { role: "user" | "assistant" } =>
            m.role === "user" || m.role === "assistant"
          )
          .map((m) => ({ role: m.role, content: m.content })),
      }),
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: data.Answer,
        timestamp: new Date().toISOString(),
        metadata: {
          fullPrompt: data.FullPrompt,
          chatHistory: data.ChatHistory,
        },
      };
      addMessage(assistantMessage);
    },
    onError: (error) => {
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Failed to get answer"}`,
        timestamp: new Date().toISOString(),
      };
      addMessage(errorMessage);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || answerMutation.isPending || !selectedLibrary) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);
    answerMutation.mutate(question);
    setQuestion("");
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, answerMutation.isPending]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] min-h-0">
      {/* Header with Library Selector */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary tracking-tight">
            Chat
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Ask questions about your indexed documents
          </p>
        </div>

        {/* Library Selector */}
        <div className="relative">
          <label className="block text-xs font-medium text-text-secondary mb-1">
            Select Library
          </label>
          <div className="relative w-64">
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
      </div>

      {/* Chat Container */}
      <Card
        className="flex flex-col flex-1 overflow-hidden min-h-0"
        contentClassName="flex flex-col flex-1 min-h-0 p-0"
      >
        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
          {chatHistory.length === 0 ?
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-lg mb-2 text-text-primary">
                  Welcome to Fehres Chat
                </p>
                <p className="text-sm text-text-secondary">
                  {selectedLibrary
                    ? `Ask questions about ${selectedLibrary.name}`
                    : "Select a library to start chatting"}
                </p>
              </div>
            </div>
            : chatHistory.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"
                  }`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${message.role === "user" ?
                    "bg-primary-600 text-white rounded-br-none"
                    : "bg-bg-tertiary text-text-primary border border-border rounded-bl-none"
                    }`}
                >
                  {message.role === "assistant" ? (
                    <div className="chat-markdown text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                  <span className="text-xs opacity-70 mt-2 block">
                    {formatDate(message.timestamp)}
                  </span>
                </div>
              </div>
            ))
          }
          {answerMutation.isPending && (
            <div className="flex justify-start">
              <div className="bg-bg-tertiary border border-border rounded-2xl rounded-bl-none px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-border p-4 bg-bg-secondary">
          {chatHistory.length > 0 && (
            <div className="mb-3 flex justify-end">
              <Button variant="ghost" size="sm" onPress={clearHistory}>
                Clear History
              </Button>
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={selectedLibrary ? `Ask about ${selectedLibrary.name}...` : "Select a library first"}
              disabled={answerMutation.isPending || !selectedLibrary}
              className="flex-1 px-4 py-3 bg-bg-tertiary border border-border rounded-md text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-600 disabled:opacity-50 transition-all"
            />
            <Button
              type="submit"
              isLoading={answerMutation.isPending}
              isDisabled={!question.trim() || !selectedLibrary}
            >
              <PaperAirplaneIcon className="w-5 h-5" />
              Send
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
