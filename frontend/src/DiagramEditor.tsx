import React, { useCallback, useEffect, useState, useRef } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type ReactFlowInstance,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeTypes,
  BackgroundVariant,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import ComponentNode from "./nodes/ComponentNode";
import UmlClassNode from "./nodes/UmlClassNode";
import ErEntityNode from "./nodes/ErEntityNode";
import WorkflowStateNode from "./nodes/WorkflowStateNode";

const nodeTypes: NodeTypes = {
  component: ComponentNode,
  umlClass: UmlClassNode,
  erEntity: ErEntityNode,
  workflowState: WorkflowStateNode,
};

interface Props {
  diagramId: string;
  projectId: string;
  diagramType: string;
}

type NodeDataPatch = Record<string, unknown>;

type WorkflowShape = "startEnd" | "process" | "decision" | "state";

interface WorkflowTemplateConfig {
  label: string;
  shape: WorkflowShape;
}

const NODE_TEMPLATES: Record<string, () => Partial<Node>> = {
  architecture: () => ({
    type: "component",
    data: { label: "Component" },
  }),
  uml_class: () => ({
    type: "umlClass",
    data: { label: "ClassName", attributes: ["- field: type"], methods: ["+ method(): void"] },
  }),
  er: () => ({
    type: "erEntity",
    data: { label: "Entity", attributes: ["id: PK", "name: string"] },
  }),
  workflow: () => ({
    type: "workflowState",
    data: { label: "State", shape: "state" },
  }),
};

const WORKFLOW_SHAPES: WorkflowTemplateConfig[] = [
  { label: "Start / End", shape: "startEnd" },
  { label: "Process", shape: "process" },
  { label: "Decision", shape: "decision" },
  { label: "State", shape: "state" },
];

