import React, { useState, useCallback } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function WorkflowStateNode({ data }: NodeProps) {
  const d = data as any;
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "State");

  const save = useCallback(() => {
    setEditing(false);
    d.label = label;
  }, [d, label]);

  return (
    <div
      style={{
        padding: "12px 24px",
        borderRadius: "24px",
        background: "#fef3c7",
        border: "2px solid #b45309",
        minWidth: "100px",
        textAlign: "center",
        fontSize: "0.9rem",
        fontWeight: 500,
      }}
    >
      <Handle type="target" position={Position.Top} />
      {editing ? (
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => e.key === "Enter" && save()}
          autoFocus
          style={{ width: "100%", textAlign: "center", border: "none", background: "transparent", fontSize: "0.9rem" }}
        />
      ) : (
        <div onDoubleClick={() => setEditing(true)}>{label}</div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
