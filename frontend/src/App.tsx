import { useEffect, useState } from "react";
import { Welcome } from "./components/Welcome";
import { Editor } from "./components/editor/Editor";
import { SettingsPanel } from "./components/settings/SettingsPanel";
import { useStudio } from "./stores/studioStore";
import { connectStudioSocket } from "./lib/ws";

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const applyEvent = useStudio((s) => s.applyEvent);
  const loadProject = useStudio((s) => s.loadProject);

  useEffect(() => connectStudioSocket(applyEvent), [applyEvent]);

  useEffect(() => {
    if (projectId) void loadProject(projectId);
  }, [projectId, loadProject]);

  return (
    <div className="h-full w-full">
      {projectId ? (
        <Editor
          onHome={() => setProjectId(null)}
          onSettings={() => setShowSettings(true)}
        />
      ) : (
        <Welcome onOpen={setProjectId} onSettings={() => setShowSettings(true)} />
      )}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}
