import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Sparkles, BookOpen, Bot, Lightbulb, ArrowUp } from "lucide-react";
import { SourceNode } from "@/services/chatApi";
import { useState, useEffect } from "react";

interface SearchEntryProps {
  query: string;
  response?: string;
  sources?: SourceNode[];
  suggestedQueries?: string[]; // Added
  onSuggestionClick?: (query: string) => void; // Added
  isLoading?: boolean;
  error?: string;
  status?: string;
}

const SkeletonLine = ({ width = "100%" }: { width?: string }) => (
    <div className={`h-4 bg-secondary/50 rounded animate-pulse`} style={{ width }} />
);

const SearchEntry = ({ 
  query, 
  response, 
  sources, 
  suggestedQueries, 
  onSuggestionClick,
  isLoading, 
  error, 
  status,
  onSourceClick, 
  isPopupEnabled = false 
}: SearchEntryProps & { 
  onSourceClick?: (source: SourceNode) => void; 
  isPopupEnabled?: boolean; 
}) => {
  const [loadingText, setLoadingText] = useState("กำลังประมวลผล...");

  useEffect(() => {
    if (!isLoading) return;
    
    if (status) {
        setLoadingText(status);
        return;
    }
    
    const steps = [
        "กำลังค้นหาข้อมูลรายวิชา...",
        "กำลังอ่านรีวิวจากนิสิต...",
        "กำลังวิเคราะห์ข้อมูล...",
        "กำลังเรียบเรียงคำตอบ..."
    ];
    let i = 0;
    
    // Set initial text immediately
    setLoadingText(steps[0]);

    const interval = setInterval(() => {
        i++;
        setLoadingText(steps[i % steps.length]);
    }, 2000); 

    return () => clearInterval(interval);
  }, [isLoading, status]);

  return (
    <div className="flex flex-col gap-6 animate-slide-up mb-12">
      {/* User Header */}
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-secondary/50 flex items-center justify-center">
            <Bot className="w-5 h-5 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold text-foreground leading-relaxed pt-1.5">
          {query}
        </h2>
      </div>

      {/* System Card */}
      <div className="ml-0 md:ml-14">
        <div className="glass-card p-6 shadow-sm border border-border/50 relative overflow-hidden group">
          {/* Card Decoration */}
          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary to-transparent opacity-50" />
          
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                {isLoading ? (
                    <div className="loading-dots gap-0.5">
                        <span className="bg-primary/50 w-0.5 h-0.5" />
                        <span className="bg-primary/50 w-0.5 h-0.5" />
                        <span className="bg-primary/50 w-0.5 h-0.5" />
                    </div>
                ) : (
                    <Sparkles className="w-4 h-4 text-primary" />
                )}
            </div>
            <span className="text-sm font-medium text-muted-foreground animate-fade-in key-{loadingText}">
                {isLoading ? (status || loadingText) : "คำตอบจาก AI"}
            </span>
          </div>

          <div className="prose prose-sm md:prose-base max-w-none dark:prose-invert prose-headings:text-primary prose-a:text-primary hover:prose-a:text-primary/80 transition-colors">
            {error ? (
                <div className="text-destructive p-4 bg-destructive/10 rounded-lg border border-destructive/20">
                    <p className="font-medium">เกิดข้อผิดพลาด</p>
                    <p className="text-sm opacity-90">{error}</p>
                </div>
            ) : (isLoading && !response) ? ( // Only show skeleton if loading AND no data yet
                <div className="space-y-3 py-2">
                    <SkeletonLine width="80%" />
                    <SkeletonLine width="90%" />
                    <SkeletonLine width="60%" />
                    <div className="h-2" /> 
                    <SkeletonLine width="75%" />
                    <SkeletonLine width="50%" />
                </div>
            ) : (
                <div className="min-h-[60px]"> {/* Prevent layout jump */}
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {response || ""}
                    </ReactMarkdown>
                    {/* Blinking cursor for streaming effect */}
                    {isLoading && response && (
                        <span className="inline-block w-1.5 h-4 bg-primary/80 align-middle ml-1 animate-pulse" />
                    )}
                </div>
            )}
          </div>

          {/* Suggested Queries Section */}
          {!isLoading && suggestedQueries && suggestedQueries.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border/50 animate-fade-in">
                <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm font-semibold text-muted-foreground">ลองถามคำถามเหล่านี้ดูไหม?</span>
                </div>
                <div className="flex flex-col gap-2">
                    {suggestedQueries.map((q, idx) => (
                        <button
                            key={idx}
                            onClick={() => onSuggestionClick?.(q)}
                            className="text-left px-4 py-3 rounded-lg bg-secondary/30 hover:bg-secondary/60 border border-border/50 transition-all text-sm text-foreground/90 hover:text-primary flex items-center justify-between group/btn"
                        >
                            <span>{q}</span>
                            <ArrowUp className="w-3 h-3 opacity-0 group-hover/btn:opacity-100 transition-opacity rotate-45" />
                        </button>
                    ))}
                </div>
            </div>
          )}

          {/* Sources Section */}
          {!isLoading && sources && sources.length > 0 && (
            <div className="mt-8 pt-6 border-t border-border/50 animate-fade-in">
                <h4 className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
                    <BookOpen className="w-4 h-4" />
                    อ้างอิงจาก
                </h4>
                <div className="flex flex-wrap gap-2">
                    {sources.map((source, idx) => (
                        <button 
                            key={`${source.node_id}-${idx}`}
                            onClick={() => isPopupEnabled && onSourceClick?.(source)}
                            disabled={!isPopupEnabled}
                            className={`
                                px-3 py-1.5 rounded-lg text-xs border border-border/50 flex flex-col transition-all text-left
                                ${isPopupEnabled 
                                    ? "bg-secondary/50 hover:bg-secondary cursor-pointer hover:border-primary/30" 
                                    : "bg-secondary/20 cursor-default opacity-80 text-secondary-foreground"
                                }
                            `}
                        >
                            <span className="font-medium truncate max-w-[200px]">
                                {source.metadata?.course_id || "เอกสาร"} 
                            </span>
                             {source.metadata?.type && (
                                <span className="opacity-60 text-[10px] uppercase tracking-wider">
                                    {source.metadata.type === 'summary_review' ? 'SUMMARY' : source.metadata.type}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchEntry;
