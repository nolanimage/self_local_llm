"""
Worker with RAG integration - enhances LLM responses with relevant RSS articles
Implements 2026 Advanced Agentic Patterns: Reflection Loop, Query Rewriting, Multi-Query
NEW: Fast Query Classifier, Multi-Query Retrieval
"""
import os
import json
import logging
import time
import pika
import requests
import re
from datetime import datetime
from typing import List
from app.worker_ollama import LLMWorker, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, OLLAMA_URL, OLLAMA_MODEL, REQUEST_QUEUE, RESPONSE_QUEUE
from app.rag_system import RAGSystem
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

# NEW: Try to load fast classifier (optional)
USE_FAST_CLASSIFIER = False
try:
    from transformers import pipeline
    fast_classifier = None  # Will be initialized lazily
    USE_FAST_CLASSIFIER = True
    logger.info("✓ Transformers available for fast classification")
except ImportError:
    logger.info("Transformers not available - using LLM-based classification")

class RAGWorker(LLMWorker):
    """Extended worker with RAG capabilities, Fast Classifier, and Multi-Query"""
    
    def __init__(self):
        super().__init__()
        # Initialize RAG system
        self.rag = RAGSystem()
        
        # NEW: Initialize fast classifier (lazy loading to avoid startup delay)
        self.fast_classifier = None
        self.use_fast_classifier = os.getenv('USE_FAST_CLASSIFIER', 'false').lower() == 'true'
        self.use_multi_query = os.getenv('USE_MULTI_QUERY', 'true').lower() == 'true'
        
        logger.info(f"RAG system initialized with model: {self.ollama_model}")
        logger.info(f"Fast classifier: {'Enabled' if self.use_fast_classifier else 'Disabled (use LLM routing)'}")
        logger.info(f"Multi-query: {'Enabled' if self.use_multi_query else 'Disabled'}")
    
    def call_llm_api(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7, force_local: bool = False) -> str:
        """
        Helper method to route LLM calls.
        Use force_local=True for fast 'thinking' stages (Planning, Reflection).
        """
        if self.use_openrouter and not force_local:
            return self.call_openrouter(prompt, max_tokens, temperature)
        else:
            # Short timeout for planning/reflection; longer for final generation to avoid false timeouts
            timeout = 30 if force_local else 120
            return self.call_ollama(prompt, max_tokens, temperature, timeout=timeout)
    
    def classify_query_fast(self, prompt: str) -> str:
        """NEW: Fast query classification using zero-shot classifier (100ms vs 2s)"""
        if not self.use_fast_classifier or not USE_FAST_CLASSIFIER:
            return None
        
        try:
            if self.fast_classifier is None:
                self.fast_classifier = pipeline(
                    "zero-shot-classification", 
                    model="facebook/bart-large-mnli",
                    device=-1
                )
            
            labels = ["news query", "casual greeting", "irrelevant question"]
            result = self.fast_classifier(prompt[:200], labels, multi_label=False)
            top_label = result['labels'][0]
            confidence = result['scores'][0]
            
            if confidence > 0.7:
                if "news" in top_label: return "RAG"
                else: return "NONE"
            return None
        except Exception as e:
            logger.warning(f"Fast classifier failed: {e}")
            return None
    
    def generate_query_variations(self, original_query: str, is_chinese: bool) -> List[str]:
        """NEW: Generate query variations for multi-query retrieval (Always uses fast local model)"""
        try:
            if is_chinese:
                template = load_prompt("query_variations_zh.txt")
                prompt = template.format(original_query=original_query)
            else:
                template = load_prompt("query_variations_en.txt")
                prompt = template.format(original_query=original_query)
            
            # Use force_local=True for fast generation
            variations_text = self.call_llm_api(prompt, max_tokens=60, temperature=0.3, force_local=True)
            variations = [line.strip() for line in variations_text.split('\n') if line.strip() and len(line.strip()) > 5]
            # Clean up potential numbering
            variations = [re.sub(r'^\d+[\.\) ]+', '', v) for v in variations]
            return [original_query] + variations[:2]
        except Exception as e:
            logger.warning(f"Query variation failed: {e}")
            return [original_query]

    def is_greeting_or_casual(self, query: str) -> bool:
        """Fast greeting detection using keywords only - 100% reliable"""
        prompt_lower = query.lower().strip()
        exact_greetings = {
            'hi', 'hello', 'hey', 'yo', 'sup', '你好', '您好', '哈囉', '嗨',
            '早安', '午安', '晚安', 'thank you', 'thanks', '謝謝', '多謝', '再見', 'bye',
            'who are you', 'what can you do', '你是誰', '你能做什麼', '你好嗎', 'how are you'
        }
        if prompt_lower in exact_greetings: return True
        if len(query.strip()) <= 15:
            for word in ['hi', 'hello', '你好', '謝謝', '再見', '哈囉']:
                if word in prompt_lower: return True
        return False
    
    def _extract_zh_terms(self, text: str) -> List[str]:
        """
        Heuristic Chinese term extraction for relevance filtering.
        We use it to prevent vector-topic drift on long/complex queries.
        """
        # Split by common glue words to avoid treating the whole sentence as one term
        s = text
        for glue in ["關於", "关于", "的", "有什麼", "有什么", "進展", "进展", "嗎", "么", "？", "?", "！", "!", "，", ",", "。", ".", "：", ":"]:
            s = s.replace(glue, "|")
        parts = [p.strip() for p in s.split("|") if p.strip()]

        stop = {
            "今天", "目前", "最新", "新聞", "新闻", "請問", "请问", "問題", "问题", "報導", "报道", "事件", "情況", "情况"
        }

        candidates: List[str] = []
        for p in parts:
            if p in stop:
                continue
            if 2 <= len(p) <= 8:
                candidates.append(p)
            # sub-phrases: "內蒙古校服" -> "內蒙古" + "校服"
            if len(p) >= 4:
                candidates.extend([p[:4], p[-4:]])
            if len(p) >= 3:
                candidates.extend([p[:3], p[-3:]])
            if len(p) >= 2:
                candidates.extend([p[:2], p[-2:]])

        # unique, preserve order
        seen = set()
        out: List[str] = []
        for t in candidates:
            t = t.strip()
            if not t or t in stop:
                continue
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out[:8]

    def _extract_fact_table(self, articles: List[dict], is_chinese: bool) -> str:
        """
        Extract a clean fact table from articles (who/what/where/when + source).
        This is the evidence base for constrained analysis.
        """
        def src_name(a: dict) -> str:
            s = (a.get("source") or "").strip()
            if not s:
                return "Source"
            return s.replace("https://", "").replace("http://", "").split("/")[0] if "://" in s else s

        def dt(a: dict) -> str:
            d = (a.get("pub_date") or "").strip()
            return d[:16] if d else "N/A"

        facts = []
        for i, a in enumerate(articles[:3], start=1):
            title = a.get('title', '(no title)')
            date = dt(a)
            source = src_name(a)
            # Extract key content snippet (first 200 chars)
            content_snippet = (a.get('content', '') or '')[:200].strip()
            facts.append(f"[{i}] {date} | {source} | {title}\n    {content_snippet}")
        
        return "\n\n".join(facts) if facts else ("無事實" if is_chinese else "No facts")

    def _generate_constrained_analysis(self, prompt: str, fact_table: str, today_str: str, is_chinese: bool) -> str:
        """
        Generate analysis using ONLY the fact table (no new facts allowed).
        This prevents hallucinations while allowing meaningful interpretation.
        """
        if is_chinese:
            template = load_prompt("analysis_constrained_zh.txt")
        else:
            template = load_prompt("analysis_constrained_en.txt")
        analysis_prompt = template.format(today_str=today_str, fact_table=fact_table, prompt=prompt)
        
        try:
            analysis = self.call_llm_api(analysis_prompt, max_tokens=200, temperature=0.3, force_local=True)
            # Clean up any accidental headers
            analysis = re.sub(r'^###\s*[^\n]+\n*', '', analysis, flags=re.MULTILINE).strip()
            return analysis if analysis else ("基於上述事實，目前資訊有限。" if is_chinese else "Based on the facts above, information is limited.")
        except Exception as e:
            logger.warning(f"Constrained analysis failed: {e}")
            return ("基於上述事實，目前資訊有限。" if is_chinese else "Based on the facts above, information is limited.")

    def _render_structured_report(self, prompt: str, articles: List[dict], today_str: str, is_chinese: bool, conflicts: str = "", intent: str = "brief") -> str:
        """
        Evidence-first report rendering with constrained analysis.
        Step A: Extract clean fact table
        Step B: Generate analysis using ONLY those facts
        """
        top = articles[0] if articles else {}

        def src_name(a: dict) -> str:
            s = (a.get("source") or "").strip()
            if not s:
                return "Source"
            return s.replace("https://", "").replace("http://", "").split("/")[0] if "://" in s else s

        def dt(a: dict) -> str:
            d = (a.get("pub_date") or "").strip()
            return d[:16] if d else "N/A"

        # Step A: Extract fact table
        fact_table = self._extract_fact_table(articles, is_chinese)
        
        # Step B: Generate constrained analysis
        analysis = ""
        if articles:
            analysis = self._generate_constrained_analysis(prompt, fact_table, today_str, is_chinese)
        else:
            analysis = "資料不足，無法提供可信的新聞簡報。" if is_chinese else "Insufficient data for reliable briefing."

        if is_chinese:
            lines = []
            lines.append("### ⚡ 今日快訊")
            if top.get("title"):
                lines.append(f"> {top.get('title')} [{1}]")
            else:
                lines.append(f"> 針對「{prompt}」，目前可用資料不足。")
            lines.append("")
            lines.append("### 🔍 深度分析")
            lines.append(analysis)
            lines.append("")
            lines.append("### 📋 事實清單")
            if not articles:
                lines.append("- **N/A | 系統**: 本次查詢未找到可引用的相關新聞。")
            else:
                for i, a in enumerate(articles[:3], start=1):
                    lines.append(f"- **{dt(a)} | {src_name(a)}**: {a.get('title','(no title)')} [{i}]")
            lines.append("")
            lines.append("### ⚖️ 差異分析")
            if conflicts and conflicts.strip() and conflicts.strip().lower() not in ["none", "無"]:
                lines.append(conflicts.strip())
            else:
                lines.append("無。")
            lines.append("")
            lines.append("### Sources")
            for i, a in enumerate(articles[:3], start=1):
                s = a.get("source") or "N/A"
                lines.append(f"[{i}] {s}")
            return "\n".join(lines).strip()

        # English
        lines = []
        lines.append("### ⚡ News Flash")
        if top.get("title"):
            lines.append(f"> {top.get('title')} [1]")
        else:
            lines.append(f"> Insufficient information for: \"{prompt}\"")
        lines.append("")
        lines.append("### 🔍 Intelligence Briefing")
        lines.append(analysis)
        lines.append("")
        lines.append("### 📋 Key Facts")
        if not articles:
            lines.append("- **N/A | System**: No relevant articles found.")
        else:
            for i, a in enumerate(articles[:3], start=1):
                lines.append(f"- **{dt(a)} | {src_name(a)}**: {a.get('title','(no title)')} [{i}]")
        lines.append("")
        lines.append("### ⚖️ Conflict Analysis")
        lines.append(conflicts.strip() if conflicts else "None.")
        lines.append("")
        lines.append("### Sources")
        for i, a in enumerate(articles[:3], start=1):
            s = a.get("source") or "N/A"
            lines.append(f"[{i}] {s}")
        return "\n".join(lines).strip()

    def process_request(self, ch, method, properties, body):
        """Process request with Reflection Loop and Query Rewriting"""
        try:
            request_data = json.loads(body)
            request_id = request_data.get('request_id', 'unknown')
            prompt = request_data.get('prompt', '')
            history = request_data.get('history', []) # NEW: Get history
            temperature = request_data.get('temperature', 0.7)
            stream_mode = request_data.get('stream_mode', False)
            
            # Format history for prompt
            history_context = ""
            if history:
                history_context = "近期對話上下文：\n"
                for msg in history[-4:]: # Use last 4 turns
                    role = "用戶" if msg['role'] == 'user' else "助理"
                    history_context += f"{role}: {msg['content']}\n"
                history_context += "---\n"

            def is_chinese(text):
                for char in text:
                    if '\u4e00' <= char <= '\u9fff': return True
                return False
            
            is_chinese_query = is_chinese(prompt)
            max_tokens = request_data.get('max_tokens', 300 if is_chinese_query else 250)
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            logger.info(f"--- START REQUEST {request_id} --- ({prompt[:50]})")
            start_request_time = time.time()
            timings = {}
            
            # State
            use_rag = True
            search_query = prompt
            relevant_articles = []
            tools_used = []
            generated_text = ""
            final_prompt = prompt  # Initialize with original prompt
            max_similarity_score = None
            context = ""
            detected_conflicts = ""
            detected_intent = "brief"  # default intent
            needs_clarification = False

            # 0. AMBIGUITY CHECK (before greeting check, for short/ambiguous queries)
            # Check if query is too short/ambiguous and might need clarification
            query_len = len(prompt.strip())
            is_ambiguous = False
            if is_chinese_query:
                # Single word or very short queries (1-3 chars) are ambiguous
                is_ambiguous = query_len <= 3 and not self.is_greeting_or_casual(prompt)
            else:
                # Single word queries in English
                words = prompt.strip().split()
                is_ambiguous = len(words) == 1 and len(words[0]) <= 8 and not self.is_greeting_or_casual(prompt)
            
            # 1. GREETING CHECK
            if self.is_greeting_or_casual(prompt):
                logger.info(f"✋ Greeting detected")
                use_rag = False
                tools_used.append('greeting_filter')
                generated_text = "你好！我是新聞助手。有什麼我可以幫您的嗎？" if is_chinese_query else "Hello! I'm a news assistant. How can I help you today?"

            # 1.5 SIMPLE OUT-OF-SCOPE ROUTER (fast, avoids wasted RAG + hallucinations)
            elif is_chinese_query and any(k in prompt for k in ["天氣", "天气", "氣溫", "温度", "降雨", "颱風", "台风"]):
                use_rag = False
                tools_used.append("router_weather_out_of_scope")
                generated_text = (
                    "### ⚡ 今日快訊\n"
                    "> 我目前的資料庫沒有「天氣/氣象」的即時來源，因此無法回答香港天氣。\n\n"
                    "### 🔍 深度分析\n"
                    "- 建議：新增香港天文台或天氣新聞的 RSS 來源後再查詢。\n\n"
                    "### 📋 事實清單\n"
                    "- **N/A | 系統**: 未收錄氣象來源。\n\n"
                    "### ⚖️ 差異分析\n"
                    "無。\n"
                )
            
            # 2.5 CLARIFYING QUESTION (for ambiguous queries) - CHECK BEFORE FAST CLASSIFIER
            if is_ambiguous and use_rag:
                # Try a quick search first - if we find strong results, proceed
                # Otherwise, ask for clarification
                quick_test = self.rag.search_articles(prompt, top_k=2, use_rerank=True, category=None)
                # Simple lexical check for short queries (same logic as full filter)
                if quick_test and is_chinese_query and len(prompt.strip()) <= 4:
                    variants = {prompt, prompt.replace("馬", "马"), prompt.replace("马", "馬")}
                    def _quick_lex(a):
                        hay = f"{a.get('title','')} {a.get('summary','')} {a.get('content','')}"
                        return any(v and v in hay for v in variants)
                    quick_test = [a for a in quick_test if _quick_lex(a)]
                # Use higher threshold (0.60) to be more conservative
                if quick_test and quick_test[0].get('similarity', 0) >= 0.60:
                    # Strong match found, proceed normally
                    logger.info(f"✓ Ambiguous query '{prompt}' found strong match (score: {quick_test[0].get('similarity', 0):.2f}), proceeding")
                    is_ambiguous = False
                else:
                    # Weak or no match - ask for clarification
                    score = quick_test[0].get('similarity', 0) if quick_test else 0
                    logger.info(f"❓ Ambiguous query '{prompt}' - weak/no match (score: {score:.2f}), asking for clarification")
                    needs_clarification = True
                    use_rag = False
                    tools_used.append("clarify_ambiguous")
                    
                    # Generate clarifying options based on query
                    if is_chinese_query:
                        # Try to infer what the user might mean
                        options = []
                        if any(c in prompt for c in ["港", "香"]):
                            options = ["香港最新新聞", "香港政治", "香港經濟"]
                        elif any(c in prompt for c in ["中", "國"]):
                            options = ["中國政治", "中國經濟", "中國社會"]
                        elif any(c in prompt for c in ["美", "國"]):
                            options = ["美國政治", "美國經濟", "美國科技"]
                        else:
                            # Generic options
                            options = [f"{prompt}最新消息", f"{prompt}相關新聞", f"{prompt}深度分析"]
                        
                        template = load_prompt("clarify_zh.txt")
                        clarifying_text = template.format(
                            prompt=prompt,
                            option1=options[0] if len(options) > 0 else "選項1",
                            option2=options[1] if len(options) > 1 else "選項2",
                            option3=options[2] if len(options) > 2 else "選項3"
                        )
                        generated_text = clarifying_text
                    else:
                        # English clarifying question
                        generated_text = (
                            f"Your query '{prompt}' is quite brief. Could you clarify:\n"
                            f"1. **Latest news about {prompt}**\n"
                            f"2. **Analysis/explanation of {prompt}**\n"
                            f"3. **Compare different sources on {prompt}**\n"
                            f"4. **Other** (please specify)"
                        )

            # 2.6 FAST CLASSIFIER (only if not clarifying)
            if not needs_clarification and self.use_fast_classifier:
                fast_decision = self.classify_query_fast(prompt)
                if fast_decision == "NONE":
                    use_rag = False
                    logger.info("Fast classifier decided: Skip RAG")

            # 3. RAG PIPELINE
            if use_rag and not needs_clarification:
                # New Flow (Budgeted Agent):
                # A) Fast-path retrieval first (no planner)
                # B) Only if weak, run planner + HyDE and retry once
                # C) Reflection only if strong results & multiple sources

                FAST_ACCEPT = float(os.getenv("RAG_FAST_ACCEPT", "0.62"))
                RELEVANCE_THRESHOLD = float(os.getenv("RAG_MIN_RELEVANCE", "0.45"))
                REFLECT_MIN = float(os.getenv("RAG_REFLECT_MIN", "0.60"))

                selected_category = "ALL"
                hyde_summary = ""
                planner_used = False

                def _build_context(arts: List[dict]) -> None:
                    nonlocal context, max_similarity_score, relevant_articles
                    for art in arts:
                        sim = art.get('similarity', 0)
                        if max_similarity_score is None or sim > max_similarity_score:
                            max_similarity_score = sim
                        context += f"【來源】: {art.get('source')} (日期: {art.get('pub_date')})\n"
                        context += f"【分類】: {art.get('category', 'General')} | 【標題】: {art['title']}\n"
                        context += f"【詳細內容】: {art['content'][:600]}\n"
                        context += "-----------------------------------\n"
                    relevant_articles.extend(arts)

                def _filter_articles(arts: List[dict], query_for_lex: str) -> List[dict]:
                    if not arts:
                        return []
                    q = (query_for_lex or "").strip()

                    # Short-query lexical guardrail (prevents Maresca/馬拉松 style drift)
                    if is_chinese_query and len(q) <= 4:
                        variants = {q, q.replace("馬", "马"), q.replace("马", "馬")}
                        def _lex(a):
                            hay = f"{a.get('title','')} {a.get('summary','')} {a.get('content','')}"
                            return any(v and v in hay for v in variants)
                        return [a for a in arts if _lex(a)]

                    if (not is_chinese_query) and len(q) <= 10:
                        ql = q.lower()
                        def _lex_en(a):
                            hay = f"{a.get('title','')} {a.get('summary','')} {a.get('content','')}".lower()
                            return ql in hay
                        return [a for a in arts if _lex_en(a)]

                    # Long Chinese query relevance filter (topic term overlap)
                    if is_chinese_query and len(q) > 4:
                        base_terms = self._extract_zh_terms(prompt)
                        if base_terms:
                            trans = str.maketrans({"內": "内", "國": "国", "臺": "台"})
                            variants = set()
                            for t in base_terms:
                                variants.add(t)
                                variants.add(t.translate(trans))
                                if len(t) >= 3:
                                    variants.add(t[:2])
                                    variants.add(t.translate(trans)[:2])

                            def _topic(a):
                                hay = f"{a.get('title','')} {a.get('summary','')} {a.get('content','')}"
                                return any(v and v in hay for v in variants)

                            filtered = [a for a in arts if _topic(a)]
                            return filtered

                    return arts

                # Step 1: Direct retrieval (fast path)
                search_start = time.time()
                direct_query = prompt
                if is_chinese_query and len(prompt.strip()) > 4:
                    terms = self._extract_zh_terms(prompt)
                    if terms:
                        direct_query = " ".join(terms)
                tools_used.append("RAG_fast")
                arts = self.rag.search_articles(direct_query, top_k=3, use_rerank=True, category=None)
                arts = _filter_articles(arts, prompt)

                if arts:
                    _build_context(arts)

                timings['search_fast'] = round(time.time() - search_start, 2)

                # Decide whether to accept fast path
                if max_similarity_score is not None and max_similarity_score >= FAST_ACCEPT and len(relevant_articles) > 0:
                    tools_used.append("fast_path_accept")
                    # Fast path: infer intent from query (simple heuristic)
                    if any(w in prompt.lower() for w in ["latest", "最新", "update", "更新", "progress", "進展"]):
                        detected_intent = "update"
                    elif any(w in prompt.lower() for w in ["compare", "比較", "difference", "差異", "conflict", "衝突"]):
                        detected_intent = "compare"
                    elif any(w in prompt.lower() for w in ["why", "為什麼", "原因", "impact", "影響", "explain", "解釋"]):
                        detected_intent = "explain"
                    else:
                        detected_intent = "brief"
                else:
                    # Step 2: Planner + HyDE + retry once (only when needed)
                    plan_start = time.time()
                    if is_chinese_query:
                        template = load_prompt("planner_zh.txt")
                        plan_prompt = template.format(today_str=today_str, history_context=history_context, prompt=prompt)
                    else:
                        template = load_prompt("planner_en.txt")
                        plan_prompt = template.format(today_str=today_str, history_context=history_context, prompt=prompt)

                    try:
                        planner_used = True
                        plan_text = self.call_llm_api(plan_prompt, max_tokens=150, temperature=0, force_local=True)
                        tools_used.append("planner")

                        kw_match = re.search(r"KEYWORDS:\s*(.*?)(?:\n|$)", plan_text, re.IGNORECASE)
                        cat_match = re.search(r"CATEGORY:\s*(.*?)(?:\n|$)", plan_text, re.IGNORECASE)
                        hyde_match = re.search(r"HYDE:\s*(.*?)(?:\n|$)", plan_text, re.IGNORECASE)
                        intent_match = re.search(r"INTENT:\s*(.*?)(?:\n|$)", plan_text, re.IGNORECASE)

                        if kw_match:
                            search_query = kw_match.group(1).strip()
                        if cat_match:
                            selected_category = cat_match.group(1).strip().split(',')[0].capitalize()
                        if hyde_match:
                            hyde_summary = hyde_match.group(1).strip()
                        
                        # Extract intent (brief/update/compare/explain)
                        detected_intent = "brief"  # default
                        if intent_match:
                            intent_str = intent_match.group(1).strip().lower()
                            if intent_str in ["brief", "update", "compare", "explain"]:
                                detected_intent = intent_str
                    except Exception as e:
                        logger.warning(f"Planning failed: {e}")
                    timings['planning'] = round(time.time() - plan_start, 2)

                    # Retry retrieval using planner keywords (+ HyDE) with optional multi-query
                    search_retry_start = time.time()
                    cat_filter = None if selected_category.upper() == "ALL" else selected_category
                    retry_query = search_query
                    if hyde_summary:
                        retry_query = f"{search_query} {hyde_summary}"
                        tools_used.append("hyde")

                    arts2: List[dict] = []
                    skip_multi = len((search_query or "").strip()) <= 4
                    if self.use_multi_query and not skip_multi:
                        queries = self.generate_query_variations(search_query, is_chinese_query)
                        if retry_query and retry_query != search_query:
                            queries.insert(0, retry_query)
                        all_articles: List[dict] = []
                        for q in queries[:3]:
                            all_articles.extend(self.rag.search_articles(q, top_k=2, use_rerank=True, category=cat_filter))
                        seen = {}
                        for a in all_articles:
                            if a['id'] not in seen or a['similarity'] > seen[a['id']]['similarity']:
                                seen[a['id']] = a
                        arts2 = sorted(seen.values(), key=lambda x: x['similarity'], reverse=True)[:3]
                    else:
                        arts2 = self.rag.search_articles(retry_query, top_k=3, use_rerank=True, category=cat_filter)

                    arts2 = _filter_articles(arts2, search_query)

                    # Replace fast-path context with retry context if retry found better results
                    if arts2:
                        context = ""
                        relevant_articles = []
                        max_similarity_score = None
                        _build_context(arts2)

                    timings['search_retry'] = round(time.time() - search_retry_start, 2)

                # Optional Reflection (only if strong results + multiple sources)
                if relevant_articles and (max_similarity_score or 0) >= REFLECT_MIN:
                    sources = {a.get("source") for a in relevant_articles if a.get("source")}
                    if len(sources) >= 2:
                        reflect_start = time.time()
                        if is_chinese_query:
                            template = load_prompt("reflection_zh.txt")
                            reflect_prompt = template.format(today_str=today_str, prompt=prompt, context=context)
                        else:
                            template = load_prompt("reflection_en.txt")
                            reflect_prompt = template.format(today_str=today_str, prompt=prompt, context=context)
                        reflect_text = self.call_llm_api(reflect_prompt, max_tokens=150, temperature=0, force_local=True)
                        tools_used.append("reflection")
                        logger.info(f"🧐 Fact-Checker Report: {reflect_text}")
                        timings['reflection'] = round(time.time() - reflect_start, 2)

                        conf_match = re.search(r"CONFLICTS:\s*(.*?)(?:\n|$)", reflect_text, re.IGNORECASE)
                        detected_conflicts = conf_match.group(1).strip() if conf_match else ""
                        if detected_conflicts.lower() not in ["none", "無", ""]:
                            tools_used.append("conflict_detected")

                timings['search'] = round(time.time() - search_start, 2)

                # Step 3: Final Response Instruction (The Reporter with Meta-Analysis)
                if use_rag:
                    # CRITICAL: If the best match is too weak, it's a "No Info" case
                    if not relevant_articles or max_similarity_score < RELEVANCE_THRESHOLD:
                        logger.info(f"🚫 No relevant news for '{prompt}'. Best score: {max_similarity_score}")
                        # WIPE EVERYTHING to prevent hallucination
                        context = ""
                        relevant_articles = []
                        max_similarity_score = 0
                        
                        if is_chinese_query:
                            final_prompt = (
                                f"### ⚡ 今日快訊\n"
                                f"> 資料庫目前沒有關於「{prompt}」的相關報導。\n\n"
                                f"### 🔍 深度分析\n"
                                f"- 可能原因：目前收錄來源尚未覆蓋該主題，或尚未完成下一輪同步。\n"
                                f"- 建議：等待下一輪 RSS 同步（每 10 分鐘一次），或新增/調整 RSS 來源以涵蓋此主題。\n\n"
                                f"### 📋 事實清單\n"
                                f"- **N/A | 系統**: 本次查詢未在資料庫中找到可引用的相關新聞。\n\n"
                                f"### ⚖️ 差異分析\n"
                                f"（無；因為沒有可比對的來源）\n"
                            )
                        else:
                            final_prompt = f"Today is {today_str}. User asked '{prompt}' but no relevant news was found in the database. Politely say you don't have data on this topic yet and suggest waiting for the next RSS sync or adding a relevant RSS source. Do NOT mention unrelated topics."
                    else:
                        # Use deterministic rendering for safety/performance (no hallucinated facts/citations)
                        generated_text = self._render_structured_report(
                            prompt=prompt,
                            articles=relevant_articles[:3],
                            today_str=today_str,
                            is_chinese=is_chinese_query,
                            conflicts=detected_conflicts,
                            intent=detected_intent,
                        )
                        tools_used.append("template_report")
                        final_prompt = None
                
            # 4. GENERATION
            gen_start = time.time()
            if not generated_text:
                if stream_mode and not self.use_openrouter:
                    generated_text = "[STREAMING_READY]"
                else:
                    generated_text = self.call_llm_api(final_prompt if final_prompt else prompt, max_tokens=max_tokens, temperature=temperature)
            
            # Step 4.5: Generate Follow-up Suggestions (Smart Follow-up Engine)
            suggestions = []
            # ONLY generate suggestions if we actually have relevant articles
            if use_rag and relevant_articles and context and generated_text != "[STREAMING_READY]":
                try:
                    template = load_prompt("followup_suggestions.txt")
                    suggest_prompt = template.format(generated_text=generated_text[:300], context=context[:500])
                    
                    suggest_text = self.call_llm_api(suggest_prompt, max_tokens=150, temperature=0.7, force_local=True)
                    logger.info(f"📋 Raw suggest text: {suggest_text}")
                    
                    # Robust parsing for suggestions
                    # Try to find anything that looks like a question or a list item
                    potential_lines = suggest_text.split('\n')
                    for line in potential_lines:
                        line = line.strip()
                        # Match: 1. Q, 1) Q, # Q, 问题1: Q, etc.
                        clean_line = re.sub(r'^(?:### |# |问题\d+[:： ]*|\d+[\.\) ]+)', '', line).strip()
                        if clean_line and (clean_line.endswith('？') or clean_line.endswith('?') or len(clean_line) > 5):
                            if clean_line not in suggestions:
                                suggestions.append(clean_line)
                    
                    suggestions = suggestions[:3]
                    logger.info(f"💡 Parsed suggestions: {suggestions}")
                except Exception as e:
                    logger.warning(f"Failed to generate suggestions: {e}")

            if generated_text != "[STREAMING_READY]":
                timings['generation'] = round(time.time() - gen_start, 2)
            
            timings['total'] = round(time.time() - start_request_time, 2)

            # 5. SEND RESPONSE
            reply_to = properties.reply_to if properties.reply_to else RESPONSE_QUEUE
            response_data = {
                'request_id': request_id,
                'response': generated_text,
                'suggestions': suggestions, # NEW: Add suggestions to response
                'final_prompt': final_prompt if (stream_mode and not self.use_openrouter) else None,
                'model': self.openrouter_model if self.use_openrouter else self.ollama_model,
                'status': 'success',
                'rag_used': use_rag,
                'articles_found': len(relevant_articles),
                'tools_used': tools_used,
                'timings': timings
            }
            
            self.channel.basic_publish(
                exchange='',
                routing_key=reply_to,
                body=json.dumps(response_data),
                properties=pika.BasicProperties(delivery_mode=2, correlation_id=properties.correlation_id)
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"--- COMPLETED {request_id} ---")
            
        except Exception as e:
            logger.error(f"Fatal worker error: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    worker = RAGWorker()
    worker.start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
