# Self LLM Web Interface

Modern, responsive web interface for the Self LLM RAG-enhanced system, built with Next.js 14, React, and Tailwind CSS.

## 🌟 Features

- ✨ **Modern UI/UX** - Beautiful, responsive design with gradient themes
- 💬 **Real-time Chat** - Interactive chat interface with streaming support
- 🔄 **RAG-Enhanced Responses** - Automatic retrieval-augmented generation
- 🌐 **Bilingual Support** - English and Traditional Chinese
- 📊 **Response Metadata** - Display tools used, articles found, and timing
- 🎨 **Markdown Rendering** - Rich text formatting with syntax highlighting
- 📝 **Chat History** - Persistent conversation history per user
- 🔍 **Knowledge Base** - Browse and search stored articles
- ⚙️ **Adjustable Parameters** - Customize max tokens, temperature, and timeout
- 👤 **User Authentication** - Simple username-based login system
- 🧠 **Agentic Reasoning** - Shows reasoning steps and tools used
- 📚 **Article Citations** - Links to source articles used in responses

## 📋 Prerequisites

- **Node.js** 18+ and npm
- **FastAPI Backend** running on `http://localhost:8000` (see main README)
- **RabbitMQ** service running (configured in docker-compose)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd web
npm install
```

### 2. Configure Environment Variables

Create a `.env.local` file in the `web/` directory:

```env
# API Server Configuration
API_SERVER_URL=http://localhost:8000
```

**⚠️ Security Note**: For production, use environment variables and never commit `.env.local` to Git.

### 3. Run Development Server

```bash
npm run dev
```

The application will be available at **http://localhost:3000**

### 4. Build for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## 📁 Project Structure

```
web/
├── app/
│   ├── api/
│   │   └── chat/
│   │       └── route.ts          # API route handler (proxies to FastAPI)
│   ├── knowledge/
│   │   └── page.tsx              # Knowledge base browser
│   ├── globals.css               # Global styles and Tailwind
│   ├── layout.tsx                # Root layout component
│   └── page.tsx                  # Main chat interface
├── next.config.js                # Next.js configuration
├── tailwind.config.js            # Tailwind CSS configuration
├── tsconfig.json                 # TypeScript configuration
├── package.json                  # Dependencies and scripts
└── README.md                     # This file
```

## 🏗️ Architecture

### Frontend Stack
- **Next.js 14** - React framework with App Router
- **React 18** - UI library with hooks
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client for API calls
- **React Markdown** - Markdown rendering
- **Lucide React** - Icon library

### Backend Integration
- **FastAPI Server** (`api_server.py`) - Main backend API
- **RabbitMQ** - Message queue for LLM requests
- **RAG System** - Article retrieval and enhancement

### Data Flow

```
User Input → Next.js API Route → FastAPI Server → RabbitMQ → Worker → LLM
                                                                    ↓
User Interface ← Next.js Frontend ← FastAPI Response ← RabbitMQ ← Response
```

## 🎨 UI Components

### Main Chat Interface (`app/page.tsx`)
- **Chat Messages** - User and assistant messages with markdown rendering
- **Input Field** - Text input with send button
- **Settings Panel** - Adjustable parameters (tokens, temperature, timeout)
- **History Sidebar** - Conversation history with search
- **User Profile** - Login/logout functionality
- **Metadata Display** - Tools used, articles found, response time

### Knowledge Base (`app/knowledge/page.tsx`)
- **Article Browser** - Browse all stored articles
- **Search Functionality** - Search articles by title/content
- **Article Details** - View full article with metadata
- **Filtering** - Filter by category, date, source

### API Route (`app/api/chat/route.ts`)
- **Request Proxy** - Forwards requests to FastAPI backend
- **Error Handling** - Graceful error responses
- **Timeout Management** - 180-second timeout for long requests

## 📡 API Integration

### Chat Endpoint

**POST** `/api/chat`

The Next.js API route (`app/api/chat/route.ts`) proxies requests to the FastAPI backend.

Request:
```json
{
  "prompt": "What are the latest news about Hong Kong?",
  "max_tokens": 500,
  "temperature": 0.7,
  "timeout": 120,
  "history": []
}
```

Response:
```json
{
  "request_id": "uuid",
  "response": "Generated response with markdown...",
  "status": "success",
  "rag_used": true,
  "articles_found": 3,
  "tools_used": ["RAG_fast", "template_report"],
  "response_time": 2.5
}
```

**Note**: The FastAPI backend supports both `/api/chat` (non-streaming) and `/api/chat/stream` (streaming) endpoints. The Next.js route currently uses the non-streaming endpoint for simplicity.

## 🎯 Usage Guide

### Starting a Conversation

1. **Login** (optional) - Enter a username or use as guest
2. **Type your question** - Enter in English or Traditional Chinese
3. **Adjust settings** (optional) - Modify max tokens, temperature if needed
4. **Send** - Click send button or press Enter
5. **View response** - Response appears with markdown formatting

### Viewing History

1. Click the **History** icon in the sidebar
2. Browse past conversations
3. Click on any history item to view full conversation
4. Use **Delete** to remove unwanted history items

### Browsing Knowledge Base

1. Click **Knowledge Base** link in navigation
2. Browse articles or use search
3. Click on any article to view details
4. Filter by category, date, or source

### Adjusting Parameters

- **Max Tokens**: Maximum length of response (50-2000)
- **Temperature**: Creativity/randomness (0.0-2.0)
  - Lower (0.1-0.3): More focused, deterministic
  - Higher (0.7-1.0): More creative, varied
- **Timeout**: Maximum wait time in seconds (30-300)

## 🐛 Troubleshooting

### Common Issues

#### 1. "API server error" or Connection Refused

**Problem**: Cannot connect to FastAPI backend

**Solution**:
- Ensure `api_server.py` is running on port 8000
- Check `API_SERVER_URL` in `.env.local`
- Verify backend is accessible: `curl http://localhost:8000/health`

