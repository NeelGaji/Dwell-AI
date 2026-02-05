'use client';

import { ArrowLeft, Loader2, Check, ImageOff } from 'lucide-react';
import { useState } from 'react';
import type { LayoutVariation, RoomDimensions, RoomObject } from '@/lib/types';

interface LayoutSelectorProps {
    variations: LayoutVariation[];
    roomDimensions: RoomDimensions | null;
    isLoading: boolean;
    onSelect: (variation: LayoutVariation) => void;
    onBack: () => void;
}

// Color mapping for furniture types
const getObjectColor = (label: string): string => {
    const labelLower = label.toLowerCase();
    if (labelLower.includes('bed')) return '#e8b4a8';
    if (labelLower.includes('sofa') || labelLower.includes('couch')) return '#f5c4c4';
    if (labelLower.includes('chair')) return '#c4e8c4';
    if (labelLower.includes('desk')) return '#c4d4e8';
    if (labelLower.includes('table')) return '#e8e4c4';
    if (labelLower.includes('door')) return '#a8c8d8';
    if (labelLower.includes('window')) return '#d8e8f0';
    if (labelLower.includes('wardrobe') || labelLower.includes('closet')) return '#d8c8b8';
    return '#d8d8d8';
};

// SVG-based preview component (fallback when no thumbnail)
function LayoutPreview({ layout, roomDimensions }: { layout: RoomObject[]; roomDimensions: RoomDimensions | null }) {
    if (!layout || layout.length === 0) {
        return (
            <div className="w-full h-full flex items-center justify-center">
                <span className="text-xs text-gray-400">No preview</span>
            </div>
        );
    }

    // Calculate bounds
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    layout.forEach(obj => {
        const [x, y, w, h] = obj.bbox;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x + w);
        maxY = Math.max(maxY, y + h);
    });

    const padding = Math.max((maxX - minX), (maxY - minY)) * 0.1;
    const viewX = minX - padding;
    const viewY = minY - padding;
    const viewW = (maxX - minX) + (padding * 2);
    const viewH = (maxY - minY) + (padding * 2);

    return (
        <svg
            viewBox={`${viewX} ${viewY} ${viewW} ${viewH}`}
            className="w-full h-full"
            preserveAspectRatio="xMidYMid meet"
        >
            {layout.map((obj, i) => {
                const [x, y, w, h] = obj.bbox;
                const color = getObjectColor(obj.label);
                const isStructural = obj.type === 'structural';

                return (
                    <g key={obj.id || i}>
                        <rect
                            x={x} y={y} width={w} height={h}
                            fill={color}
                            stroke={isStructural ? '#666' : '#888'}
                            strokeWidth={Math.max(1, viewW * 0.005)}
                            strokeDasharray={isStructural ? `${viewW * 0.01},${viewW * 0.005}` : 'none'}
                            rx={viewW * 0.01}
                            fillOpacity={0.8}
                        />
                        {w > viewW * 0.08 && h > viewH * 0.08 && (
                            <text
                                x={x + w / 2} y={y + h / 2}
                                textAnchor="middle" dominantBaseline="middle"
                                fontSize={Math.min(viewW * 0.04, 14)}
                                fill="#555"
                                className="pointer-events-none font-medium"
                            >
                                {obj.label.split('_')[0].charAt(0).toUpperCase()}
                            </text>
                        )}
                    </g>
                );
            })}
        </svg>
    );
}

// Thumbnail image component with error handling
function ThumbnailImage({ base64, name, onError }: { base64: string; name: string; onError: () => void }) {
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState(false);

    // Try different image formats
    const imageSrc = base64.startsWith('data:')
        ? base64
        : `data:image/png;base64,${base64}`;

    if (error) {
        return null; // Will trigger fallback to SVG preview
    }

    return (
        <>
            {!loaded && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
            )}
            <img
                src={imageSrc}
                alt={name}
                className={`w-full h-full object-contain rounded-lg transition-opacity ${loaded ? 'opacity-100' : 'opacity-0'}`}
                onLoad={() => setLoaded(true)}
                onError={() => {
                    console.warn(`Failed to load thumbnail for ${name}`);
                    setError(true);
                    onError();
                }}
            />
        </>
    );
}

