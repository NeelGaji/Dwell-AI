'use client';

import { useState, useCallback, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { ImageUpload } from '@/components/ImageUpload';
import { CanvasOverlay } from '@/components/CanvasOverlay';
import { ObjectsPanel } from '@/components/ObjectsPanel';
import { OptimizePanel } from '@/components/OptimizePanel';
import { LayoutSelector } from '@/components/LayoutSelector';
import { PerspectiveView } from '@/components/PerspectiveView';
import { ChatEditor } from '@/components/ChatEditor';
import { GeneratingOverlay } from '@/components/GeneratingOverlay';
import { useAnalyze } from '@/hooks/useAnalyze';
import { useOptimize } from '@/hooks/useOptimize';
import { usePerspective } from '@/hooks/usePerspective';
import { useChatEdit } from '@/hooks/useChatEdit';
import type { RoomObject, RoomDimensions, LayoutVariation, AppStage } from '@/lib/types';

interface AppState {
  stage: AppStage;
  image: string | null;
  roomDimensions: RoomDimensions | null;
  objects: RoomObject[];
  selectedObjectId: string | null;
  isAnalyzing: boolean;
  layoutVariations: LayoutVariation[];
  selectedVariation: LayoutVariation | null;
  perspectiveImage: string | null;
  currentLayout: RoomObject[];
  generatingStep: number; // Track which step of generation we're on
}

const initialState: AppState = {
  stage: 'analyze',
  image: null,
  roomDimensions: null,
  objects: [],
  selectedObjectId: null,
  isAnalyzing: false,
  layoutVariations: [],
  selectedVariation: null,
  perspectiveImage: null,
  currentLayout: [],
  generatingStep: 0,
};

// Generation steps for the loading animation
const GENERATION_STEPS = [
  { label: 'Analyzing room layout', duration: 2000 },
  { label: 'Designing Productivity Focus', duration: 3000 },
  { label: 'Designing Cozy Retreat', duration: 3000 },
  { label: 'Designing Creative Flow', duration: 3000 },
  { label: 'Generating preview images', duration: 4000 },
  { label: 'Finalizing layouts', duration: 2000 },
];

export default function PocketPlannerApp() {
  const [state, setState] = useState<AppState>(initialState);

  const { analyze } = useAnalyze();
  const { optimize, isLoading: isOptimizing } = useOptimize();
  const { generate: generatePerspective, isLoading: isGeneratingPerspective } = usePerspective();
  const { sendCommand, isLoading: isChatLoading, messages } = useChatEdit();

  // Auto-load test image on mount
  useEffect(() => {
    const loadTestImage = async () => {
      try {
        const response = await fetch('/test_img.jpg');
        const blob = await response.blob();
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result as string;
          setState(prev => ({ ...prev, image: base64 }));
          toast.success('Test image loaded! Click "Analyze Room" to start.');
        };
        reader.readAsDataURL(blob);
      } catch (error) {
        console.log('No test image found, starting fresh.');
      }
    };
    loadTestImage();
  }, []);

  // Step through generation animation
  useEffect(() => {
    if (!isOptimizing) {
      setState(prev => ({ ...prev, generatingStep: 0 }));
      return;
    }

    const stepInterval = setInterval(() => {
      setState(prev => {
        if (prev.generatingStep < GENERATION_STEPS.length - 1) {
          return { ...prev, generatingStep: prev.generatingStep + 1 };
        }
        return prev;
      });
    }, 2500);

    return () => clearInterval(stepInterval);
  }, [isOptimizing]);

  // Image Upload
  const handleImageSelect = useCallback((base64: string) => {
    setState(prev => ({
      ...prev,
      stage: 'analyze',
      image: `data:image/jpeg;base64,${base64}`,
      objects: [],
      selectedObjectId: null,
      layoutVariations: [],
      selectedVariation: null,
      perspectiveImage: null,
    }));
  }, []);

  // Analyze
  const handleAnalyze = useCallback(async () => {
    if (!state.image) return;

    setState(prev => ({ ...prev, isAnalyzing: true }));

    try {
      const base64 = state.image.split(',')[1];
      const response = await analyze(base64);

      setState(prev => ({
        ...prev,
        roomDimensions: response.room_dimensions,
        objects: response.objects,
        isAnalyzing: false,
        stage: 'analyze',
      }));

      toast.success(`Detected ${response.objects.length} objects`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Analysis failed');
      setState(prev => ({ ...prev, isAnalyzing: false }));
    }
  }, [state.image, analyze]);

  // Generate Layouts
  const handleGenerateLayouts = useCallback(async () => {
    if (!state.roomDimensions || state.objects.length === 0) return;

    setState(prev => ({ ...prev, generatingStep: 0 }));

    try {
      const lockedIds = state.objects
        .filter(o => o.is_locked)
        .map(o => o.id);

      const response = await optimize({
        current_layout: state.objects,
        locked_ids: lockedIds,
        room_dimensions: state.roomDimensions,
        image_base64: state.image ? state.image.split(',')[1] : undefined,
      });

      // Update state and transition to layouts stage
      setState(prev => ({
        ...prev,
        layoutVariations: response.variations,
        stage: 'layouts',
        generatingStep: 0,
      }));

      toast.success(`Generated ${response.variations.length} layout options`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate layouts');
      setState(prev => ({ ...prev, generatingStep: 0 }));
    }
  }, [state.roomDimensions, state.objects, state.image, optimize]);

  // Select Layout
  const handleSelectLayout = useCallback(async (variation: LayoutVariation) => {
    setState(prev => ({
      ...prev,
      selectedVariation: variation,
      currentLayout: variation.layout,
      stage: 'perspective',
    }));

    if (state.roomDimensions) {
      try {
        const response = await generatePerspective({
          layout: variation.layout,
          room_dimensions: state.roomDimensions,
          style: 'modern',
        });

        setState(prev => ({
          ...prev,
          perspectiveImage: response.image_base64,
        }));

        toast.success('Perspective view generated!');
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to generate perspective');
      }
    }
  }, [state.roomDimensions, generatePerspective]);

  // Object selection
  const handleObjectSelect = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      selectedObjectId: prev.selectedObjectId === id ? null : id,
    }));
  }, []);

  // Navigation handlers
  const handleBackToAnalyze = useCallback(() => {
    setState(prev => ({ ...prev, stage: 'analyze', layoutVariations: [] }));
  }, []);

  const handleBackToLayouts = useCallback(() => {
    setState(prev => ({ ...prev, stage: 'layouts' }));
  }, []);

  const handleBackToPerspective = useCallback(() => {
    setState(prev => ({ ...prev, stage: 'perspective' }));
  }, []);

  const handleContinueToChat = useCallback(() => {
    setState(prev => ({ ...prev, stage: 'chat' }));
  }, []);

  const handleChatCommand = useCallback(async (command: string) => {
    if (!state.roomDimensions || !state.currentLayout.length) return;

    try {
      const response = await sendCommand({
        command,
        current_layout: state.currentLayout,
        room_dimensions: state.roomDimensions,
        current_image_base64: state.perspectiveImage || undefined,
      });

      if (response.updated_layout) {
        setState(prev => ({
          ...prev,
          currentLayout: response.updated_layout!,
        }));
      }

      if (response.updated_image_base64) {
        setState(prev => ({
          ...prev,
          perspectiveImage: response.updated_image_base64!,
        }));
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Edit failed');
    }
  }, [state.roomDimensions, state.currentLayout, state.perspectiveImage, sendCommand]);

  // Render based on stage
  const renderContent = () => {
    // Show generating overlay when optimizing
    if (isOptimizing) {
      return (
        <GeneratingOverlay
          steps={GENERATION_STEPS}
          currentStep={state.generatingStep}
        />
      );
    }

    switch (state.stage) {
      case 'layouts':
        return (
          <LayoutSelector
            variations={state.layoutVariations}
            roomDimensions={state.roomDimensions}
            isLoading={false}
            onSelect={handleSelectLayout}
            onBack={handleBackToAnalyze}
          />
        );

      case 'perspective':
        return (
          <PerspectiveView
            imageBase64={state.perspectiveImage}
            isLoading={isGeneratingPerspective}
            layoutName={state.selectedVariation?.name}
            onContinue={handleContinueToChat}
            onBack={handleBackToLayouts}
          />
        );

      case 'chat':
        return (
          <ChatEditor
            imageBase64={state.perspectiveImage}
            layout={state.currentLayout}
            roomDimensions={state.roomDimensions}
            messages={messages}
            isLoading={isChatLoading}
            onSendCommand={handleChatCommand}
            onBack={handleBackToPerspective}
          />
        );

      case 'analyze':
      default:
        return (
          <div className="flex flex-col gap-6">
            {/* Main content area */}
            <div className="flex flex-col lg:flex-row gap-6">
              {/* Floor Plan Viewer */}
              <div className="flex-1 min-w-0">
                {state.image && state.objects.length > 0 ? (
                  <CanvasOverlay
                    imageUrl={state.image}
                    objects={state.objects}
                    selectedObjectId={state.selectedObjectId}
                    onObjectSelect={handleObjectSelect}
                  />
                ) : state.image ? (
                  <div className="floor-plan-container p-4">
                    <img
                      src={state.image}
                      alt="Floor plan"
                      className="w-full h-auto rounded-xl"
                    />
                    <div className="text-center mt-4">
                      <button
                        onClick={handleAnalyze}
                        disabled={state.isAnalyzing}
                        className="btn-analyze inline-flex items-center gap-2 px-6 py-3"
                      >
                        {state.isAnalyzing ? (
                          <>
                            <span className="animate-spin">⏳</span>
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <span>🔍</span>
                            Analyze Room
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ) : (
                  <ImageUpload
                    onImageSelect={handleImageSelect}
                    currentImage={state.image}
                    disabled={state.isAnalyzing}
                  />
                )}
              </div>

              {/* Right Panel - Optimize */}
              {state.objects.length > 0 && (
                <div className="w-full lg:w-80 shrink-0">
                  <OptimizePanel
                    objects={state.objects}
                    roomDimensions={state.roomDimensions}
                    isGenerating={isOptimizing}
                    onGenerate={handleGenerateLayouts}
                    onReanalyze={handleAnalyze}
                    isAnalyzing={state.isAnalyzing}
                  />
                </div>
              )}
            </div>

            {/* Detected Objects Panel - Below the image */}
            {state.objects.length > 0 && (
              <ObjectsPanel
                objects={state.objects}
                selectedObjectId={state.selectedObjectId}
                onObjectSelect={handleObjectSelect}
              />
            )}

            {/* Room dimensions */}
            {state.roomDimensions && (
              <div className="text-center text-sm text-gray-400">
                Room: {state.roomDimensions.width_estimate.toFixed(1)} × {state.roomDimensions.height_estimate.toFixed(1)} ft
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f3f0]">
      <Toaster
        position="top-right"
        toastOptions={{
          className: '!bg-white !text-gray-800 !shadow-lg',
          style: { borderRadius: '12px' },
        }}
      />

      {/* Header */}
      <header className="py-8 text-center">
        <h1 className="title-script text-4xl md:text-5xl text-[#6b7aa1]">
          Pocket Planner
        </h1>
        {/* Stage indicator */}
        <div className="flex justify-center gap-2 mt-4">
          {['analyze', 'layouts', 'perspective', 'chat'].map((s) => (
            <div
              key={s}
              className={`w-2 h-2 rounded-full transition-colors ${state.stage === s ? 'bg-[#6b7aa1]' : 'bg-gray-300'
                }`}
            />
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 pb-8">
        <div className="card p-4 md:p-6">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}