#### 2. "CORS Error"

**Problem**: Cross-origin request blocked

**Solution**:
- Ensure FastAPI CORS is configured (should be in `api_server.py`)
- Check that both frontend and backend are on same origin or CORS is enabled

#### 3. Slow Response Times

**Problem**: Responses take too long

**Solution**:
- Check RabbitMQ and worker status
- Verify Ollama/OpenRouter is running
- Reduce `max_tokens` in settings
- Check network connection

#### 4. Build Errors

**Problem**: `npm run build` fails

**Solution**:
- Clear `.next` directory: `rm -rf .next`
- Clear node_modules: `rm -rf node_modules && npm install`
- Check TypeScript errors: `npm run lint`

#### 5. Styling Issues

**Problem**: Styles not loading correctly

**Solution**:
- Ensure Tailwind is properly configured
- Check `globals.css` is imported in `layout.tsx`
- Verify PostCSS configuration

## 🔒 Security Considerations

### Environment Variables
- Never commit `.env.local` to Git
- Use strong passwords for production
- Rotate API keys regularly

### API Security
- The frontend proxies requests to FastAPI
- Authentication is handled by the backend
- Rate limiting is enforced by the backend

### Production Deployment
- Use HTTPS in production
- Set secure environment variables
- Enable Next.js security headers
- Use a reverse proxy (nginx) for production

## 🚀 Deployment

### Vercel (Recommended)

1. Import project in Vercel
2. Set environment variables in Vercel dashboard
3. Deploy

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Manual Deployment

```bash
# Build
npm run build

# Start production server
npm start

# Or use PM2
pm2 start npm --name "self-llm-web" -- start
```

## 📦 Dependencies

### Production Dependencies
- `next` - Next.js framework
- `react` & `react-dom` - React library
- `axios` - HTTP client
- `react-markdown` - Markdown renderer
- `react-syntax-highlighter` - Code syntax highlighting
- `lucide-react` - Icon library
- `uuid` - UUID generation

### Development Dependencies
- `typescript` - TypeScript compiler
- `tailwindcss` - CSS framework
- `eslint` - Linting
- `@types/*` - TypeScript type definitions

## 🧪 Development

### Running in Development Mode

```bash
npm run dev
```

### Linting

```bash
npm run lint
```

### Type Checking

```bash
npx tsc --noEmit
```

### Building

```bash
npm run build
```

## 📚 Additional Resources

- **Main Project README**: `../README.md`
- **Installation Guide**: `../INSTALLATION.md`
- **API Documentation**: See FastAPI docs at `http://localhost:8000/docs`
- **Next.js Docs**: https://nextjs.org/docs
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **React Docs**: https://react.dev

## 🤝 Contributing

When contributing to the web interface:

1. Follow TypeScript best practices
2. Use Tailwind for styling (avoid custom CSS)
3. Maintain responsive design
4. Test on multiple browsers
5. Update this README if adding features

## 📝 License

MIT (same as main project)

## 🆘 Support

For issues or questions:
1. Check the main project README: `../README.md`
2. Review troubleshooting section above
3. Check FastAPI server logs
4. Review RabbitMQ and worker logs

---

**Built with ❤️ using Next.js 14 and React**
