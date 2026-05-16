import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Square, Search, ArrowUp } from "lucide-react";
import Layout from "@/components/Layout";
import SearchEntry from "@/components/SearchEntry";
import { useMutation } from "@tanstack/react-query";
import { fetchChatResponse, SourceNode } from "@/services/chatApi";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

// MARK: - Configuration
const ENABLE_SOURCE_POPUP = true; // Toggle this to false to disable source clicking

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  sources?: SourceNode[];
  suggestedQueries?: string[]; // Added
  isLoading?: boolean;
  error?: string;
  status?: string;
}

const ChatBot = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  
  // Source Viewer State
  const [viewSource, setViewSource] = useState<SourceNode | null>(null);
  
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const { mutate: sendMessage, isPending: isGlobalLoading } = useMutation({
    mutationFn: ({ query, signal }: { query: string; signal?: AbortSignal }) => 
      fetchChatResponse(
        query, 
        signal,
        // onStatus
        (status) => {
             setMessages((prev) => prev.map(msg => 
                (msg.isLoading && msg.type === 'bot') ? { ...msg, status } : msg
            ));
        },
        // onToken
        (token) => {
             setMessages((prev) => prev.map(msg => 
                (msg.isLoading && msg.type === 'bot') ? { ...msg, content: msg.content + token } : msg
            ));
        }
      ),
    onSuccess: (data) => {
      setMessages((prev) => {
        return prev.map(msg => {
            if (msg.isLoading && msg.type === 'bot') {
                return {
                    ...msg,
                    content: data.response, // Ensure final consistency
                    sources: data.sources,
                    suggestedQueries: data.suggested_queries, // Map suggestions
                    isLoading: false,
                    status: undefined // Clear status on finish
                };
            }
            return msg;
        });
      });
    },
    onError: (error) => {
      setMessages((prev) => {
        return prev.map(msg => {
            if (msg.isLoading && msg.type === 'bot') {
                return {
                    ...msg,
                    content: error.message || "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์",
                    error: error.message,
                    isLoading: false
                };
            }
            return msg;
        });
      });
    },
    onSettled: () => {
      setAbortController(null);
    }
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to new content logic
  useEffect(() => {
    if (messages.length > 0) {
         messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [messages]);

  const handleSend = (queryOverride?: string) => {
    const finalQuery = queryOverride || input.trim();
    if (!finalQuery || isGlobalLoading) return; 

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: finalQuery,
    };

    const botPlaceholder: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: "",
        isLoading: true
    };

    const controller = new AbortController();
    setAbortController(controller);

    // Append both user message and bot placeholder
    setMessages((prev) => [...prev, userMessage, botPlaceholder]);
    
    // Always clear input
    setInput("");
    
    sendMessage({ query: finalQuery, signal: controller.signal });
  };

  const handleSuggestionClick = (query: string) => {
      handleSend(query);
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Render Logic
  const renderSearchFeed = () => {
    // Group messages into pairs [User, Bot]
    const pairs = [];
    for (let i = 0; i < messages.length; i++) {
        if (messages[i].type === 'user') {
            const userMsg = messages[i];
            const nextMsg = messages[i+1];
            const botMsg = (nextMsg && nextMsg.type === 'bot') ? nextMsg : null;
            
            if (botMsg) {
                pairs.push({ user: userMsg, bot: botMsg });
                i++; // Skip next since it's the bot response
            }
        }
    }

    return (
        <div className="flex flex-col gap-0 pb-12">
            {pairs.map((pair, idx) => (
                <div key={pair.user.id} ref={idx === pairs.length - 1 ? messagesEndRef : null} className="scroll-mt-24">
                     <SearchEntry 
                        query={pair.user.content}
                        response={pair.bot.content}
                        sources={pair.bot.sources}
                        isLoading={pair.bot.isLoading}
                        error={pair.bot.error}
                        status={pair.bot.status} // Pass status
                        suggestedQueries={pair.bot.suggestedQueries} // Pass suggestions
                        onSuggestionClick={handleSuggestionClick} // Pass handler
                        onSourceClick={setViewSource}
                        isPopupEnabled={ENABLE_SOURCE_POPUP}
                     />
                     {/* Divider between threads */}
                     {idx < pairs.length - 1 && (
                        <div className="h-px bg-border w-full my-8" />
                     )}
                </div>
            ))}
        </div>
    );
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        {/* Welcome / Hero Section */}
        {messages.length === 0 && (
          <div className="text-center py-16 animate-fade-in">
            <div className="relative inline-flex items-center justify-center mb-6">
              <div className="absolute w-40 h-40 bg-gradient-radial from-primary/30 via-primary/10 to-transparent rounded-full blur-2xl" />
              <div className="relative inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary">
                <Sparkles className="w-10 h-10 text-primary-foreground" />
              </div>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              ถามเกี่ยวกับ<span className="text-primary"> รายวิชา GenEd</span>
            </h1>
            <p className="text-muted-foreground text-lg max-w-md mx-auto mb-8">
              ค้นหาข้อมูลรายวิชา คำอธิบาย และรีวิวจากนิสิต
            </p>

            <div className="mt-8 flex flex-wrap justify-center gap-2">
              {[
                "วิชา 01999033 กับ 01387101 ต่างกันยังไง?",
                "วิชา Arts of living เรียนเกี่ยวกับอะไร?",
                "ใช้งานยังไง?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="px-4 py-2 text-sm bg-secondary/50 hover:bg-secondary border border-border rounded-full text-muted-foreground hover:text-foreground transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Content Area */}
        {messages.length > 0 && (
            <div className="flex-1">
                {renderSearchFeed()}
            </div>
        )}

        {/* Floating Input Area */}
        <div className={`fixed bottom-0 left-0 right-0 px-2 py-4 sm:p-4 transition-all duration-300 ${messages.length > 0 ? "bg-gradient-to-t from-background via-background/95 to-transparent pt-12" : ""}`}>
          <div className="container mx-auto max-w-3xl">
            <div className="relative transition-all duration-300 shadow-lg">
                <div className="glass-card p-2 flex items-center gap-2 rounded-2xl border-primary/20 bg-card/80 backdrop-blur-xl">
                
                   <div className="pl-3 text-muted-foreground shrink-0">
                        <Search className="w-5 h-5" />
                   </div>

                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    maxLength={200}
                    placeholder="ค้นหารายวิชาหรือถามคำถาม..."
                    className="flex-1 min-w-0 bg-transparent px-3 sm:px-4 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none"
                    disabled={isGlobalLoading}
                  />
                  
                  {isGlobalLoading ? (
                    <button
                      onClick={handleStop}
                      className="p-3 rounded-xl bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors"
                    >
                      <Square className="w-4 h-4 fill-current" />
                    </button>
                  ) : (
                    <button
                      onClick={() => handleSend()}
                      disabled={!input.trim()}
                      className={`p-3 rounded-xl transition-all duration-200 ${
                        input.trim() 
                            ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20' 
                            : 'bg-secondary text-muted-foreground'
                      }`}
                    >
                        <ArrowUp className="w-5 h-5" />
                    </button>
                  )}
                </div>
            </div>
            <p className="text-center text-xs text-muted-foreground mt-2">
              AI อาจเกิดข้อผิดพลาดได้ กรุณาตรวจสอบข้อมูลอีกครั้ง
            </p>
          </div>
        </div>

        {/* View Source Dialog */}
        <Dialog open={!!viewSource} onOpenChange={(open) => !open && setViewSource(null)}>
            <DialogContent className="bg-card border-border sm:max-w-xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <div className="flex items-center gap-2 mb-2">
                        <span className={`text-xs px-2 py-1 rounded-md font-mono uppercase ${
                            ['summary_review', 'full_course_info'].includes(viewSource?.metadata.type || '') 
                            ? 'bg-purple-500/10 text-purple-500 border border-purple-500/20' 
                            : 'bg-primary/10 text-primary'
                        }`}>
                            {['summary_review', 'full_course_info'].includes(viewSource?.metadata.type || '') ? 'SUMMARY AI' : (viewSource?.metadata.type || 'SOURCE')}
                        </span>
                        <DialogTitle>{viewSource?.metadata.course_name || viewSource?.metadata.course_id}</DialogTitle>
                    </div>
                    <DialogDescription>
                         รหัสวิชา: {viewSource?.metadata.course_id}
                         {viewSource?.metadata.faculty && ` • คณะ: ${viewSource.metadata.faculty}`}
                    </DialogDescription>
                </DialogHeader>
                
                <div className="space-y-4 pt-2">
                    {/* Scores Section for Summaries */}
                    {['summary_review', 'full_course_info'].includes(viewSource?.metadata.type || '') && (
                        <>
                            <div className="flex items-center gap-2 p-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-xs text-purple-600 dark:text-purple-300">
                                <Sparkles className="w-3 h-3" />
                                <span>เนื้อหานี้ถูกสรุปโดย AI จากรีวิวของผู้เรียนทั้งหมด/ข้อมูลรายวิชา</span>
                            </div>

                            {/* Only show scores if they exist (full_course_info might not have scores or uses different keys) */}
                            {(viewSource?.metadata.difficulty !== undefined) && (
                                <div className="grid grid-cols-3 gap-2 p-3 bg-secondary/30 rounded-lg border border-border/50">
                                    <div className="text-center p-2 rounded bg-background/50">
                                        <div className="text-xs text-muted-foreground mb-1">ความยาก</div>
                                        <div className="font-semibold text-primary">{viewSource.metadata.difficulty}/3</div>
                                    </div>
                                    <div className="text-center p-2 rounded bg-background/50">
                                        <div className="text-xs text-muted-foreground mb-1">งาน</div>
                                        <div className="font-semibold text-primary">{viewSource.metadata.workload}/3</div>
                                    </div>
                                    <div className="text-center p-2 rounded bg-background/50">
                                        <div className="text-xs text-muted-foreground mb-1">เกรด</div>
                                        <div className="font-semibold text-primary">{viewSource.metadata.grading}/3</div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    <div className="p-4 rounded-lg bg-secondary/30 border border-border text-sm leading-relaxed whitespace-pre-wrap max-h-[400px] overflow-y-auto">
                        {viewSource?.text || "ไม่มีเนื้อหา"}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default ChatBot;
