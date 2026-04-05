import React from "react";
import { createRoot } from "react-dom/client";
import DiagramEditor from "./DiagramEditor";

const container = document.getElementById("diagram-editor");
if (container) {
  const diagramId = container.dataset.diagramId || "";
  const projectId = container.dataset.projectId || "";
  const diagramType = container.dataset.diagramType || "architecture";

  createRoot(container).render(
    <React.StrictMode>
      <DiagramEditor
        diagramId={diagramId}
        projectId={projectId}
        diagramType={diagramType}
      />
    </React.StrictMode>
  );
}
