import React, { useEffect, useMemo, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function UmlClassNode({ data }: NodeProps) {
  const d = data as {
    label?: string;
    attributes?: string[];
    methods?: string[];
    onChange?: (patch: { label: string; attributes: string[]; methods: string[] }) => void;
  };
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "ClassName");
  const [attributesText, setAttributesText] = useState((d.attributes || []).join("\n"));
  const [methodsText, setMethodsText] = useState((d.methods || []).join("\n"));

  useEffect(() => {
    if (editing) return;
    setLabel(d.label || "ClassName");
    setAttributesText((d.attributes || []).join("\n"));
    setMethodsText((d.methods || []).join("\n"));
  }, [d.attributes, d.label, d.methods, editing]);

  const attributes = useMemo(
    () =>
      attributesText
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
    [attributesText]
  );

  const methods = useMemo(
    () =>
      methodsText
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
    [methodsText]
  );

  const save = () => {
    setEditing(false);
    d.onChange?.({ label: label.trim() || "ClassName", attributes, methods });
  };

  const addAttribute = () => {
    setAttributesText((current) => (current.trim() ? `${current}\n- newField: type` : "- newField: type"));
  };

  const addMethod = () => {
    setMethodsText((current) => (current.trim() ? `${current}\n+ newMethod(): void` : "+ newMethod(): void"));
  };

  const cancel = () => {
    setEditing(false);
    setLabel(d.label || "ClassName");
    setAttributesText((d.attributes || []).join("\n"));
    setMethodsText((d.methods || []).join("\n"));
  };

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
        className="nopan"
        style={{
          padding: "8px 10px",
          fontWeight: 600,
          textAlign: "center",
          background: "#e0e7ff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
        }}
      >
        <span style={{ flex: 1, textAlign: "center", paddingLeft: "28px" }}>{label}</span>
        <button
          type="button"
          className="nodrag nopan"
          onClick={() => setEditing((value) => !value)}
          style={{
            border: "1px solid #6366f1",
            background: "#fff",
            color: "#4338ca",
            borderRadius: "4px",
            fontSize: "0.75rem",
            padding: "2px 6px",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          {editing ? "Close" : "Edit"}
        </button>
      </div>
      {editing && (
        <div className="nodrag nopan" style={{ padding: "10px", borderTop: "1px solid #6366f1", display: "grid", gap: "8px" }}>
          <input
            className="nodrag nopan"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                save();
              }
              if (e.key === "Escape") {
                cancel();
              }
            }}
            autoFocus
            placeholder="Class name"
            style={{ width: "100%", border: "1px solid #c7d2fe", borderRadius: "4px", padding: "6px 8px", fontWeight: 600 }}
          />
          <textarea
            className="nodrag nopan"
            value={attributesText}
            onChange={(e) => setAttributesText(e.target.value)}
            rows={4}
            placeholder={"One attribute per line\n- field: type"}
            style={{ width: "100%", border: "1px solid #c7d2fe", borderRadius: "4px", padding: "6px 8px", resize: "vertical", fontFamily: "inherit", fontSize: "0.8rem" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="nodrag nopan"
              onClick={addAttribute}
              style={{ border: "1px solid #6366f1", background: "#eef2ff", color: "#4338ca", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "0.75rem" }}
            >
              + Add field
            </button>
          </div>
          <textarea
            className="nodrag nopan"
            value={methodsText}
            onChange={(e) => setMethodsText(e.target.value)}
            rows={4}
            placeholder={"One method per line\n+ method(): void"}
            style={{ width: "100%", border: "1px solid #c7d2fe", borderRadius: "4px", padding: "6px 8px", resize: "vertical", fontFamily: "inherit", fontSize: "0.8rem" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="nodrag nopan"
              onClick={addMethod}
              style={{ border: "1px solid #6366f1", background: "#eef2ff", color: "#4338ca", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "0.75rem" }}
            >
              + Add method
            </button>
          </div>
          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="nodrag nopan"
              onClick={cancel}
              style={{ border: "1px solid #d1d5db", background: "#fff", borderRadius: "4px", padding: "4px 8px", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="button"
              className="nodrag nopan"
              onClick={save}
              style={{ border: "1px solid #4338ca", background: "#4338ca", color: "#fff", borderRadius: "4px", padding: "4px 8px", cursor: "pointer" }}
            >
              Apply
            </button>
          </div>
        </div>
      )}
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
