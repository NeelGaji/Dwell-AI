'use client';

import { useEffect, useState } from 'react';
import { Sparkles, Check, Loader2 } from 'lucide-react';

interface GeneratingOverlayProps {
    steps: Array<{ label: string; duration: number }>;
    currentStep: number;
}

export function GeneratingOverlay({ steps, currentStep }: GeneratingOverlayProps) {
    const [dots, setDots] = useState('');

    // Animate dots
    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => (prev.length >= 3 ? '' : prev + '.'));
        }, 400);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="min-h-[500px] flex flex-col items-center justify-center p-8">
            {/* Animated Icon */}
            <div className="relative mb-8">
                <div className="w-24 h-24 bg-gradient-to-br from-[#6b7aa1] to-[#8b9ac1] rounded-3xl flex items-center justify-center shadow-2xl animate-pulse">
                    <Sparkles className="w-12 h-12 text-white" />
                </div>
                {/* Orbiting dots */}
                <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
                    <div className="absolute -top-2 left-1/2 w-3 h-3 bg-blue-400 rounded-full transform -translate-x-1/2" />
                </div>
                <div className="absolute inset-0 animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }}>
                    <div className="absolute -bottom-2 left-1/2 w-2 h-2 bg-rose-400 rounded-full transform -translate-x-1/2" />
                </div>
                <div className="absolute inset-0 animate-spin" style={{ animationDuration: '5s' }}>
                    <div className="absolute top-1/2 -right-2 w-2.5 h-2.5 bg-violet-400 rounded-full transform -translate-y-1/2" />
                </div>
            </div>

            {/* Title */}
            <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                Designing Your Space{dots}
            </h2>
            <p className="text-gray-500 mb-8">Our AI is creating unique layout options</p>

            {/* Progress Steps */}
            <div className="w-full max-w-md space-y-3">
                {steps.map((step, index) => {
                    const isComplete = index < currentStep;
                    const isCurrent = index === currentStep;
                    const isPending = index > currentStep;

                    return (
                        <div
                            key={index}
                            className={`
                flex items-center gap-3 p-3 rounded-xl transition-all duration-300
                ${isComplete ? 'bg-emerald-50' : isCurrent ? 'bg-[#6b7aa1]/10' : 'bg-gray-50'}
              `}
                        >
                            {/* Status Icon */}
                            <div className={`
                w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all
                ${isComplete
                                    ? 'bg-emerald-500 text-white'
                                    : isCurrent
                                        ? 'bg-[#6b7aa1] text-white'
                                        : 'bg-gray-200 text-gray-400'
                                }
              `}>
                                {isComplete ? (
                                    <Check className="w-4 h-4" />
                                ) : isCurrent ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <span className="text-xs font-medium">{index + 1}</span>
                                )}
                            </div>

                            {/* Label */}
                            <span className={`
                text-sm font-medium transition-colors
                ${isComplete
                                    ? 'text-emerald-700'
                                    : isCurrent
                                        ? 'text-[#6b7aa1]'
                                        : 'text-gray-400'
                                }
              `}>
                                {step.label}
                            </span>

                            {/* Progress indicator for current step */}
                            {isCurrent && (
                                <div className="ml-auto">
                                    <div className="flex gap-1">
                                        <div className="w-1.5 h-1.5 bg-[#6b7aa1] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-1.5 h-1.5 bg-[#6b7aa1] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-1.5 h-1.5 bg-[#6b7aa1] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Tip */}
            <div className="mt-8 text-center">
                <p className="text-xs text-gray-400 max-w-sm">
                    💡 Tip: Each layout style optimizes for different needs - productivity, comfort, or creativity
                </p>
            </div>
        </div>
    );
}