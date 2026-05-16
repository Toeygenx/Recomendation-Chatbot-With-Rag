import { Bot, User, BookOpen } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SourceNode } from "@/services/chatApi";

interface ChatMessageProps {
  type: "user" | "bot";
  message: string;
  isLoading?: boolean;
  sources?: SourceNode[];
  onSourceClick?: (source: SourceNode) => void;
  isPopupEnabled?: boolean;
}

const ChatMessage = ({ 
  type, 
  message, 
  isLoading, 
  sources, 
  onSourceClick, 
  isPopupEnabled = false 
}: ChatMessageProps) => {
  return (
    <div
      className={`flex gap-3 animate-slide-up ${
        type === "user" ? "flex-row-reverse" : ""
      }`}
    >
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          type === "user"
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-foreground"
        }`}
      >
        {type === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className="flex flex-col gap-2 max-w-[80%]">
        <div
          className={`chat-bubble ${
            type === "user" ? "chat-bubble-user" : "chat-bubble-bot"
          }`}
        >
          {isLoading ? (
            <div className="loading-dots py-1">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources Section */}
        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1 animate-fade-in">
             <div className="w-full text-xs text-muted-foreground flex items-center gap-1 mb-1">
                <BookOpen className="w-3 h-3" />
                <span>อ้างอิงจาก:</span>
             </div>
             {sources.map((source, idx) => (
                <button
                  key={`${source.node_id}-${idx}`}
                  onClick={() => isPopupEnabled && onSourceClick?.(source)}
                  disabled={!isPopupEnabled}
                  className={`
                    text-xs px-2 py-1 rounded-md border border-border/50 
                    flex items-center gap-1 transition-all
                    ${isPopupEnabled 
                        ? "bg-secondary/50 hover:bg-secondary cursor-pointer hover:border-primary/30" 
                        : "bg-secondary/20 cursor-default opacity-80"
                    }
                  `}
                >
                  <span className="font-medium text-foreground/80">
                    {source.metadata.course_id || "Unknown"}
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase">
                    {source.metadata.type === 'summary_review' ? 'SUMMARY' : source.metadata.type || 'DOC'}
                  </span>
                </button>
             ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
