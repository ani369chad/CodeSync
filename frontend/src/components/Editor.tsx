import MonacoEditor, { type OnMount } from "@monaco-editor/react";
import type * as monacoEditor from "monaco-editor";
import { useEffect, useRef } from "react";
import { MonacoBinding } from "y-monaco";
import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";
import type { CommentThread, Highlight } from "../types";

const YJS_WS_URL = import.meta.env.VITE_YJS_WS_URL;

export interface RemoteCursor {
  clientId: string;
  name: string;
  color: string;
  line: number;
  column: number;
}

interface Props {
  sessionId: string;
  language: string | null;
  initialContent: string;
  remoteCursors: RemoteCursor[];
  threads: CommentThread[];
  highlights: Highlight[];
  onCursorMove: (line: number, column: number) => void;
  onGutterClick: (line: number) => void;
  onSelectionForHighlight: (startLine: number, endLine: number) => void;
  onContentSynced: (getContent: () => string) => void;
}

let styleSheet: HTMLStyleElement | null = null;
const injectedColors = new Set<string>();

function colorToClassName(color: string): string {
  const cls = `hl-${color.replace("#", "")}`;
  if (!injectedColors.has(cls)) {
    if (!styleSheet) {
      styleSheet = document.createElement("style");
      document.head.appendChild(styleSheet);
    }
    styleSheet.sheet?.insertRule(
      `.${cls} { background: ${color}55; border-left: 3px solid ${color}; }`
    );
    injectedColors.add(cls);
  }
  return cls;
}

export default function CodeEditor({
  sessionId,
  language,
  initialContent,
  remoteCursors,
  threads,
  highlights,
  onCursorMove,
  onGutterClick,
  onSelectionForHighlight,
  onContentSynced,
}: Props) {
  const editorRef = useRef<monacoEditor.editor.IStandaloneCodeEditor | null>(null);
  const monacoNsRef = useRef<typeof monacoEditor | null>(null);
  const cursorDecorationsRef = useRef<string[]>([]);
  const highlightDecorationsRef = useRef<string[]>([]);
  const commentDecorationsRef = useRef<string[]>([]);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const ydocRef = useRef<Y.Doc | null>(null);

  const handleMount: OnMount = (editor, monacoNs) => {
    editorRef.current = editor;
    monacoNsRef.current = monacoNs;

    const ydoc = new Y.Doc();
    ydocRef.current = ydoc;
    const ytext = ydoc.getText("monaco");

    const provider = new WebsocketProvider(YJS_WS_URL, `codesync-${sessionId}`, ydoc);
    providerRef.current = provider;

    provider.on("status", (event: { status: string }) => {
      if (event.status === "connected" && ytext.length === 0) {
        ytext.insert(0, initialContent);
      }
    });

    // Fallback in case the doc is already empty and no remote peer seeds it.
    setTimeout(() => {
      if (ytext.length === 0) {
        ytext.insert(0, initialContent);
      }
    }, 800);

    new MonacoBinding(ytext, editor.getModel()!, new Set([editor]), provider.awareness);

    onContentSynced(() => ytext.toString());

    editor.onDidChangeCursorPosition((e) => {
      onCursorMove(e.position.lineNumber, e.position.column);
    });

    editor.onMouseDown((e) => {
      const targetType = e.target.type;
      if (
        targetType === monacoNs.editor.MouseTargetType.GUTTER_GLYPH_MARGIN ||
        targetType === monacoNs.editor.MouseTargetType.GUTTER_LINE_NUMBERS
      ) {
        const line = e.target.position?.lineNumber;
        if (line) onGutterClick(line);
      }
    });
  };

  // Expose a keyboard shortcut / external trigger for highlight creation via selection.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const monacoNs = monacoNsRef.current;
    if (!monacoNs) return;

    const disposable = editor.addAction({
      id: "codesync-highlight-selection",
      label: "Highlight selection for everyone",
      keybindings: [monacoNs.KeyMod.CtrlCmd | monacoNs.KeyMod.Shift | monacoNs.KeyCode.KeyH],
      run: (ed) => {
        const sel = ed.getSelection();
        if (sel) {
          onSelectionForHighlight(sel.startLineNumber, sel.endLineNumber);
        }
      },
    });

    return () => disposable.dispose();
  }, [onSelectionForHighlight]);

  useEffect(() => {
    return () => {
      providerRef.current?.destroy();
      ydocRef.current?.destroy();
    };
  }, []);

  // Remote cursor decorations
  useEffect(() => {
    const editor = editorRef.current;
    const monacoNs = monacoNsRef.current;
    if (!editor || !monacoNs) return;

    const decorations: monacoEditor.editor.IModelDeltaDecoration[] = remoteCursors.map((c) => {
      const cls = colorToClassName(c.color);
      return {
        range: new monacoNs.Range(c.line, c.column, c.line, c.column + 1),
        options: {
          className: `remote-cursor ${cls}-cursor`,
          beforeContentClassName: "remote-cursor-flag",
          hoverMessage: { value: c.name },
          stickiness: monacoNs.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
        },
      };
    });

    cursorDecorationsRef.current = editor.deltaDecorations(cursorDecorationsRef.current, decorations);
  }, [remoteCursors]);

  // Highlight decorations
  useEffect(() => {
    const editor = editorRef.current;
    const monacoNs = monacoNsRef.current;
    if (!editor || !monacoNs) return;

    const decorations: monacoEditor.editor.IModelDeltaDecoration[] = highlights.map((h) => ({
      range: new monacoNs.Range(h.start_line, 1, h.end_line, 1),
      options: {
        isWholeLine: true,
        className: colorToClassName(h.color),
        hoverMessage: { value: `Highlighted by ${h.author_name}` },
      },
    }));

    highlightDecorationsRef.current = editor.deltaDecorations(highlightDecorationsRef.current, decorations);
  }, [highlights]);

  // Comment glyph decorations
  useEffect(() => {
    const editor = editorRef.current;
    const monacoNs = monacoNsRef.current;
    if (!editor || !monacoNs) return;

    const decorations: monacoEditor.editor.IModelDeltaDecoration[] = threads.map((t) => ({
      range: new monacoNs.Range(t.line_number, 1, t.line_number, 1),
      options: {
        glyphMarginClassName: t.resolved ? "comment-glyph resolved" : "comment-glyph",
        glyphMarginHoverMessage: {
          value: `${t.comments.length} comment${t.comments.length === 1 ? "" : "s"}${t.resolved ? " (resolved)" : ""}`,
        },
      },
    }));

    commentDecorationsRef.current = editor.deltaDecorations(commentDecorationsRef.current, decorations);
  }, [threads]);

  return (
    <MonacoEditor
      height="100%"
      theme="vs-dark"
      defaultLanguage={language ?? "plaintext"}
      onMount={handleMount}
      options={{
        glyphMargin: true,
        minimap: { enabled: true },
        fontSize: 13,
        automaticLayout: true,
      }}
    />
  );
}
