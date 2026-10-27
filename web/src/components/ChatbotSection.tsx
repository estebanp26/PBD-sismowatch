import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Sparkles, 
  Send, 
  Zap, 
  Database, 
  Trash2, 
  ChevronDown, 
  ChevronUp, 
  HelpCircle,
  Layers,
  ShieldCheck
} from 'lucide-react';
import { ChatMessage, UserSession } from '../types';
import { api } from '../services/api';

interface ChatbotSectionProps {
  session: UserSession | null;
}

// Renderizador ligero de Markdown para tablas, negritas, listas y enlaces
const renderMarkdown = (text: string) => {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let tableRows: string[] = [];
  let inTable = false;

  const flushTable = (keyPrefix: number) => {
    if (tableRows.length === 0) return null;
    const headerLine = tableRows[0];
    const dataLines = tableRows.slice(2); // Omitir la fila divisora |:---|
    const headers = headerLine.split('|').map(s => s.trim()).filter(Boolean);

    const tableNode = (
      <div key={`tbl-${keyPrefix}`} className="overflow-x-auto my-3 rounded-lg border border-slate-700/80 bg-slate-950/60 shadow-inner">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-800/80 text-slate-300 border-b border-slate-700">
              {headers.map((h, i) => (
                <th key={i} className="p-2.5 font-semibold text-slate-200">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80 text-slate-300">
            {dataLines.map((row, rIdx) => {
              const cells = row.split('|').map(s => s.trim()).filter(Boolean);
              return (
                <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                  {cells.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2.5">
                      {formatInlineMarkdown(cell)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
    tableRows = [];
    inTable = false;
    return tableNode;
  };

  const formatInlineMarkdown = (line: string): React.ReactNode => {
    // Reemplazar enlaces [texto](url)
    const linkRegex = /\[(.*?)\]\((.*?)\)/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        parts.push(replaceBoldAndCode(line.substring(lastIndex, match.index)));
      }
      parts.push(
        <a 
          key={match.index} 
          href={match[2]} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-400 hover:text-blue-300 underline font-medium"
        >
          {match[1]}
        </a>
      );
      lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < line.length) {
      parts.push(replaceBoldAndCode(line.substring(lastIndex)));
    }

    return parts.length > 0 ? parts : replaceBoldAndCode(line);
  };

  const replaceBoldAndCode = (str: string): React.ReactNode => {
    // Negrita **texto** y código `codigo`
    const boldRegex = /\*\*(.*?)\*\*/g;
    const pieces: React.ReactNode[] = [];
    let lastIdx = 0;
    let bMatch;

    while ((bMatch = boldRegex.exec(str)) !== null) {
      if (bMatch.index > lastIdx) {
        pieces.push(replaceCodeOnly(str.substring(lastIdx, bMatch.index)));
      }
      pieces.push(<strong key={bMatch.index} className="text-white font-semibold">{bMatch[1]}</strong>);
      lastIdx = boldRegex.lastIndex;
    }

    if (lastIdx < str.length) {
      pieces.push(replaceCodeOnly(str.substring(lastIdx)));
    }

    return pieces.length > 0 ? pieces : replaceCodeOnly(str);
  };

  const replaceCodeOnly = (str: string): React.ReactNode => {
    const codeRegex = /`(.*?)`/g;
    const segments: React.ReactNode[] = [];
    let lastIdx = 0;
    let cMatch;

    while ((cMatch = codeRegex.exec(str)) !== null) {
      if (cMatch.index > lastIdx) {
        segments.push(str.substring(lastIdx, cMatch.index));
      }
      segments.push(
        <code key={cMatch.index} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700/80 text-blue-300 font-mono text-[11px]">
          {cMatch[1]}
        </code>
      );
      lastIdx = codeRegex.lastIndex;
    }

    if (lastIdx < str.length) {
      segments.push(str.substring(lastIdx));
    }

    return segments.length > 0 ? segments : str;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Detección de Tabla Markdown
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      inTable = true;
      tableRows.push(line.trim());
      continue;
    } else if (inTable) {
      const tbl = flushTable(i);
      if (tbl) elements.push(tbl);
    }

    // Encabezados
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-sm font-bold text-white mt-2 mb-1 flex items-center gap-1.5">
          {formatInlineMarkdown(line.replace('### ', ''))}
        </h3>
      );
    } else if (line.startsWith('#### ')) {
      elements.push(
        <h4 key={i} className="text-xs font-semibold text-slate-200 mt-2 mb-1">
          {formatInlineMarkdown(line.replace('#### ', ''))}
        </h4>
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-2 border-blue-500 pl-3 py-1 my-1.5 text-xs text-slate-300 italic bg-blue-950/20 rounded-r">
          {formatInlineMarkdown(line.replace('> ', ''))}
        </blockquote>
      );
    } else if (line.startsWith('- ')) {
      elements.push(
        <li key={i} className="text-xs text-slate-300 ml-4 list-disc my-0.5">
          {formatInlineMarkdown(line.replace('- ', ''))}
        </li>
      );
    } else if (line.trim().length > 0) {
      elements.push(
        <p key={i} className="text-xs text-slate-300 my-1 leading-relaxed">
          {formatInlineMarkdown(line)}
        </p>
      );
    }
  }

  if (inTable) {
    const tbl = flushTable(lines.length);
    if (tbl) elements.push(tbl);
  }

  return elements;
};

export const ChatbotSection: React.FC<ChatbotSectionProps> = ({ session }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `### 🤖 Hola ${session?.fullName || 'Operador'}, soy el Asistente Analítico de SismoWatch.\n\nTengo dominio absoluto sobre las capas **Silver (Staging)** y **Gold (Curated)** de la arquitectura Medallion.\nPuedo responder cualquier consulta analítica con tiempos de respuesta optimizados en milisegundos:\n\n- Comparar registros entre **Silver y Gold**.\n- Identificar los sismos de **mayor magnitud** o más recientes.\n- Filtrar por **países y regiones** (Japón, Chile, California, México, Perú, etc.).\n- Monitorear **alertas de tsunami** y **métricas de calidad** de datos.\n- Consultar las conclusiones del **último reporte generado con IA**.\n\n*Selecciona una sugerencia abajo o escribe tu propia pregunta.*`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sourceLayer: 'Silver (Staging) & Gold (Curated)',
      executionTimeMs: 0.1,
      cached: true
    }
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [expandedSqlId, setExpandedSqlId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadSuggestions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSuggestions = async () => {
    try {
      const data = await api.getChatSuggestions();
      setSuggestions(data);
    } catch {
      setSuggestions([
        "¿Cuáles son los 5 sismos más fuertes registrados?",
        "¿Cuántos sismos hay en Silver (Staging) vs Gold (Curated)?",
        "¿Hay alertas de tsunami activas en las últimas 24 horas?",
        "¿Cómo está la calidad de los datos y cuántos registros fallaron?"
      ]);
    }
  };

  const handleSend = async (messageToSend?: string) => {
    const textToSend = messageToSend || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const historyPayload = messages.slice(-6).map(m => ({ sender: m.sender, text: m.text }));
      const res = await api.queryChatbot(userMsg.text, historyPayload);
      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        sender: 'assistant',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sourceLayer: res.source_layer,
        querySql: res.query_sql,
        executionTimeMs: res.execution_time_ms,
        cached: res.cached
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `⚠️ **Error:** No se pudo procesar la consulta. Detalle: ${err.message || 'Error de conexión'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        executionTimeMs: 0
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'reset',
        sender: 'assistant',
        text: '🧹 Historial limpiado. ¿En qué puedo ayudarte sobre los datos de Silver o Gold?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-slate-900/70 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
      {/* Cabecera del Asistente */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-900/90 border-b border-slate-800/80 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white flex items-center gap-1.5">
                Asistente SismoWatch
                <Sparkles className="w-4 h-4 text-amber-400" />
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Activo
              </span>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
              <span className="flex items-center gap-1 text-slate-300">
                <Database className="w-3 h-3 text-blue-400" />
                Dominio: Silver & Gold
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-amber-300/90">
                <Zap className="w-3 h-3 text-amber-400" />
                Motor Híbrido Caché & Fast-Path
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleClear}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
            title="Limpiar conversación"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Limpiar</span>
          </button>
        </div>
      </div>

      {/* Sugerencias Rápidas (Chips) */}
      <div className="px-6 py-2.5 bg-slate-950/40 border-b border-slate-800/60 overflow-x-auto flex items-center gap-2 scrollbar-thin">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1 shrink-0">
          <HelpCircle className="w-3 h-3 text-blue-400" />
          Preguntas Rápidas:
        </span>
        {suggestions.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            disabled={loading}
            className="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/90 hover:bg-blue-600/30 text-slate-300 hover:text-blue-300 border border-slate-700/80 hover:border-blue-500/40 text-[11px] font-medium transition-all"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Área de Mensajes */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-lg ${
                  isUser
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-none'
                    : 'bg-slate-800/90 border border-slate-700/80 text-slate-200 rounded-bl-none'
                }`}
              >
                {/* Cabecera del Mensaje */}
                <div className="flex items-center justify-between gap-3 mb-2 pb-1 border-b border-white/10 text-[10px]">
                  <span className="font-semibold flex items-center gap-1.5 opacity-90">
                    {isUser ? (
                      'Tú (Operador)'
                    ) : (
                      <>
                        <Bot className="w-3.5 h-3.5 text-blue-400" />
                        SismoWatch AI
                      </>
                    )}
                  </span>
                  <span className="opacity-70">{msg.timestamp}</span>
                </div>

                {/* Contenido */}
                <div className="text-xs leading-relaxed space-y-1">
                  {isUser ? msg.text : renderMarkdown(msg.text)}
                </div>

                {/* Métricas y Datos Técnicos (Solo en respuestas del Asistente) */}
                {!isUser && (msg.executionTimeMs !== undefined || msg.sourceLayer) && (
                  <div className="mt-3 pt-2 border-t border-slate-700/60 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-400">
                    <div className="flex items-center gap-2">
                      {msg.executionTimeMs !== undefined && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-amber-300">
                          <Zap className="w-3 h-3 text-amber-400" />
                          {msg.executionTimeMs} ms {msg.cached ? '(Caché)' : ''}
                        </span>
                      )}
                      {msg.sourceLayer && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-blue-300">
                          <Layers className="w-3 h-3 text-blue-400" />
                          {msg.sourceLayer}
                        </span>
                      )}
                    </div>

                    {msg.querySql && (
                      <button
                        onClick={() => setExpandedSqlId(expandedSqlId === msg.id ? null : msg.id)}
                        className="flex items-center gap-1 text-slate-400 hover:text-slate-200 font-mono text-[10px] transition-colors"
                      >
                        <span>Ver SQL</span>
                        {expandedSqlId === msg.id ? (
                          <ChevronUp className="w-3 h-3" />
                        ) : (
                          <ChevronDown className="w-3 h-3" />
                        )}
                      </button>
                    )}
                  </div>
                )}

                {/* SQL Colapsable */}
                {!isUser && msg.querySql && expandedSqlId === msg.id && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-950 border border-slate-700/80 font-mono text-[11px] text-emerald-400 overflow-x-auto shadow-inner">
                    <code>{msg.querySql}</code>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Indicador de Carga */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl rounded-bl-none p-4 shadow-lg flex items-center space-x-2 text-slate-400 text-xs">
              <Bot className="w-4 h-4 text-blue-400 animate-spin" />
              <span>Consultando motor analítico sobre Silver y Gold...</span>
              <span className="flex space-x-1 ml-2">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></span>
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Barra de Entrada de Pregunta */}
      <div className="p-4 bg-slate-900/90 border-t border-slate-800">
        <div className="flex items-center space-x-2 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500/50 shadow-inner">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pregúntale al Asistente sobre sismos, magnitudes, regiones, calidad de datos o Silver vs Gold..."
            disabled={loading}
            className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium shadow-md shadow-blue-600/30 transition-all flex items-center justify-center"
            title="Enviar pregunta"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-slate-500 mt-2 text-center flex items-center justify-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-500" />
          Consultas seguras de solo lectura en PostgreSQL sobre capas Silver y Gold.
        </p>
      </div>
    </div>
  );
};
