import Foundation

/// Centralized WebSocket URL builder that ensures proper scheme handling
/// Fixes -1011 handshake failures caused by incorrect http:// schemes
struct WSURLBuilder {
    
    enum Environment {
        case local
        case production
        
        var defaultScheme: String {
            switch self {
            case .local: return "ws"
            case .production: return "wss"
            }
        }
        
        var defaultHost: String {
            switch self {
            case .local: return "127.0.0.1"
            case .production: return "api.example.com"  // Replace with actual prod host
            }
        }
        
        var defaultPort: Int? {
            switch self {
            case .local: return 8000
            case .production: return nil  // Use default port for wss (443)
            }
        }
    }
    
    /// Builds a WebSocket URL with proper scheme validation
    /// - Parameters:
    ///   - environment: Local or production environment
    ///   - host: Override default host (optional)
    ///   - port: Override default port (optional)
    ///   - path: API path (e.g., "/api/v1/ws/ingest/meetings/test-connection")
    ///   - queryItems: Query parameters (excluding token - use header instead)
    /// - Returns: Valid WebSocket URL or nil if construction fails
    static func build(
        environment: Environment,
        host: String? = nil,
        port: Int? = nil,
        path: String,
        queryItems: [URLQueryItem] = []
    ) -> URL? {
        
        var components = URLComponents()
        
        // Force correct WebSocket scheme
        components.scheme = environment.defaultScheme
        
        // Use provided host or environment default
        components.host = host ?? environment.defaultHost
        
        // Use provided port or environment default
        components.port = port ?? environment.defaultPort
        
        // Ensure path starts with /
        components.path = path.hasPrefix("/") ? path : "/\(path)"
        
        // Add query items if provided
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        
        guard let url = components.url else {
            print("[WSURLBuilder] ❌ Failed to construct URL from components: \(components)")
            return nil
        }
        
        // Validate scheme is WebSocket
        guard url.scheme == "ws" || url.scheme == "wss" else {
            print("[WSURLBuilder] ❌ Invalid scheme: \(url.scheme ?? "nil"). Must be ws:// or wss://")
            return nil
        }
        
        print("[WSURLBuilder] ✅ Built WebSocket URL: \(url.absoluteString)")
        return url
    }
    
    /// Convenience method for building local development URLs
    static func buildLocal(
        host: String = "127.0.0.1",
        port: Int = 8000,
        path: String,
        queryItems: [URLQueryItem] = []
    ) -> URL? {
        return build(
            environment: .local,
            host: host,
            port: port,
            path: path,
            queryItems: queryItems
        )
    }
    
    /// Convenience method for building production URLs
    static func buildProduction(
        host: String? = nil,
        path: String,
        queryItems: [URLQueryItem] = []
    ) -> URL? {
        return build(
            environment: .production,
            host: host,
            port: nil,
            path: path,
            queryItems: queryItems
        )
    }
    
    /// Validates if a URL is a proper WebSocket URL
    static func isValidWebSocketURL(_ url: URL) -> Bool {
        return url.scheme == "ws" || url.scheme == "wss"
    }
}
