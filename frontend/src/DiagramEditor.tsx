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
  type Connection,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type EdgeMouseHandler,
  type NodeTypes,
  BackgroundVariant,
  MarkerType,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import ComponentNode from "./nodes/ComponentNode";
import UmlClassNode from "./nodes/UmlClassNode";
import ErEntityNode from "./nodes/ErEntityNode";
import WorkflowStateNode from "./nodes/WorkflowStateNode";
import SequenceParticipantNode from "./nodes/SequenceParticipantNode";

const nodeTypes: NodeTypes = {
  component: ComponentNode,
  umlClass: UmlClassNode,
  erEntity: ErEntityNode,
  workflowState: WorkflowStateNode,
  sequenceParticipant: SequenceParticipantNode,
};

interface Props {
  diagramId: string;
  projectId: string;
  diagramType: string;
}

type NodeDataPatch = Record<string, unknown>;

type WorkflowShape = "startEnd" | "process" | "decision" | "state";
type SequenceParticipantKind = "actor" | "participant" | "boundary" | "control" | "entity";

interface WorkflowTemplateConfig {
  label: string;
  shape: WorkflowShape;
}

interface SequenceTemplateConfig {
  label: string;
  kind: SequenceParticipantKind;
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
  uml_sequence: () => ({
    type: "sequenceParticipant",
    data: { label: "Participant", kind: "participant" },
  }),
};

const WORKFLOW_SHAPES: WorkflowTemplateConfig[] = [
  { label: "Start / End", shape: "startEnd" },
  { label: "Process", shape: "process" },
  { label: "Decision", shape: "decision" },
  { label: "State", shape: "state" },
];

const SEQUENCE_PARTICIPANTS: SequenceTemplateConfig[] = [
  { label: "Actor", kind: "actor" },
  { label: "Participant", kind: "participant" },
  { label: "Boundary", kind: "boundary" },
  { label: "Control", kind: "control" },
  { label: "Entity", kind: "entity" },
];

