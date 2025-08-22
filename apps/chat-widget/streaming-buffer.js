/**
 * Progressive Streaming Buffer
 * 
 * This class takes text that arrives all at once and progressively
 * reveals it character-by-character to simulate real-time streaming.
 * This solves the issue where n8n sends all chunks within microseconds.
 */
class StreamingBuffer {
    constructor(options = {}) {
        // Configuration
        this.charsPerInterval = options.charsPerInterval || 1;  // Characters to reveal per interval
        this.intervalMs = options.intervalMs || 30;  // Milliseconds between reveals
        this.wordBoundary = options.wordBoundary || false;  // Reveal at word boundaries
        
        // State
        this.buffer = '';
        this.position = 0;
        this.isStreaming = false;
        this.onChunk = null;
        this.onComplete = null;
        this.intervalId = null;
    }
    
    /**
     * Add text to the buffer and start streaming if not already streaming
     */
    addText(text) {
        this.buffer += text;
        
        if (!this.isStreaming) {
            this.startStreaming();
        }
    }
    
    /**
     * Start the progressive reveal of buffered text
     */
    startStreaming() {
        if (this.isStreaming || this.position >= this.buffer.length) {
            return;
        }
        
        this.isStreaming = true;
        
        this.intervalId = setInterval(() => {
            if (this.position >= this.buffer.length) {
                this.stopStreaming();
                return;
            }
            
            // Calculate how many characters to reveal
            let charsToReveal = this.charsPerInterval;
            let endPosition = Math.min(this.position + charsToReveal, this.buffer.length);
            
            // If word boundary mode, extend to next space or punctuation
            if (this.wordBoundary && endPosition < this.buffer.length) {
                const nextSpace = this.buffer.indexOf(' ', endPosition);
                const nextPunct = this.findNextPunctuation(endPosition);
                
                if (nextSpace !== -1 || nextPunct !== -1) {
                    if (nextSpace === -1) endPosition = nextPunct + 1;
                    else if (nextPunct === -1) endPosition = nextSpace + 1;
                    else endPosition = Math.min(nextSpace, nextPunct) + 1;
                    
                    // Don't jump too far ahead
                    endPosition = Math.min(endPosition, this.position + charsToReveal * 10);
                }
            }
            
            // Extract the chunk
            const chunk = this.buffer.substring(this.position, endPosition);
            this.position = endPosition;
            
            // Emit the chunk
            if (this.onChunk && chunk) {
                this.onChunk(chunk);
            }
            
            // Check if complete
            if (this.position >= this.buffer.length) {
                this.stopStreaming();
            }
        }, this.intervalMs);
    }
    
    /**
     * Stop streaming and cleanup
     */
    stopStreaming() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        
        this.isStreaming = false;
        
        if (this.onComplete && this.position >= this.buffer.length) {
            this.onComplete();
        }
    }
    
    /**
     * Find next punctuation mark position
     */
    findNextPunctuation(startPos) {
        const punctuation = ['.', '!', '?', ',', ';', ':', '\n'];
        let nearestPos = -1;
        
        for (const punct of punctuation) {
            const pos = this.buffer.indexOf(punct, startPos);
            if (pos !== -1 && (nearestPos === -1 || pos < nearestPos)) {
                nearestPos = pos;
            }
        }
        
        return nearestPos;
    }
    
    /**
     * Reset the buffer
     */
    reset() {
        this.stopStreaming();
        this.buffer = '';
        this.position = 0;
    }
    
    /**
     * Get remaining text that hasn't been revealed yet
     */
    getRemaining() {
        return this.buffer.substring(this.position);
    }
    
    /**
     * Force complete - reveal all remaining text immediately
     */
    forceComplete() {
        if (this.position < this.buffer.length) {
            const remaining = this.getRemaining();
            this.position = this.buffer.length;
            
            if (this.onChunk && remaining) {
                this.onChunk(remaining);
            }
        }
        
        this.stopStreaming();
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreamingBuffer;
}