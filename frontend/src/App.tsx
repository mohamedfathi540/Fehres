import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MainLayout } from "./components/layout/MainLayout";
import { ChatPage } from "./pages/ChatPage";
import { UploadPage } from "./pages/UploadPage";
import { SearchPage } from "./pages/SearchPage";
import { IndexInfoPage } from "./pages/IndexInfoPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LearningBooksAdminPage } from "./pages/LearningBooksAdminPage";
import { LearningAssistantChatPage } from "./pages/LearningAssistantChatPage";
import { PrescriptionPage } from "./pages/PrescriptionPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<ChatPage />} />
            <Route path="learning" element={<LearningAssistantChatPage />} />
            <Route path="learning-books" element={<LearningBooksAdminPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="index" element={<IndexInfoPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="prescription" element={<PrescriptionPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
