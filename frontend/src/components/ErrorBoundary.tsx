import { Component } from "react";
import type { ReactNode } from "react";
import { IconAlert } from "../design/icons";
import { logger } from "../lib/logger";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    logger.error("ErrorBoundary a attrapé une erreur de rendu", {
      message: error.message,
      stack: info.componentStack,
    });
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-3">
            <IconAlert size={28} className="text-amber-400" />
            <p className="text-sm text-zinc-300 font-medium">
              Une erreur inattendue s&apos;est produite
            </p>
            <p className="text-xs text-zinc-500 font-mono break-all max-w-xs">
              {this.state.error.message}
            </p>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-2 px-3 py-1.5 text-xs rounded-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors"
            >
              Réessayer
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
