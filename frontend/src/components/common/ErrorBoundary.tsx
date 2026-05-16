import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  handleGoHome = () => {
    this.setState({
      hasError: false,
      error: null,
    });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-[#060d1a] p-6">
          <div className="glass-card max-w-md w-full p-8 text-center border-danger-500/30">
            <div className="w-16 h-16 rounded-2xl bg-danger-500/10 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle size={32} className="text-danger-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Engine Failure</h2>
            <p className="text-dark-400 text-sm mb-6">
              A critical error occurred in the agent orchestration layer. The system has been halted for security.
            </p>

            {this.state.error && (
              <div className="bg-dark-950/50 rounded-lg p-3 mb-6 text-left border border-dark-800">
                <p className="text-[10px] font-mono text-danger-400 uppercase mb-1">Error Trace</p>
                <p className="text-xs font-mono text-dark-300 break-words">{this.state.error.message}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="btn-primary flex-1 justify-center gap-2"
              >
                <RefreshCw size={16} />
                Restart Engine
              </button>
              <button
                onClick={this.handleGoHome}
                className="btn-secondary p-3"
                title="Go to Landing Page"
              >
                <Home size={16} />
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
