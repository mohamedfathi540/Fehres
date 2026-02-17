import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  GlobeAltIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { useSettingsStore } from "../../stores/settingsStore";
import { StatusBadge } from "../ui/StatusBadge";
import { Button } from "../ui/Button";
import { checkHealth } from "../../api/base";

const navigation = [
  { name: "Chat", href: "/", icon: ChatBubbleLeftRightIcon },
  { name: "Library Docs", href: "/library-docs", icon: GlobeAltIcon },
  { name: "Search", href: "/search", icon: MagnifyingGlassIcon },
  { name: "Index Info", href: "/index", icon: ChartBarIcon },
  { name: "Settings", href: "/settings", icon: Cog6ToothIcon },
];

export function Sidebar() {
  const { apiUrl } = useSettingsStore();
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
        <h1 className="text-xl font-semibold tracking-tight text-white">
          Fehres
        </h1>
        <p className="text-xs text-text-muted mt-0.5">RAG System</p>
      </div>

      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                isActive ?
                  "bg-primary-600 text-white"
                : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
              }`
            }
          >
            <item.icon className="w-5 h-5 shrink-0" />
            <span className="truncate">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-border space-y-3">
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