export function LayoutSelector({
    variations,
    roomDimensions,
    isLoading,
    onSelect,
    onBack,
}: LayoutSelectorProps) {
    const [failedThumbnails, setFailedThumbnails] = useState<Set<number>>(new Set());

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <Loader2 className="w-12 h-12 animate-spin text-[#6b7aa1]" />
                <p className="text-gray-500 text-lg">Generating layout variations...</p>
                <p className="text-gray-400 text-sm">Our AI is creating 3 unique designs for you</p>
            </div>
        );
    }

    if (!variations || variations.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <ImageOff className="w-12 h-12 text-gray-400" />
                <p className="text-gray-500 text-lg">No layouts generated</p>
                <button
                    onClick={onBack}
                    className="px-4 py-2 bg-[#6b7aa1] text-white rounded-xl"
                >
                    Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button
                    onClick={onBack}
                    className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                >
                    <ArrowLeft className="w-5 h-5 text-gray-600" />
                </button>
                <div>
                    <h2 className="text-xl font-semibold text-gray-800">Choose Your Layout</h2>
                    <p className="text-sm text-gray-500">Select one of the AI-generated options</p>
                </div>
            </div>

            {/* Layout Cards */}
            <div className="grid gap-6 md:grid-cols-3">
                {variations.map((variation, index) => {
                    const hasThumbnail = variation.thumbnail_base64 && !failedThumbnails.has(index);

                    return (
                        <div
                            key={index}
                            className="card p-4 hover:shadow-lg transition-all cursor-pointer group border-2 border-transparent hover:border-[#6b7aa1]/30"
                            onClick={() => onSelect(variation)}
                        >
                            {/* Layout Preview */}
                            <div className="aspect-square bg-gradient-to-br from-[#faf9f7] to-[#f0eeea] rounded-xl mb-4 relative overflow-hidden p-2 border border-gray-100">
                                {/* Score Badge */}
                                {variation.score != null && (
                                    <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-full text-xs font-medium text-[#6b7aa1] z-10 shadow-sm">
                                        {Math.round(variation.score)}%
                                    </div>
                                )}

                                {/* Thumbnail or SVG Preview */}
                                {hasThumbnail ? (
                                    <ThumbnailImage
                                        base64={variation.thumbnail_base64!}
                                        name={variation.name}
                                        onError={() => {
                                            setFailedThumbnails(prev => new Set(prev).add(index));
                                        }}
                                    />
                                ) : (
                                    <LayoutPreview
                                        layout={variation.layout}
                                        roomDimensions={roomDimensions}
                                    />
                                )}

                                {/* Hover Overlay */}
                                <div className="absolute inset-0 bg-[#6b7aa1]/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-xl">
                                    <div className="bg-white rounded-full p-3 shadow-lg">
                                        <Check className="w-6 h-6 text-[#6b7aa1]" />
                                    </div>
                                </div>
                            </div>

                            {/* Layout Info */}
                            <h3 className="font-semibold text-gray-800 mb-1">{variation.name}</h3>
                            <p className="text-sm text-gray-500 line-clamp-2 mb-3">{variation.description}</p>

                            {/* Object count badges */}
                            <div className="flex gap-2 flex-wrap mb-3">
                                {variation.layout && (
                                    <>
                                        <span className="text-xs px-2 py-1 bg-[#e8f4e8] text-[#558b55] rounded-full">
                                            {variation.layout.filter(o => o.type === 'movable').length} movable
                                        </span>
                                        <span className="text-xs px-2 py-1 bg-[#f0f0f0] text-[#666] rounded-full">
                                            {variation.layout.filter(o => o.type === 'structural').length} fixed
                                        </span>
                                    </>
                                )}
                                {!hasThumbnail && (
                                    <span className="text-xs px-2 py-1 bg-[#fff3e0] text-[#e65100] rounded-full">
                                        SVG Preview
                                    </span>
                                )}
                            </div>

                            {/* Select Button */}
                            <button
                                className="w-full py-2 px-4 bg-[#6b7aa1] text-white rounded-xl font-medium hover:bg-[#5a6890] transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onSelect(variation);
                                }}
                            >
                                Select This Layout
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-4 text-xs text-gray-500 mt-6 pt-4 border-t border-gray-100">
                {(() => {
                    const uniqueLabels = new Set<string>();
                    variations.forEach(v => v.layout?.forEach(o => uniqueLabels.add(o.label)));

                    return Array.from(uniqueLabels).slice(0, 8).map(label => (
                        <div key={label} className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded" style={{ backgroundColor: getObjectColor(label) }} />
                            <span>{label.split('_')[0]}</span>
                        </div>
                    ));
                })()}
            </div>

            {/* Room Info */}
            {roomDimensions && (
                <div className="text-center text-sm text-gray-400">
                    Room: {roomDimensions.width_estimate.toFixed(0)} × {roomDimensions.height_estimate.toFixed(0)} px
                </div>
            )}
        </div>
    );
}