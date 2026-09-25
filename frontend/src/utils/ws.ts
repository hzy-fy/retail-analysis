/** 带自动重连的 WebSocket 封装 */
export class ReconnectWebSocket {
  private url: string
  private ws: WebSocket | null = null
  private closed = false
  private retry = 0
  onMessage: (data: any) => void = () => {}
  onStatusChange: (connected: boolean) => void = () => {}

  constructor(url: string) {
    this.url = url
  }

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const full = this.url.startsWith('ws') ? this.url : `${proto}://${location.host}${this.url}`
    this.ws = new WebSocket(full)
    this.ws.onopen = () => {
      this.retry = 0
      this.onStatusChange(true)
    }
    this.ws.onmessage = (e) => {
      try {
        this.onMessage(JSON.parse(e.data))
      } catch { /* ignore */ }
    }
    this.ws.onclose = () => {
      this.onStatusChange(false)
      if (!this.closed) {
        const delay = Math.min(1000 * 2 ** this.retry++, 10000)
        setTimeout(() => !this.closed && this.connect(), delay)
      }
    }
    this.ws.onerror = () => this.ws?.close()
  }

  close() {
    this.closed = true
    this.ws?.close()
  }
}
