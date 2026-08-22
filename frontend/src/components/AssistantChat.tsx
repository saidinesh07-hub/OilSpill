import React, { useState } from 'react';
import { Bot, Send, Sparkles, MapPin, CheckCircle2, RefreshCw } from 'lucide-react';
import type { GroundedCitation } from '../types';
import { apiService } from '../services/api';

interface AssistantChatProps {
  activeTrackId?: string;
  onFlyTo?: (coords: [number, number]) => void;
}

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  citations?: GroundedCitation[];
  timestamp: string;
}

export const AssistantChat: React.FC<AssistantChatProps> = ({
  activeTrackId,
  onFlyTo,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: 'Grounded AI Assistant ready. Ask any question regarding active slick dimensions, temporal evolution, forecast trajectories, or explainable risk factors.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([
    'Why is this spill high risk?',
    'What changed since the previous observation?',
    'Which areas may be affected in next 24 hours?',
    'How large is the detected slick?',
  ]);

  const handleSend = async (questionText?: string) => {
    const query = questionText || inputQuery;
    if (!query.trim() || isLoading) return;

    const userMsg: Message = {
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const res = await apiService.queryAssistant(query, activeTrackId);
      const assistantMsg: Message = {
        sender: 'assistant',
        text: res.answer,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (res.suggested_followups?.length) {
        setSuggestedQuestions(res.suggested_followups);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: `Error retrieving grounded state: ${err.message || 'System unavailable'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col h-[520px] border border-slate-700/80">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center">
            <Bot className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-100">Grounded Intelligence Assistant</h3>
            <span className="text-[10px] text-emerald-400 flex items-center space-x-1">
              <CheckCircle2 className="w-2.5 h-2.5" />
              <span>Grounded in DB State Ledger</span>
            </span>
          </div>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1 mb-3 text-xs">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`rounded-xl px-3.5 py-2.5 max-w-[90%] leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none shadow-md'
                  : 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-bl-none'
              }`}
            >
              <div className="whitespace-pre-line">{m.text}</div>

              {/* Clickable Citations */}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-800 space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">
                    Grounded Database Citations:
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.citations.map((c, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          if (c.coordinates && onFlyTo) onFlyTo(c.coordinates);
                        }}
                        className="bg-slate-800 hover:bg-slate-700 border border-blue-500/40 text-blue-300 rounded px-2 py-0.5 text-[10px] flex items-center space-x-1 transition"
                        title={`Table: ${c.source_table} • Time: ${c.data_timestamp}`}
                      >
                        <MapPin className="w-2.5 h-2.5 text-blue-400" />
                        <span>{c.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <span className="text-[9px] text-slate-500 mt-1 px-1">{m.timestamp}</span>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 text-xs text-blue-400 bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Querying state ledger & verifying factual grounding...</span>
          </div>
        )}
      </div>

      {/* Suggested Questions Pills */}
      <div className="flex items-center space-x-1.5 overflow-x-auto custom-scrollbar pb-2 mb-2 text-[10px]">
        <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
        {suggestedQuestions.map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSend(sq)}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-full px-2.5 py-1 whitespace-nowrap transition"
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center space-x-2"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask about slick evolution, forecast trajectory, or risk..."
          className="flex-1 bg-slate-900/90 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading || !inputQuery.trim()}
          className="bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-3 py-2 text-xs transition disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
