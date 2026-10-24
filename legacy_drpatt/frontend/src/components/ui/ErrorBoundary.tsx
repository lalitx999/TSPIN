"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("🔥 ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            padding: "40px",
            textAlign: "center",
            background: "#FFFFFF",
            border: "1px solid #E5E7EB",
            borderRadius: "8px",
            margin: "24px",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              background: "#FEF2F2",
              borderRadius: "12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#1F2937", marginBottom: "8px" }}>
            เกิดข้อผิดพลาดทางเทคนิค
          </h3>
          <p style={{ fontSize: "13px", color: "#6B7280", marginBottom: "20px", maxWidth: "360px", margin: "0 auto 20px" }}>
            ระบบพบปัญหาไม่คาดคิด กรุณาลองใหม่อีกครั้ง หรือติดต่อผู้ดูแลระบบ
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: "8px 24px",
              fontSize: "13px",
              fontWeight: 600,
              background: "#0A5C8E",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            ลองใหม่อีกครั้ง
          </button>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <details style={{ marginTop: "24px", textAlign: "left" }}>
              <summary style={{ fontSize: "11px", color: "#9CA3AF", cursor: "pointer" }}>
                รายละเอียดทางเทคนิค (Dev only)
              </summary>
              <pre
                style={{
                  marginTop: "8px",
                  padding: "12px",
                  fontSize: "11px",
                  color: "#EF4444",
                  background: "#FEF2F2",
                  borderRadius: "6px",
                  overflowX: "auto",
                  whiteSpace: "pre-wrap",
                }}
              >
                {this.state.error.message}
                {"\n\n"}
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
