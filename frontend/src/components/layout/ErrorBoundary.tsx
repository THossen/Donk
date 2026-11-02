import { Component, type ReactNode } from 'react';

export default class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error('Donk crashed:', error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-ink-950 px-4">
          <div className="w-full max-w-lg rounded-xl border border-ink-700 bg-ink-900 p-6 shadow-sm">
            <h1 className="text-lg font-semibold">Something went wrong</h1>
            <p className="mt-1 text-sm">
              Donk hit an error and couldn't render. The details below help track it down.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-ink-950 p-3 font-mono text-xs">
              {String(this.state.error.message || this.state.error)}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a5a53]"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
