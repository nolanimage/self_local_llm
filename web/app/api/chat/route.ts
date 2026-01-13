import { NextRequest, NextResponse } from 'next/server'

// API server URL (FastAPI backend)
const API_SERVER_URL = process.env.API_SERVER_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Forward request to FastAPI backend with extended timeout
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 180000); // 180 seconds

    const response = await fetch(`${API_SERVER_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal
    })
    clearTimeout(id);

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { error: error.detail || 'API server error' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('API error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