export default function DiagramEditor({ diagramId, projectId, diagramType }: Props) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const nextId = useRef(1);
  const reactFlowRef = useRef<ReactFlowInstance<any, Edge> | null>(null);
  const hasLoadedRef = useRef(false);
  const saveTimeoutRef = useRef<number | null>(null);
  const statusTimeoutRef = useRef<number | null>(null);

  const storageKey = `diagram-draft:${diagramId}`;

  const clearStatusLater = useCallback(() => {
    if (statusTimeoutRef.current !== null) {
      window.clearTimeout(statusTimeoutRef.current);
    }
    statusTimeoutRef.current = window.setTimeout(() => setStatus(""), 2000);
  }, []);

  const persistDraft = useCallback((nextNodes: Node[], nextEdges: Edge[]) => {
    if (!diagramId) return;
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        nodes: nextNodes,
        edges: nextEdges,
        savedAt: new Date().toISOString(),
      })
    );
  }, [diagramId, storageKey]);

  const saveDiagram = useCallback(async (nextNodes: Node[], nextEdges: Edge[], successMessage = "Saved") => {
    if (!diagramId) return false;
    setSaving(true);
    setStatus("");
    try {
      const resp = await fetch(`/api/diagrams/${diagramId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: { nodes: nextNodes, edges: nextEdges } }),
      });
      if (resp.ok) {
        window.localStorage.removeItem(storageKey);
        setStatus(successMessage);
        clearStatusLater();
        return true;
      }
      setStatus("Save failed");
      clearStatusLater();
      return false;
    } catch {
      setStatus("Save failed");
      clearStatusLater();
      return false;
    } finally {
      setSaving(false);
    }
  }, [clearStatusLater, diagramId, storageKey]);

  useEffect(() => {
    if (!diagramId) return;
    fetch(`/api/diagrams/${diagramId}`)
      .then((r) => r.json())
      .then((data) => {
        const serverNodes = data.data?.nodes || [];
        const serverEdges = data.data?.edges || [];
        const savedDraft = window.localStorage.getItem(storageKey);
        const draft = savedDraft ? JSON.parse(savedDraft) : null;
        const loadedNodes = draft?.nodes || serverNodes;
        const loadedEdges = draft?.edges || serverEdges;

        setNodes(loadedNodes);
        setEdges(loadedEdges);
        const maxId = loadedNodes.reduce(
          (max: number, n: Node) => Math.max(max, parseInt(n.id, 10) || 0),
          0
        );
        nextId.current = maxId + 1;
        hasLoadedRef.current = true;
        if (draft) {
          setStatus("Restored draft");
          clearStatusLater();
        }
      });
  }, [clearStatusLater, diagramId, storageKey]);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect: OnConnect = useCallback(
    (connection) =>
      setEdges((eds) =>
        addEdge({ ...connection, id: `e${connection.source}-${connection.target}` }, eds)
      ),
    []
  );

  const updateNodeData = useCallback((nodeId: string, patch: NodeDataPatch) => {
    setNodes((currentNodes) =>
      currentNodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...(node.data || {}),
                ...patch,
              },
            }
          : node
      )
    );
  }, []);

  const addNode = useCallback(() => {
    const template = NODE_TEMPLATES[diagramType] || NODE_TEMPLATES.architecture;
    const newNode: Node = {
      id: String(nextId.current++),
      position: { x: 100 + Math.random() * 300, y: 100 + Math.random() * 300 },
      ...template(),
    } as Node;
    setNodes((nds) => [...nds, newNode]);
  }, [diagramType]);

  const addWorkflowNode = useCallback((shape: WorkflowShape, position?: { x: number; y: number }) => {
    const labelMap: Record<WorkflowShape, string> = {
      startEnd: "Start",
      process: "Process",
      decision: "Decision",
      state: "State",
    };

    const newNode: Node = {
      id: String(nextId.current++),
      type: "workflowState",
      position: position || { x: 100 + Math.random() * 300, y: 100 + Math.random() * 300 },
      data: {
        label: labelMap[shape],
        shape,
      },
    };

    setNodes((currentNodes) => [...currentNodes, newNode]);
  }, []);

  const onWorkflowDragStart = useCallback((event: React.DragEvent<HTMLButtonElement>, shape: WorkflowShape) => {
    event.dataTransfer.setData("application/x-workflow-shape", shape);
    event.dataTransfer.effectAllowed = "move";
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    if (diagramType !== "workflow") return;
    if (!event.dataTransfer.types.includes("application/x-workflow-shape")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, [diagramType]);

  const onDrop = useCallback((event: React.DragEvent) => {
    if (diagramType !== "workflow") return;

    const shape = event.dataTransfer.getData("application/x-workflow-shape") as WorkflowShape;
    if (!shape || !reactFlowRef.current) return;

    event.preventDefault();
    const position = reactFlowRef.current.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    addWorkflowNode(shape, position);
  }, [addWorkflowNode, diagramType]);

  const save = useCallback(async () => {
    await saveDiagram(nodes, edges);
  }, [edges, nodes, saveDiagram]);

  useEffect(() => {
    if (!diagramId || !hasLoadedRef.current) return;

    persistDraft(nodes, edges);

    if (saveTimeoutRef.current !== null) {
      window.clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = window.setTimeout(() => {
      void saveDiagram(nodes, edges, "Autosaved");
    }, 1200);

    return () => {
      if (saveTimeoutRef.current !== null) {
        window.clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [diagramId, edges, nodes, persistDraft, saveDiagram]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (!hasLoadedRef.current) return;
      persistDraft(nodes, edges);
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [edges, nodes, persistDraft]);

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current !== null) {
        window.clearTimeout(saveTimeoutRef.current);
      }
      if (statusTimeoutRef.current !== null) {
        window.clearTimeout(statusTimeoutRef.current);
      }
    };
  }, []);

  const renderedNodes = nodes.map((node) => ({
    ...node,
    data: {
      ...(node.data || {}),
      onChange: (patch: NodeDataPatch) => updateNodeData(node.id, patch),
    },
  }));

  return (
    <div style={{ width: "100%", height: "600px", border: "1px solid #e5e5e5", borderRadius: "8px" }}>
      <ReactFlow
        nodes={renderedNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        onInit={(instance) => {
          reactFlowRef.current = instance;
        }}
        onDragOver={onDragOver}
        onDrop={onDrop}
        fitView
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        {diagramType === "workflow" && (
          <Panel position="top-left">
            <div
              className="nopan"
              style={{
                display: "grid",
                gap: "0.5rem",
                padding: "0.75rem",
                minWidth: "170px",
                background: "rgba(255,255,255,0.96)",
                border: "1px solid #e5e7eb",
                borderRadius: "10px",
                boxShadow: "0 8px 20px rgba(15, 23, 42, 0.08)",
              }}
            >
              <div style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#6b7280" }}>
                Workflow Shapes
              </div>
              {WORKFLOW_SHAPES.map((shape) => (
                <button
                  key={shape.shape}
                  type="button"
                  className="nodrag nopan"
                  draggable
                  onDragStart={(event) => onWorkflowDragStart(event, shape.shape)}
                  onClick={() => addWorkflowNode(shape.shape)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "0.75rem",
                    width: "100%",
                    padding: "0.5rem 0.65rem",
                    border: "1px solid #d1d5db",
                    borderRadius: "8px",
                    background: "#fff",
                    cursor: "grab",
                    fontSize: "0.85rem",
                  }}
                  title="Click to add or drag onto the canvas"
                >
                  <span>{shape.label}</span>
                  <span style={{ fontSize: "0.7rem", color: "#6b7280" }}>Drag</span>
                </button>
              ))}
            </div>
          </Panel>
        )}
        <Panel position="top-right">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button onClick={addNode} className="btn btn-primary" style={{ fontSize: "0.85rem" }}>
              + Add Node
            </button>
            <button onClick={save} disabled={saving} className="btn" style={{ fontSize: "0.85rem" }}>
              {saving ? "Saving..." : "Save"}
            </button>
            {status && <span style={{ fontSize: "0.8rem", color: "#059669" }}>{status}</span>}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
