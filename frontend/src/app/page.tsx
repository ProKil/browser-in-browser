'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function WebSocketScreenshotDisplay() {
  const [events, setEvents] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [, setError] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const [serverUrl, setServerUrl] = useState('https://sotopia-lab--bib-backend-modalapp-serve.modal.run')
  const wsRef = useRef<WebSocket | null>(null)
  const interactionAreaRef = useRef<HTMLDivElement>(null)

  const addEvent = useCallback((eventData: string) => {
    setEvents(prevEvents => [eventData, ...prevEvents.slice(0, 19)])
  }, [])

  const handleGoto = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch(`${serverUrl}/goto`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      })
      if (!response.ok) {
        throw new Error('Failed to navigate')
      }
      addEvent(`Navigated to: ${url}`)
    } catch (error) {
      console.error(`Error navigating: ${error}`)
    }
  }, [url, serverUrl, addEvent])

  const handleNavigation = useCallback(async (direction: 'back' | 'forward') => {
    try {
      const response = await fetch(`${serverUrl}/${direction}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      if (!response.ok) {
        throw new Error(`Failed to navigate ${direction}`)
      }
      addEvent(`Navigated ${direction}`)
    } catch (error) {
      console.error(`Error navigating ${direction}: ${error}`)
    }
  }, [addEvent])

  useEffect(() => {
    const connectWebSocket = () => {
      // wsRef.current = new WebSocket('ws://localhost:8000/screenshot')
      wsRef.current = new WebSocket(`${serverUrl.replace("http", "ws")}/screenshot`)

      wsRef.current.onopen = () => {
        setIsConnected(true)
        setError(null)
        addEvent('Connected to WebSocket')
      }

      wsRef.current.onmessage = (event) => {
        try {
          const blob = event.data as Blob
          const reader = new FileReader()
          reader.onload = () => {
            setImageUrl(reader.result as string)
          }
          reader.readAsDataURL(blob)
        } catch (err) {
          console.error('Error reading blob data:', err)
        }
      }

      wsRef.current.onerror = (event) => {
        setError('WebSocket error occurred')
        addEvent(`WebSocket error: ${event.type}`)
      }

      wsRef.current.onclose = () => {
        setIsConnected(false)
        addEvent('WebSocket connection closed')
      }
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [addEvent, serverUrl])

  useEffect(() => {
    const interactionArea = interactionAreaRef.current
    if (!interactionArea) return

    const handleMouseMove = (e: MouseEvent) => {
      const rect = interactionArea.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      fetch(`${serverUrl}/hover`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ x , y })
      })
      addEvent(`Mouse move: (${x.toFixed(2)}, ${y.toFixed(2)})`)
    }

    const handleClick = (e: MouseEvent) => {
      const rect = interactionArea.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      fetch(`${serverUrl}/click`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ x , y })
      })
      addEvent(`Click: (${x.toFixed(2)}, ${y.toFixed(2)})`)
    }

    const handleWheel = (e: WheelEvent) => {
      // Prevent default scrolling behavior
      e.preventDefault()
      
      // deltaX is horizontal scroll, deltaY is vertical scroll
      // deltaMode indicates the unit (0: pixels, 1: lines, 2: pages)
      const rect = interactionArea.getBoundingClientRect()
      const deltaX = e.deltaX / rect.width
      const deltaY = e.deltaY / rect.height
      
      addEvent(`Wheel delta: (${deltaX}, ${deltaY})`)
      fetch(`${serverUrl}/scroll`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ dx: deltaX, dy: deltaY })
      })
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      addEvent(`Key down: ${e.key}`)
      fetch(`${serverUrl}/keyboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ key: e.key })
      })
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      addEvent(`Key up: ${e.key}`)
    }

    // Make sure the interaction area can receive focus
    interactionArea.setAttribute('tabindex', '0')

    interactionArea.addEventListener('mousemove', handleMouseMove)
    interactionArea.addEventListener('click', handleClick)
    interactionArea.addEventListener('wheel', handleWheel, { passive: false })
    interactionArea.addEventListener('keydown', handleKeyDown)
    interactionArea.addEventListener('keyup', handleKeyUp)

    return () => {
      interactionArea.removeEventListener('mousemove', handleMouseMove)
      interactionArea.removeEventListener('click', handleClick)
      interactionArea.removeEventListener('wheel', handleWheel)
      interactionArea.removeEventListener('keydown', handleKeyDown)
      interactionArea.removeEventListener('keyup', handleKeyUp)
    }
  }, [addEvent, serverUrl])


  return (
    <div className="w-full h-full">
      <div className="flex flex-col gap-4">
        <div className="p-4">
          <div className="flex gap-2 -mb-8">
            <Input
              type="url"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="Enter URL"
              required
              className="flex-grow"
            />
            <span className={`font-semibold ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        <form onSubmit={handleGoto} className="p-4 mb-4">
          <div className="flex gap-2">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => handleNavigation('back')}
              title="Go back"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => handleNavigation('forward')}
              title="Go forward"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter URL"
              required
              className="flex-grow"
            />
            <Button type="submit">Go</Button>
          </div>
        </form>
        <div className="grid-cols-8 grid gap-4">
          <div 
            className="col-span-7 h-full bg-white p-4 rounded shadow outline-none focus:ring-2 focus:ring-blue-500"
            tabIndex={0}
            role="region"
            aria-label="Interaction area for mouse and keyboard events"
          >
            <div 
              ref={interactionAreaRef} 
              className="inline-block" // Changed to inline-block to wrap content exactly
            >
              {imageUrl ? (
                <img 
                  src={imageUrl} 
                  alt="Latest screenshot" 
                  className="max-w-full max-h-[calc(100vh-200px)] object-contain" // Allow image to determine its natural size
                />
              ) : (
                <div className="w-full h-64 bg-gray-200 flex items-center justify-center">
                  <p>No screenshot available yet</p>
                </div>
              )}
            </div>
          </div>
          <div className="col-span-1 bg-white p-4 rounded shadow flex-1">
            <h2 className="text-xl font-semibold mb-2">Events:</h2>
            <ul className="space-y-1 max-h-96 overflow-y-auto" aria-live="polite">
              {events.map((event, index) => (
                <li key={index} className="text-sm">{event}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}