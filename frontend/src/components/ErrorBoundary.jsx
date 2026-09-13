import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Three.js/Canvas render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex flex-col items-center justify-center h-64 font-mono text-center"
          style={{ color: "var(--th-primary)" }}
        >
          <div
            className="w-24 h-24 rounded-full border animate-pulse mb-3"
            style={{ borderColor: "var(--th-border-bright)" }}
          />
          <p className="text-xs uppercase tracking-widest">[TACTICAL CORE 2D FALLBACK]</p>
        </div>
      );
    }
    return this.props.children;
  }
}
