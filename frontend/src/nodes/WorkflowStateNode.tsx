import React, { useEffect, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function WorkflowStateNode({ data }: NodeProps) {
  const d = data as {
    label?: string;
    shape?: "startEnd" | "process" | "decision" | "state";
    onChange?: (patch: { label: string }) => void;
  };
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "State");

  useEffect(() => {
    if (editing) return;
    setLabel(d.label || "State");
  }, [d.label, editing]);

  const save = () => {
    setEditing(false);
    d.onChange?.({ label: label.trim() || "State" });
  };

  const shape = d.shape || "state";

  const shapeStyles: Record<string, React.CSSProperties> = {
    startEnd: {
      padding: "12px 24px",
      borderRadius: "999px",
      background: "#dcfce7",
      border: "2px solid #15803d",
      minWidth: "120px",
    },
    process: {
      padding: "14px 24px",
      borderRadius: "10px",
      background: "#dbeafe",
      border: "2px solid #2563eb",
      minWidth: "130px",
    },
    decision: {
      width: "130px",
      height: "130px",
      background: "#fef3c7",
      border: "2px solid #b45309",
      transform: "rotate(45deg)",
      borderRadius: "12px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "14px",
    },
    state: {
      padding: "12px 24px",
      borderRadius: "24px",
      background: "#fef3c7",
      border: "2px solid #b45309",
      minWidth: "100px",
    },
  };

  const content = editing ? (
    <input
      className="nodrag nopan"
      value={label}
      onChange={(e) => setLabel(e.target.value)}
      onBlur={save}
      onKeyDown={(e) => {
        if (e.key === "Enter") save();
        if (e.key === "Escape") setEditing(false);
      }}
      autoFocus
      style={{ width: "100%", textAlign: "center", border: "none", background: "transparent", fontSize: "0.9rem" }}
    />
  ) : (
    <div onDoubleClick={() => setEditing(true)}>
      {label}
    </div>
  );

  return (
    <div
      style={{
        textAlign: "center",
        fontSize: "0.9rem",
        fontWeight: 500,
        ...shapeStyles[shape],
      }}
    >
      <Handle type="target" position={Position.Top} />
      {shape === "decision" ? (
        <div style={{ transform: "rotate(-45deg)", width: "100%", display: "flex", justifyContent: "center" }}>
          {content}
        </div>
      ) : (
        content
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
