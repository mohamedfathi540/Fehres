import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  ChatBubbleLeftRightIcon,
  ArrowUpTrayIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  AcademicCapIcon,
  BookOpenIcon,
} from "@heroicons/react/24/outline";
import { useSettingsStore } from "../../stores/settingsStore";
import { StatusBadge } from "../ui/StatusBadge";
import { Button } from "../ui/Button";
import { checkHealth } from "../../api/base";

const navigation = [
  { name: "Chat", href: "/", icon: ChatBubbleLeftRightIcon },
  { name: "Learning Assistant", href: "/learning", icon: AcademicCapIcon },
  { name: "Learning Books", href: "/learning-books", icon: BookOpenIcon },
  { name: "Upload & Process", href: "/upload", icon: ArrowUpTrayIcon },
  { name: "Search", href: "/search", icon: MagnifyingGlassIcon },
  { name: "Index Info", href: "/index", icon: ChartBarIcon },
  { name: "Settings", href: "/settings", icon: Cog6ToothIcon },
];

export function Sidebar() {
  const { projectId, setProjectId, apiUrl } = useSettingsStore();
  const [apiStatus, setApiStatus] = useState<"online" | "offline">("offline");
  const [isChecking, setIsChecking] = useState(false);

  const checkApiStatus = async () => {
    setIsChecking(true);
    try {
      await checkHealth();
      setApiStatus("online");
    } catch {
      setApiStatus("offline");
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <aside className="w-60 shrink-0 bg-bg-secondary border-r border-border flex flex-col h-full">
      <div className="p-5 border-b border-border">
        <h1 className="text-xl font-semibold tracking-tight gradient-primary bg-clip-text text-transparent">
          Fehres
        </h1>
        <p className="text-xs text-text-muted mt-0.5">RAG System</p>
      </div>

      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-500/12 text-primary-400 border border-primary-500/25"
                  : "text-text-secondary hover:bg-bg-hover hover:text-text-primary border border-transparent"
              }`
            }
          >
            <item.icon className="w-5 h-5 shrink-0" />
            <span className="truncate">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-border space-y-3">
        <div>
          <label className="text-[11px] font-medium text-text-muted uppercase tracking-wider block mb-1">
            Project ID
          </label>
          <input
            type="number"
            min={1}
            value={projectId}
            onChange={(e) => setProjectId(parseInt(e.target.value) || 1)}
            className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30"
          />
        </div>
        <div className="flex items-center justify-between gap-2">
          <StatusBadge
            status={apiStatus}
            text={isChecking ? "Checking..." : undefined}
          />
          <Button
            variant="ghost"
            size="sm"
            onPress={checkApiStatus}
            isLoading={isChecking}
          >
            Check
          </Button>
        </div>
        <p className="text-[11px] text-text-muted truncate" title={apiUrl}>
          {apiUrl}
        </p>
      </div>
    </aside>
  );
}