function normalizeDecisionLabel(value: string | null | undefined): "Yes" | "No" | "" {
  const normalized = (value || "").trim().toLowerCase();
  if (!normalized) return "";
  if (normalized === "yes" || normalized === "y") return "Yes";
  if (normalized === "no" || normalized === "n") return "No";
  return "";
}

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

  const buildLabeledEdge = useCallback((connection: Connection, label?: string): Edge => ({
    ...connection,
    id: `e${connection.source}-${connection.target}-${Date.now()}`,
    label: label || undefined,
    labelBgPadding: label ? [8, 4] as [number, number] : undefined,
    labelBgBorderRadius: label ? 6 : undefined,
    labelBgStyle: label
      ? { fill: "#fff", fillOpacity: 0.95, stroke: "#d1d5db", strokeWidth: 1 }
      : undefined,
    style: { strokeWidth: 2 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
    },
  }), []);

  const promptDecisionEdgeLabel = useCallback((connection: Connection) => {
    const sourceNode = nodes.find((node) => node.id === connection.source);
    const isDecisionSource = sourceNode?.type === "workflowState" && sourceNode.data?.shape === "decision";

    if (!isDecisionSource) {
      return "";
    }

    const outgoingDecisionEdges = edges.filter((edge) => edge.source === connection.source);
    const suggested = outgoingDecisionEdges.some((edge) => normalizeDecisionLabel(String(edge.label ?? "")) === "Yes")
      ? "No"
      : "Yes";

    const input = window.prompt("Decision branch label", suggested);
    const label = normalizeDecisionLabel(input);

    if (input !== null && !label) {
      window.alert('Use "Yes" or "No" for decision branches.');
      return null;
    }

    return label;
  }, [edges, nodes]);

  const promptSequenceMessageLabel = useCallback(() => {
    const input = window.prompt("Message label", "message()");
    if (input === null) {
      return null;
    }
    return input.trim();
  }, []);

  const onConnect: OnConnect = useCallback(
    (connection) => {
      if (diagramType === "uml_sequence") {
        const sequenceLabel = promptSequenceMessageLabel();
        if (sequenceLabel === null) {
          return;
        }

        setEdges((eds) => addEdge(buildLabeledEdge(connection, sequenceLabel), eds));
        return;
      }

      const decisionLabel = promptDecisionEdgeLabel(connection);
      if (decisionLabel === null) {
        return;
      }

      setEdges((eds) => addEdge(buildLabeledEdge(connection, decisionLabel || undefined), eds));
    },
    [buildLabeledEdge, diagramType, promptDecisionEdgeLabel, promptSequenceMessageLabel]
  );

  const onEdgeDoubleClick: EdgeMouseHandler = useCallback((event, edge) => {
    event.preventDefault();

    const sourceNode = nodes.find((node) => node.id === edge.source);
    const isDecisionEdge = sourceNode?.type === "workflowState" && sourceNode.data?.shape === "decision";
    const isSequenceEdge = diagramType === "uml_sequence";
    const currentLabel = String(edge.label ?? "");
    const suggested = normalizeDecisionLabel(currentLabel) || "Yes";
    const input = window.prompt(
      isDecisionEdge ? 'Decision branch label ("Yes" or "No")' : isSequenceEdge ? "Message label" : "Edge label",
      currentLabel || (isSequenceEdge ? "message()" : suggested)
    );

    if (input === null) {
      return;
    }

    const nextLabel = isDecisionEdge ? normalizeDecisionLabel(input) : input.trim();
    if (isDecisionEdge && !nextLabel) {
      window.alert('Use "Yes" or "No" for decision branches.');
      return;
    }

    setEdges((currentEdges) =>
      currentEdges.map((currentEdge) =>
        currentEdge.id === edge.id
          ? {
              ...currentEdge,
              label: nextLabel || undefined,
              labelBgPadding: nextLabel ? [8, 4] : undefined,
              labelBgBorderRadius: nextLabel ? 6 : undefined,
              labelBgStyle: nextLabel
                ? { fill: "#fff", fillOpacity: 0.95, stroke: "#d1d5db", strokeWidth: 1 }
                : undefined,
            }
          : currentEdge
      )
    );
  }, [diagramType, nodes]);

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

  const addSequenceParticipant = useCallback((kind: SequenceParticipantKind, position?: { x: number; y: number }) => {
    const labelMap: Record<SequenceParticipantKind, string> = {
      actor: "Actor",
      participant: "Participant",
      boundary: "Boundary",
      control: "Control",
      entity: "Entity",
    };

    const participantCount = nodes.filter((node) => node.type === "sequenceParticipant").length;
    const newNode: Node = {
      id: String(nextId.current++),
      type: "sequenceParticipant",
      position: position || { x: 80 + participantCount * 220, y: 40 },
      draggable: true,
      data: {
        label: labelMap[kind],
        kind,
      },
    };

    setNodes((currentNodes) => [...currentNodes, newNode]);
  }, [nodes]);

  const onWorkflowDragStart = useCallback((event: React.DragEvent<HTMLButtonElement>, shape: WorkflowShape) => {
    event.dataTransfer.setData("application/x-workflow-shape", shape);
    event.dataTransfer.effectAllowed = "move";
  }, []);

  const onSequenceDragStart = useCallback((event: React.DragEvent<HTMLButtonElement>, kind: SequenceParticipantKind) => {
    event.dataTransfer.setData("application/x-sequence-participant", kind);
    event.dataTransfer.effectAllowed = "move";
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    const supportsWorkflowDrop = diagramType === "workflow" && event.dataTransfer.types.includes("application/x-workflow-shape");
    const supportsSequenceDrop = diagramType === "uml_sequence" && event.dataTransfer.types.includes("application/x-sequence-participant");
    if (!supportsWorkflowDrop && !supportsSequenceDrop) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, [diagramType]);

  const onDrop = useCallback((event: React.DragEvent) => {
    if (!reactFlowRef.current) return;

    if (diagramType === "workflow") {
      const shape = event.dataTransfer.getData("application/x-workflow-shape") as WorkflowShape;
      if (!shape) return;

      event.preventDefault();
      const position = reactFlowRef.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      addWorkflowNode(shape, position);
      return;
    }

    if (diagramType === "uml_sequence") {
      const kind = event.dataTransfer.getData("application/x-sequence-participant") as SequenceParticipantKind;
      if (!kind) return;

      event.preventDefault();
      const position = reactFlowRef.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      addSequenceParticipant(kind, { x: position.x, y: 40 });
    }
  }, [addSequenceParticipant, addWorkflowNode, diagramType]);

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
        onEdgeDoubleClick={onEdgeDoubleClick}
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
        {diagramType === "uml_sequence" && (
          <Panel position="top-left">
            <div
              className="nopan"
              style={{
                display: "grid",
                gap: "0.5rem",
                padding: "0.75rem",
                minWidth: "190px",
                background: "rgba(255,255,255,0.96)",
                border: "1px solid #e5e7eb",
                borderRadius: "10px",
                boxShadow: "0 8px 20px rgba(15, 23, 42, 0.08)",
              }}
            >
              <div style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#6b7280" }}>
                Sequence Participants
              </div>
              {SEQUENCE_PARTICIPANTS.map((participant) => (
                <button
                  key={participant.kind}
                  type="button"
                  className="nodrag nopan"
                  draggable
                  onDragStart={(event) => onSequenceDragStart(event, participant.kind)}
                  onClick={() => addSequenceParticipant(participant.kind)}
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
                  <span>{participant.label}</span>
                  <span style={{ fontSize: "0.7rem", color: "#6b7280" }}>Drag</span>
                </button>
              ))}
              <div style={{ fontSize: "0.75rem", color: "#6b7280", lineHeight: 1.4 }}>
                Connect participants with labeled arrows to model messages.
              </div>
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
