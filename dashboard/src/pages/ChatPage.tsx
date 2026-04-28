import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { sendChatMessage } from '../lib/api';
import ChatBubble from '../components/ChatBubble';
import { MessageSquare, Send, Bot, Fuel, Wrench, Zap } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agente?: string;
  loading?: boolean;
}

const suggestedQuestions = [
  { text: '¿Qué buses tienen mayor consumo y cuáles tienen riesgo mecánico?', icon: Zap },
  { text: '¿Cuál es el estado general de la flota ahora mismo?', icon: Zap },
  { text: 'Analiza el bus 7313: consumo y estado mecánico', icon: Zap },
  { text: '¿Qué alertas prioritarias hay y qué las está causando?', icon: Zap },
];

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-fill from bus selection on map
  useEffect(() => {
    const bus = searchParams.get('bus');
    const context = searchParams.get('context');
    if (bus && messages.length === 0) {
      const prompt = context
        ? `Analiza el bus ${bus}. Contexto: ${context}`
        : `Analiza el estado completo del bus ${bus}: consumo de combustible y estado mecánico`;
      setInput(prompt);
      inputRef.current?.focus();
    }
  }, [searchParams, messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const prompt = text || input.trim();
    if (!prompt || sending) return;

    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: prompt },
      { id: assistantMsgId, role: 'assistant', content: '', agente: 'ambos', loading: true },
    ]);
    setInput('');
    setSending(true);

    try {
      const response = await sendChatMessage(prompt, 'ambos');
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, content: response.respuesta, loading: false, agente: response.agente_usado }
            : m
        )
      );
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, content: `Error: ${err.message}`, loading: false }
            : m
        )
      );
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const lastAssistantId = [...messages].reverse().find(m => m.role === 'assistant')?.id;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center gap-3 shrink-0">
        <MessageSquare className="w-6 h-6 text-red-400" />
        <div>
          <h1 className="text-white font-bold">Chat con Agentes IA</h1>
          <p className="text-slate-400 text-xs flex items-center gap-2">
            <span className="flex items-center gap-1"><Fuel className="w-3 h-3 text-amber-400" /> Combustible</span>
            <span className="text-slate-600">+</span>
            <span className="flex items-center gap-1"><Wrench className="w-3 h-3 text-blue-400" /> Mantenimiento</span>
            <span className="text-slate-600">— respuesta unificada</span>
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-slate-600 mb-4" />
            <h2 className="text-white text-xl font-bold mb-2">ADO MobilityIA</h2>
            <p className="text-slate-400 mb-6 max-w-md">
              Ambos agentes responden a tu pregunta simultáneamente.
              Combustible analiza consumo y eficiencia. Mantenimiento evalúa riesgo mecánico.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-lg">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q.text)}
                  className="flex items-center gap-2 p-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-left text-sm text-slate-300 transition-colors"
                >
                  <q.icon className="w-4 h-4 text-slate-500 shrink-0" />
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <ChatBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            agente={msg.agente}
            loading={msg.loading}
            isLatest={msg.id === lastAssistantId}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50 shrink-0">
        <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Pregunta sobre la flota — ambos agentes responden..."
            disabled={sending}
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-slate-700 text-white rounded-xl transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
