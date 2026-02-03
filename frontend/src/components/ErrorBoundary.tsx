'use client';

import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * Error Boundary component to catch and display errors gracefully.
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    handleReset = (): void => {
        this.setState({ hasError: false, error: null });
    };

    render(): ReactNode {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-[300px] flex items-center justify-center p-8">
                    <div className="text-center max-w-md">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
                            <AlertTriangle className="w-8 h-8 text-red-500" />
                        </div>
                        <h2 className="text-xl font-semibold text-slate-200 mb-2">
                            Something went wrong
                        </h2>
                        <p className="text-slate-400 mb-4">
                            {this.state.error?.message || 'An unexpected error occurred'}
                        </p>
                        <button
                            onClick={this.handleReset}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Try Again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

/**
 * Skeleton loader for image analysis
 */
export function AnalysisSkeleton() {
    return (
        <div className="animate-pulse space-y-3">
            <div className="h-4 bg-slate-700 rounded w-3/4"></div>
            <div className="h-4 bg-slate-700 rounded w-1/2"></div>
            <div className="h-4 bg-slate-700 rounded w-5/6"></div>
            <div className="flex gap-2 mt-4">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="h-8 w-24 bg-slate-700 rounded"></div>
                ))}
            </div>
        </div>
    );
}

/**
 * Loading spinner with message
 */
export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
    return (
        <div className="flex items-center justify-center gap-3 py-8">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-slate-400">{message}</span>
        </div>
    );
}

/**
 * Progress indicator for rendering
 */
export function RenderingProgress({ progress = 0 }: { progress?: number }) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-sm text-slate-400">
                <span>Rendering...</span>
                <span>{progress}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}
