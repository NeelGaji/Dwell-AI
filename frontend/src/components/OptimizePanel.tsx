'use client';

import { Sparkles, RefreshCw, Loader2, Wand2, Layout, Palette, Zap } from 'lucide-react';
import type { RoomObject, RoomDimensions } from '@/lib/types';

interface OptimizePanelProps {
    objects: RoomObject[];
    roomDimensions: RoomDimensions | null;
    isGenerating: boolean;
    onGenerate: () => void;
    onReanalyze: () => void;
    isAnalyzing: boolean;
}

export function OptimizePanel({
    objects,
    roomDimensions,
    isGenerating,
    onGenerate,
    onReanalyze,
    isAnalyzing,
}: OptimizePanelProps) {
    const movableCount = objects.filter(o => o.type === 'movable').length;
    const structuralCount = objects.filter(o => o.type === 'structural').length;

    return (
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm h-full flex flex-col">
            {/* Header */}
            <div className="text-center mb-6">
                <div className="w-14 h-14 mx-auto mb-3 bg-gradient-to-br from-[#6b7aa1] to-[#8b9ac1] rounded-2xl flex items-center justify-center shadow-lg">
                    <Sparkles className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-gray-800">AI Layout Designer</h2>
                <p className="text-sm text-gray-500 mt-1">Generate optimized room arrangements</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 mb-6">
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                    <div className="text-2xl font-bold text-emerald-600">{movableCount}</div>
                    <div className="text-xs text-emerald-600/70">Movable</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <div className="text-2xl font-bold text-slate-600">{structuralCount}</div>
                    <div className="text-xs text-slate-600/70">Fixed</div>
                </div>
            </div>

            {/* Layout Styles Preview */}
            <div className="mb-6">
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                    AI will generate 3 styles
                </div>
                <div className="space-y-2">
                    <div className="flex items-center gap-3 p-2.5 bg-blue-50 rounded-lg">
                        <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                            <Zap className="w-4 h-4 text-blue-600" />
                        </div>
                        <div>
                            <div className="text-sm font-medium text-blue-800">Productivity Focus</div>
                            <div className="text-xs text-blue-600/70">Desk near window, work zones</div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-2.5 bg-rose-50 rounded-lg">
                        <div className="w-8 h-8 bg-rose-100 rounded-lg flex items-center justify-center">
                            <Layout className="w-4 h-4 text-rose-600" />
                        </div>
                        <div>
                            <div className="text-sm font-medium text-rose-800">Cozy Retreat</div>
                            <div className="text-xs text-rose-600/70">Bed-centered, intimate spaces</div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-2.5 bg-violet-50 rounded-lg">
                        <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center">
                            <Palette className="w-4 h-4 text-violet-600" />
                        </div>
                        <div>
                            <div className="text-sm font-medium text-violet-800">Creative Flow</div>
                            <div className="text-xs text-violet-600/70">Diagonal, unconventional</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Generate Button */}
            <button
                onClick={onGenerate}
                disabled={isGenerating || movableCount === 0}
                className="w-full py-3.5 px-4 bg-gradient-to-r from-[#6b7aa1] to-[#8b9ac1] text-white rounded-xl font-semibold
          hover:from-[#5a6890] hover:to-[#7a89b0] transition-all shadow-lg
          disabled:opacity-50 disabled:cursor-not-allowed
          flex items-center justify-center gap-2"
            >
                {isGenerating ? (
                    <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Generating...
                    </>
                ) : (
                    <>
                        <Sparkles className="w-5 h-5" />
                        Generate Layouts
                    </>
                )}
            </button>

            {/* Re-analyze button */}
            <button
                onClick={onReanalyze}
                disabled={isAnalyzing}
                className="w-full mt-3 py-2 px-4 text-gray-500 hover:text-gray-700 hover:bg-gray-50 
          rounded-xl transition-colors flex items-center justify-center gap-2 text-sm"
            >
                {isAnalyzing ? (
                    <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Re-analyzing...
                    </>
                ) : (
                    <>
                        <RefreshCw className="w-4 h-4" />
                        Re-analyze Room
                    </>
                )}
            </button>

            {/* Info */}
            {movableCount === 0 && (
                <p className="text-xs text-amber-600 text-center mt-3 bg-amber-50 rounded-lg p-2">
                    No movable objects detected. All items are structural.
                </p>
            )}
        </div>
    );
}