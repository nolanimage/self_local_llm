'use client'

import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import Link from 'next/link'
import { 
  Send, 
  Database, 
  User, 
  Bot, 
  RefreshCcw, 
  CheckCircle2, 
  Search,
  BrainCircuit,
  Settings,
  Copy,
  Clock,
  ArrowRight,
  LogOut,
  LogIn,
  History,
  Trash2
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface Message {
  role: 'user' | 'assistant'
  content: string
  metadata?: any
  suggestions?: string[]
  timestamp: string
}

interface UserProfile {
  id: number
  username: string
}

interface HistoryItem {
  id: number
  prompt: string
  response: string
  rag_used: boolean
  articles_found: number
  created_at: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState(true)
  const [ragStats, setRagStats] = useState({ total_articles: 0 })
  const [status, setStatus] = useState('')
  const [user, setUser] = useState<UserProfile | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [trending, setTrending] = useState<any[]>([])
  const [rateLimit, setRateLimit] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    loadRAGStats()
    loadTrending()
    
    // Check local storage for logged in user
    const savedUser = localStorage.getItem('chat_user')
    if (savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser)
        setUser(parsedUser)
        loadHistory(parsedUser.id)
        loadRateLimit(String(parsedUser.id))
      } catch (e) {
        localStorage.removeItem('chat_user')
      }
    }
    
    // Restore conversation from session storage
    const savedMessages = sessionStorage.getItem('chat_messages')
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages)
        setMessages(parsedMessages)
      } catch (e) {
        sessionStorage.removeItem('chat_messages')
      }
    }
  }, [])

  // Save messages to session storage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      sessionStorage.setItem('chat_messages', JSON.stringify(messages))
    }
  }, [messages])

  const loadRAGStats = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/rag/stats`)
      setRagStats(response.data)
    } catch (error) {
      console.error('Error loading RAG stats:', error)
    }
  }

  const loadTrending = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/trending`)
      setTrending(response.data.trending || [])
    } catch (error) {
      console.error('Error loading trending:', error)
    }
  }

  const loadRateLimit = async (userId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/rate-limit/${userId}`)
      setRateLimit(response.data)
    } catch (error) {
      console.error('Error loading rate limit:', error)
    }
  }

  const loadHistory = async (userId: number) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/history/${userId}`)
      setHistory(response.data.history || [])
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const handleLogin = async () => {
    if (!loginUsername.trim()) return
    setLoginLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      console.log('Attempting login for:', loginUsername.trim())
      const response = await axios.post(`${apiUrl}/api/auth/login`, { username: loginUsername.trim() })
      console.log('Login response:', response.data)
      const loggedInUser = response.data
      setUser(loggedInUser)
      localStorage.setItem('chat_user', JSON.stringify(loggedInUser))
      setShowLoginModal(false)
      setLoginUsername('')
      loadHistory(loggedInUser.id)
    } catch (error: any) {
      console.error('Login error:', error)
      alert(`Login failed: ${error.response?.data?.detail || error.message}`)
    } finally {
      setLoginLoading(false)
    }
  }

  const handleLogout = () => {
    setUser(null)
    setHistory([])
    localStorage.removeItem('chat_user')
  }

  const selectHistoryItem = (item: HistoryItem) => {
    setMessages([
      { role: 'user', content: item.prompt, timestamp: item.created_at.slice(11, 16) },
      { role: 'assistant', content: item.response, timestamp: item.created_at.slice(11, 16), metadata: { rag_used: item.rag_used, articles_found: item.articles_found } }
    ])
  }

  const sendMessage = async (overrideInput?: string) => {
    const textToSend = overrideInput || input
    if (!textToSend.trim() || loading) return

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMessage: Message = {
      role: 'user',
      content: textToSend.trim(),
      timestamp: now
    }

    setMessages(prev => [...prev, userMessage])
    if (!overrideInput) setInput('')
    setLoading(true)
    setStatus('Agent is thinking...')

    // Add empty assistant message for streaming
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: now,
      metadata: null
    }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await fetch(`${apiUrl}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: userMessage.content,
          history: messages.slice(-6).map(m => ({ role: m.role, content: m.content })), // Send last 6 turns
          user_id: user?.id 
        })
      })

      if (!response.ok) throw new Error('Network response was not ok')
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      if (reader) {
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          
          // Keep the last partial line in the buffer
          buffer = lines.pop() || ''
          
          for (const line of lines) {
            const trimmedLine = line.trim()
            if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue
            
            try {
              const data = JSON.parse(trimmedLine.slice(6))
              
                if (data.type === 'status') {
                  setStatus(data.content)
                } else if (data.type === 'metadata') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const last = newMessages[newMessages.length - 1]
                    last.metadata = data.data
                    if (data.data.suggestions) {
                      last.suggestions = data.data.suggestions
                    }
                    return newMessages
                  })
                } else if (data.type === 'chunk') {
                fullContent += data.content
                setMessages(prev => {
                  const newMessages = [...prev]
                  newMessages[newMessages.length - 1].content = fullContent
                  return newMessages
                })
              } else if (data.type === 'error') {
                throw new Error(data.content)
              }
            } catch (e) {
              console.error('Error parsing line:', line, e)
            }
          }
        }
      }

      setConnected(true)
      if (user) {
        loadHistory(user.id) // Refresh history after message
        loadRateLimit(String(user.id)) // Refresh rate limit quota
      }
      loadTrending() // Refresh trending topics
    } catch (error: any) {
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1].content = `**Error:** ${error.message || 'Connection lost'}`
        return newMessages
      })
      setConnected(false)
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="flex h-screen bg-white dark:bg-black text-gray-900 dark:text-gray-100 overflow-hidden font-sans">
      
      {/* Sidebar */}
      <div className="w-72 bg-gray-50 dark:bg-black border-r border-gray-200 dark:border-gray-800 flex flex-col hidden md:flex">
        <div className="p-6 flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-xl">
            <BrainCircuit className="text-white w-6 h-6" />
          </div>
          <h1 className="font-bold text-xl tracking-tight">Self LLM</h1>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 space-y-2 custom-scrollbar">
          <button 
            onClick={() => setMessages([])}
            className="w-full flex items-center gap-3 px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-xl font-medium hover:opacity-80 transition mb-6"
          >
            <RefreshCcw className="w-4 h-4" /> New Chat
          </button>

          <button 
            onClick={() => {
              setMessages([])
              sessionStorage.removeItem('chat_messages')
            }}
            className="w-full flex items-center gap-3 px-4 py-3 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl font-medium transition mb-6 text-sm"
          >
            <Trash2 className="w-4 h-4" /> Clear Session
          </button>
          
          {user && (
            <>
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 mb-2 flex items-center gap-2">
                <History className="w-3 h-3" /> Chat History
              </div>
              <div className="space-y-1 mb-6">
                {history.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-gray-400 italic bg-gray-50/50 dark:bg-gray-800/20 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
                    No recent queries
                  </div>
                ) : (
                  history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => selectHistoryItem(item)}
                      className="w-full text-left px-4 py-2 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition line-clamp-1 text-gray-600 dark:text-gray-400 border border-transparent hover:border-gray-200 dark:hover:border-gray-700"
                    >
                      {item.prompt}
                    </button>
                  ))
                )}
              </div>
            </>
          )}

          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 mb-2">System Status</div>
          <div className="px-4 py-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">Server</span>
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`}></span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">RAG Articles</span>
              <span className="text-xs font-mono bg-gray-200 dark:bg-gray-800 px-2 py-0.5 rounded">{ragStats.total_articles}</span>
            </div>
            {rateLimit && (
              <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800">
                <span className="text-sm">Quota</span>
                <span className={`text-xs font-mono px-2 py-0.5 rounded ${rateLimit.remaining > 10 ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'}`}>
                  {rateLimit.remaining}/{rateLimit.limit}
                </span>
              </div>
            )}
          </div>

          {trending.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 mb-2">🔥 Trending</div>
              <div className="px-4 py-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 space-y-2">
                {trending.slice(0, 5).map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="truncate flex-1 text-gray-600 dark:text-gray-400">{item.query}</span>
                    <span className="ml-2 text-gray-400 font-mono">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <Link 
            href="/knowledge"
            className="w-full flex items-center justify-between px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition group"
          >
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5" /> Knowledge Base
            </div>
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        
        {/* Top Navbar */}
        <div className="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-black flex items-center justify-between px-8 z-10">
          <div className="flex items-center gap-2">
            <span className="font-semibold">Qwen2.5 1.5B</span>
            <span className="text-xs bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded-full">Agentic RAG</span>
          </div>
          <div className="flex items-center gap-4">
            {user ? (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <User className="w-4 h-4 text-indigo-500" />
                  <span className="text-sm font-medium">{user.username}</span>
                </div>
                <button 
                  onClick={handleLogout}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <button 
                onClick={() => setShowLoginModal(true)}
                className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white text-sm font-bold rounded-lg hover:bg-indigo-700 transition"
              >
                <LogIn className="w-4 h-4" /> Login
              </button>
            )}
            <div className="h-6 w-px bg-gray-200 dark:bg-gray-800 mx-1"></div>
            <button className="text-gray-500 hover:text-indigo-500 transition"><Settings className="w-5 h-5" /></button>
          </div>
        </div>

        {/* Login Modal */}
        {showLoginModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-md bg-black/40">
            <div className="bg-white dark:bg-black w-full max-w-sm rounded-3xl shadow-2xl p-8 border border-gray-200 dark:border-gray-800 animate-in zoom-in-95 duration-200">
              <div className="flex flex-col items-center text-center mb-8">
                <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/40 rounded-2xl flex items-center justify-center mb-4">
                  <User className="w-8 h-8 text-indigo-500" />
                </div>
                <h2 className="text-2xl font-bold">Welcome Back</h2>
                <p className="text-sm text-gray-500 mt-1">Enter your username to access your history</p>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1 mb-2 block">Username</label>
                  <input 
                    type="text" 
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !loginLoading && handleLogin()}
                    placeholder="e.g. nolanlu"
                    disabled={loginLoading}
                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 transition disabled:opacity-50 text-gray-900 dark:text-white"
                    autoFocus
                  />
                </div>
                <button 
                  onClick={handleLogin}
                  disabled={loginLoading || !loginUsername.trim()}
                  className="w-full py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loginLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Logging in...</span>
                    </>
                  ) : (
                    'Continue'
                  )}
                </button>
                <button 
                  onClick={() => {
                    setShowLoginModal(false)
                    setLoginUsername('')
                  }}
                  disabled={loginLoading}
                  className="w-full py-3 text-gray-500 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-40 py-20">
              <div className="bg-gray-100 dark:bg-gray-800 p-6 rounded-full mb-6">
                <Bot className="w-16 h-16 text-indigo-500" />
              </div>
              <h2 className="text-3xl font-bold mb-2">How can I help you?</h2>
              <p className="max-w-md">I am your agentic assistant with a 2-step reflection loop and deep knowledge from your local RSS feeds.</p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-8 pb-10">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center ${
                    msg.role === 'user' ? 'bg-indigo-600' : 'bg-gray-100 dark:bg-gray-800'
                  }`}>
                    {msg.role === 'user' ? <User className="text-white w-5 h-5" /> : <Bot className="w-5 h-5 text-gray-700 dark:text-gray-300" />}
                  </div>
                  
                  <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-[85%]`}>
                    <div className={`p-5 rounded-3xl ${
                      msg.role === 'user' 
                        ? 'bg-indigo-600 text-white rounded-tr-none shadow-lg shadow-indigo-500/10' 
                        : 'bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-tl-none shadow-sm'
                    }`}>
                      <div className="prose prose-sm dark:prose-invert max-w-none min-h-[1.5em]">
                        {msg.content === '' && msg.role === 'assistant' ? (
                          <div className="flex items-center gap-2 text-gray-400">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce"></span>
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                          </div>
                        ) : (
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code({node, inline, className, children, ...props}: any) {
                                const match = /language-(\w+)/.exec(className || '')
                                return !inline && match ? (
                                  <SyntaxHighlighter
                                    style={vscDarkPlus}
                                    language={match[1]}
                                    PreTag="div"
                                    className="rounded-lg !my-4 shadow-inner"
                                    {...props}
                                  >
                                    {String(children).replace(/\n$/, '')}
                                  </SyntaxHighlighter>
                                ) : (
                                  <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-indigo-500 font-mono" {...props}>
                                    {children}
                                  </code>
                                )
                              }
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        )}
                      </div>
                    </div>

                    {msg.suggestions && msg.suggestions.length > 0 && !loading && idx === messages.length - 1 && (
                      <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {msg.suggestions.map((suggestion, i) => (
                          <button
                            key={i}
                            onClick={() => sendMessage(suggestion)}
                            className="px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 text-xs font-bold rounded-xl border border-indigo-100 dark:border-indigo-900/30 hover:bg-indigo-600 hover:text-white transition shadow-sm"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                    
                    <div className="flex items-center gap-3 mt-2 px-2 text-[10px] text-gray-400 uppercase font-semibold">
                      <span>{msg.timestamp}</span>
                      {msg.role === 'assistant' && msg.content !== '' && (
                        <button 
                          onClick={() => copyToClipboard(msg.content)}
                          className="hover:text-indigo-500 transition flex items-center gap-1"
                        >
                          <Copy className="w-3 h-3" /> Copy
                        </button>
                      )}
                    </div>

                    {msg.metadata && (
                      <div className="mt-4 w-full bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl p-4 overflow-hidden">
                        <div className="flex items-center gap-2 mb-3 text-xs font-bold text-gray-500 uppercase tracking-widest">
                          <CheckCircle2 className="w-4 h-4 text-green-500" /> Agent Execution Log
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-white dark:bg-black p-2 rounded-xl border border-gray-200 dark:border-gray-700">
                            <div className="text-[10px] text-gray-400 uppercase">RAG Status</div>
                            <div className="text-sm font-semibold">{msg.metadata.rag_used ? 'Enabled' : 'Bypassed'}</div>
                          </div>
                          <div className="bg-white dark:bg-black p-2 rounded-xl border border-gray-200 dark:border-gray-700">
                            <div className="text-[10px] text-gray-400 uppercase">Articles</div>
                            <div className="text-sm font-semibold text-indigo-500">{msg.metadata.articles_found} Found</div>
                          </div>
                        </div>

                        {msg.metadata.timings && (
                          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800">
                            <div className="text-[10px] text-gray-400 uppercase font-bold mb-2">Performance</div>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] font-mono">
                              {msg.metadata.timings.planning && <div><span className="text-blue-500">PLAN:</span> {msg.metadata.timings.planning}s</div>}
                              {msg.metadata.timings.search && <div><span className="text-green-500">SEARCH:</span> {msg.metadata.timings.search}s</div>}
                              {msg.metadata.timings.generation && <div><span className="text-purple-500">GEN:</span> {msg.metadata.timings.generation}s</div>}
                              <div className="ml-auto font-bold text-indigo-500">TOTAL: {msg.metadata.timings.total}s</div>
                            </div>
                          </div>
                        )}

                        {msg.metadata.tools_used && msg.metadata.tools_used.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {msg.metadata.tools_used.map((tool: string, i: number) => (
                              <span key={i} className="flex items-center gap-1 px-2 py-1 bg-indigo-500/10 text-indigo-500 rounded-md text-[10px] font-bold">
                                <Search className="w-3 h-3" /> {tool}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center animate-pulse">
                    <Bot className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="flex-1 max-w-[400px]">
                    <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5 rounded-3xl rounded-tl-none shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <div className="w-4 h-4 bg-indigo-500 rounded-full animate-ping absolute"></div>
                          <div className="w-4 h-4 bg-indigo-500 rounded-full relative"></div>
                        </div>
                        <span className="text-sm font-medium text-gray-500 italic">{status}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Dock */}
        <div className="p-6 md:p-10 max-w-4xl mx-auto w-full">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-1000 group-hover:duration-200"></div>
            <div className="relative flex items-center bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden shadow-xl">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder="Message your RAG Agent..."
                className="flex-1 px-6 py-5 bg-transparent focus:outline-none text-gray-900 dark:text-white"
                disabled={loading}
              />
              <div className="px-4 flex items-center gap-2">
                <button
                  onClick={sendMessage}
                  disabled={loading || !input.trim()}
                  className="p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-indigo-500/20"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4 flex justify-center gap-6 text-[11px] font-bold text-gray-400 uppercase tracking-widest">
            <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> Real-time Stream</span>
            <span className="flex items-center gap-1.5"><Search className="w-3.5 h-3.5" /> Agentic Flow Enabled</span>
            <span className="flex items-center gap-1.5 text-indigo-500"><CheckCircle2 className="w-3.5 h-3.5" /> Metal GPU (M3 Max)</span>
          </div>
        </div>
      </div>

      <style jsx global>{`
        .gradient-text {
          background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
      `}</style>
    </div>
  )
}
