import React, { useState, useCallback } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function UmlClassNode({ data }: NodeProps) {
  const d = data as any;
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "ClassName");
  const [attributes, setAttributes] = useState<string[]>(d.attributes || []);
  const [methods, setMethods] = useState<string[]>(d.methods || []);

  const save = useCallback(() => {
    setEditing(false);
    d.label = label;
    d.attributes = attributes;
    d.methods = methods;
  }, [d, label, attributes, methods]);

  const sectionStyle: React.CSSProperties = {
    padding: "6px 10px",
    fontSize: "0.8rem",
    borderTop: "1px solid #6366f1",
    textAlign: "left",
  };

  return (
    <div
      style={{
        borderRadius: "4px",
        background: "#fff",
        border: "2px solid #6366f1",
        minWidth: "160px",
        fontSize: "0.85rem",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div
        style={{
          padding: "8px 10px",
          fontWeight: 600,
          textAlign: "center",
          background: "#e0e7ff",
        }}
        onDoubleClick={() => setEditing(true)}
      >
        {editing ? (
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={save}
            onKeyDown={(e) => e.key === "Enter" && save()}
            autoFocus
            style={{ width: "100%", textAlign: "center", border: "none", background: "transparent", fontWeight: 600 }}
          />
        ) : (
          label
        )}
      </div>
      <div style={sectionStyle}>
        {attributes.map((attr, i) => (
          <div key={i}>{attr}</div>
        ))}
        {attributes.length === 0 && <div style={{ color: "#999" }}>No attributes</div>}
      </div>
      <div style={sectionStyle}>
        {methods.map((m, i) => (
          <div key={i}>{m}</div>
        ))}
        {methods.length === 0 && <div style={{ color: "#999" }}>No methods</div>}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
