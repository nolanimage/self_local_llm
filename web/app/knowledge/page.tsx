'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import Link from 'next/link'
import { 
  ArrowLeft, 
  Trash2, 
  Database, 
  Search, 
  X, 
  ExternalLink, 
  Clock, 
  Calendar,
  FileText,
  AlertCircle
} from 'lucide-react'

interface Article {
  id: number
  title: string
  content: string
  summary?: string
  entities?: string
  keywords?: string
  category?: string
  link: string
  pub_date: string
  source: string
  created_at: string
}

export default function KnowledgePage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [relatedArticles, setRelatedArticles] = useState<any[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [loadingRelated, setLoadingRelated] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const articlesPerPage = 20

  useEffect(() => {
    loadArticles()
  }, [])

  const loadArticles = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/rag/articles?limit=${page * articlesPerPage}`)
      const newArticles = response.data.articles || []
      setArticles(newArticles)
      setTotal(response.data.total || 0)
      setHasMore(newArticles.length < response.data.total)
    } catch (error) {
      console.error('Error loading articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadMore = () => {
    setPage(prev => prev + 1)
    setTimeout(() => loadArticles(), 100)
  }

  const handleArticleClick = async (articleId: number) => {
    setLoadingDetail(true)
    setRelatedArticles([])
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/rag/articles/${articleId}`)
      setSelectedArticle(response.data)
      
      // Load related articles
      loadRelated(articleId)
    } catch (error) {
      console.error('Error loading article detail:', error)
      alert('Failed to load article details')
    } finally {
      setLoadingDetail(false)
    }
  }

  const loadRelated = async (articleId: number) => {
    setLoadingRelated(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${apiUrl}/api/rag/articles/${articleId}/related`)
      setRelatedArticles(response.data.related || [])
    } catch (error) {
      console.warn('Error loading related articles:', error)
    } finally {
      setLoadingRelated(false)
    }
  }

  const deleteArticle = async (e: React.MouseEvent, articleId: number) => {
    e.stopPropagation() // Don't trigger the modal
    if (!confirm('Are you sure you want to delete this article?')) return
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await axios.delete(`${apiUrl}/api/rag/articles/${articleId}`)
      setArticles(articles.filter(a => a.id !== articleId))
      setTotal(total - 1)
      if (selectedArticle?.id === articleId) setSelectedArticle(null)
    } catch (error) {
      alert('Failed to delete')
    }
  }

  const filteredArticles = articles.filter(a => 
    a.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
    a.content.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-[#f8f9fa] dark:bg-[#0d1117] text-gray-900 dark:text-gray-100 font-sans">
      
      {/* Header */}
      <div className="bg-white dark:bg-[#161b22] border-b border-gray-200 dark:border-gray-800 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition group">
              <ArrowLeft className="w-6 h-6 group-hover:-translate-x-1 transition-transform" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Database className="text-indigo-500" /> Knowledge Base
              </h1>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-widest mt-0.5">
                {total} Articles Total
              </p>
            </div>
          </div>

          <div className="relative w-96 hidden md:block">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search in knowledge base..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-11 pr-4 py-2.5 bg-gray-50 dark:bg-[#0d1117] border border-gray-200 dark:border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            />
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto p-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-40 gap-4">
            <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-500 font-medium">Loading knowledge base...</p>
          </div>
        ) : filteredArticles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-40 text-gray-400 gap-4">
            <AlertCircle className="w-16 h-16 opacity-20" />
            <p className="text-xl">No articles found matching your search.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredArticles.map((article) => (
              <div 
                key={article.id}
                onClick={() => handleArticleClick(article.id)}
                className="group bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 rounded-2xl p-6 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/5 transition cursor-pointer flex flex-col h-full"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 text-[10px] font-bold uppercase tracking-wider rounded">
                      {article.source}
                    </span>
                    {article.category && (
                      <span className="px-2 py-1 bg-emerald-50 dark:bg-green-900/20 text-emerald-600 dark:text-green-400 text-[10px] font-bold uppercase tracking-wider rounded">
                        {article.category}
                      </span>
                    )}
                  </div>
                  <button 
                    onClick={(e) => deleteArticle(e, article.id)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <h3 className="text-lg font-bold mb-3 group-hover:text-indigo-500 transition line-clamp-2 leading-tight">
                  {article.title}
                </h3>

                {article.entities && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {article.entities.split(',').slice(0, 3).map((entity, i) => (
                      <span key={i} className="text-[9px] text-gray-400 border border-gray-200 dark:border-gray-700 px-1.5 py-0.5 rounded-full">
                        #{entity.trim()}
                      </span>
                    ))}
                  </div>
                )}

                {article.keywords && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {article.keywords.split(',').slice(0, 4).map((kw, i) => (
                      <span key={i} className="text-[9px] text-indigo-400 bg-indigo-500/5 px-1.5 py-0.5 rounded">
                        {kw.trim()}
                      </span>
                    ))}
                  </div>
                )}
                
                <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-3 mb-6 flex-1 leading-relaxed italic">
                  {article.summary || article.content}
                </p>

                <div className="pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[11px] text-gray-400 font-bold uppercase tracking-wide">
                  <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> {article.pub_date ? article.pub_date.slice(0, 10) : 'N/A'}</span>
                  <span className="flex items-center gap-1">Read More <ArrowLeft className="w-3.5 h-3.5 rotate-180" /></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Load More Button */}
        {!loading && hasMore && filteredArticles.length > 0 && (
          <div className="mt-12 flex justify-center">
            <button
              onClick={loadMore}
              className="px-8 py-4 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20 flex items-center gap-2"
            >
              Load More Articles
            </button>
          </div>
        )}
      </main>

      {/* Full Content Modal */}
      {(selectedArticle || loadingDetail) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8 backdrop-blur-md bg-black/40 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-[#161b22] w-full max-w-4xl max-h-full rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            {loadingDetail ? (
              <div className="flex flex-col items-center justify-center py-40 gap-4">
                <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-500 font-medium">Loading content...</p>
              </div>
            ) : selectedArticle ? (
              <>
                <div className="p-6 md:p-8 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-black/20">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center">
                      <FileText className="text-white w-6 h-6" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-indigo-500 uppercase tracking-widest">{selectedArticle.source}</h2>
                      <p className="text-xs text-gray-500 flex items-center gap-1.5 mt-0.5"><Clock className="w-3 h-3" /> {selectedArticle.pub_date || selectedArticle.created_at}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setSelectedArticle(null)}
                    className="p-3 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-8 md:p-12">
                  <h1 className="text-3xl md:text-4xl font-extrabold mb-8 leading-tight">
                    {selectedArticle.title}
                  </h1>

                  {/* Summary Box */}
                  <div className="mb-10 p-6 bg-indigo-50 dark:bg-indigo-900/10 border-l-4 border-indigo-500 rounded-r-2xl">
                    <h4 className="text-xs font-bold text-indigo-500 uppercase tracking-widest mb-3">AI 核心摘要</h4>
                    <p className="text-lg text-gray-700 dark:text-gray-200 leading-relaxed italic">
                      「{selectedArticle.summary || selectedArticle.title}」
                    </p>
                  </div>

                  {/* Entities & Keywords Box */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
                    {selectedArticle.entities && (
                      <div>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                          <Search className="w-3 h-3" /> 識別實體 (Entities)
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {selectedArticle.entities.split(',').map((entity, i) => (
                            <span key={i} className="px-3 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-medium text-gray-600 dark:text-gray-300 shadow-sm">
                              {entity.trim()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedArticle.keywords && (
                      <div>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                          <Database className="w-3 h-3" /> 核心主題 (Keywords)
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {selectedArticle.keywords.split(',').map((kw, i) => (
                            <span key={i} className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 rounded-xl text-xs font-medium text-indigo-600 dark:text-indigo-400 shadow-sm">
                              {kw.trim()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="prose prose-lg dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 leading-relaxed space-y-4">
                    {selectedArticle.content.split('\n').map((para, i) => (
                      <p key={i}>{para}</p>
                    ))}
                  </div>

                  {/* Related Articles / Knowledge Graph / Timeline */}
                  {(relatedArticles.length > 0 || loadingRelated) && (
                    <div className="mt-16 pt-8 border-t border-gray-100 dark:border-gray-800">
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                          <Database className="w-4 h-4 text-indigo-500" /> 相關新聞與時序記錄 (Knowledge Link)
                        </h3>
                        {loadingRelated && <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>}
                      </div>
                      
                      <div className="space-y-4">
                        {relatedArticles.map((rel, i) => (
                          <div 
                            key={i}
                            onClick={() => handleArticleClick(rel.id)}
                            className="group p-4 bg-gray-50 dark:bg-white/5 rounded-2xl hover:bg-white dark:hover:bg-white/10 border border-transparent hover:border-indigo-500/30 transition cursor-pointer"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-bold text-indigo-500 uppercase tracking-wider bg-indigo-50 dark:bg-indigo-900/20 px-1.5 py-0.5 rounded">
                                {rel.reason || 'Related'}
                              </span>
                              <span className="text-[10px] text-gray-400 font-medium">
                                {rel.pub_date ? rel.pub_date.slice(0, 16) : ''}
                              </span>
                            </div>
                            <h4 className="text-sm font-bold group-hover:text-indigo-500 transition line-clamp-1">
                              {rel.title}
                            </h4>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-12 pt-8 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
                    <a 
                      href={selectedArticle.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20"
                    >
                      <ExternalLink className="w-4 h-4" /> View Original Source
                    </a>
                    
                    <button 
                      onClick={(e) => deleteArticle(e, selectedArticle.id)}
                      className="flex items-center gap-2 px-6 py-3 border border-red-100 text-red-500 rounded-xl font-bold hover:bg-red-50 dark:hover:bg-red-500/10 transition"
                    >
                      <Trash2 className="w-4 h-4" /> Delete Article
                    </button>
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      <style jsx global>{`
        .line-clamp-1 { display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
        .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .line-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
      `}</style>
    </div>
  )
}
