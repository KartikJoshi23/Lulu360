import { Component, type ReactNode } from "react";

/** Contains render errors (e.g. WebGL unavailable for the Silk background) so a
 *  failure in one subtree never takes down the whole app. */
export class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) return this.props.fallback ?? null;
    return this.props.children;
  }
}
