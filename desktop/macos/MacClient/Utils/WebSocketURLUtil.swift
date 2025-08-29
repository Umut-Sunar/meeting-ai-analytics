import Foundation

/// WebSocket URL normalization utility for consistent scheme handling
/// 
/// This utility ensures all WebSocket connections use proper ws:// or wss:// schemes
/// and handles HTTP→WS conversion automatically.
/// 
/// References:
/// - Apple URLSessionWebSocketTask: https://developer.apple.com/documentation/foundation/urlsessionwebsockettask
/// - NSURLErrorBadServerResponse: https://developer.apple.com/documentation/foundation/nsurlerrorbadserverresponse
/// - RFC 6455 WebSocket Protocol: https://tools.ietf.org/html/rfc6455
struct WebSocketURLUtil {
    
    enum WSURLError: Error, LocalizedError {
        case invalidURL(String)
        case unsupportedScheme(String)
        case nilComponents
        
        var errorDescription: String? {
            switch self {
            case .invalidURL(let url):
                return "Invalid URL format: \(url)"
            case .unsupportedScheme(let scheme):
                return "Unsupported scheme '\(scheme)'. Only http, https, ws, wss are supported."
            case .nilComponents:
                return "Failed to parse URL components"
            }
        }
    }
    
    /// Normalize URL for WebSocket connections
    /// 
    /// This function converts HTTP schemes to WebSocket schemes:
    /// - http:// → ws://
    /// - https:// → wss://
    /// - ws:// → ws:// (unchanged)
    /// - wss:// → wss:// (unchanged)
    /// 
    /// Any other scheme will throw an error.
    /// 
    /// - Parameters:
    ///   - baseURL: The base URL to normalize
    ///   - path: Optional path to append
    ///   - queryItems: Optional query parameters to add
    /// - Returns: Normalized WebSocket URL
    /// - Throws: WSURLError if URL is invalid or uses unsupported scheme
    static func makeWebSocketURL(
        baseURL: String,
        path: String = "",
        queryItems: [URLQueryItem] = []
    ) throws -> URL {
        
        guard var components = URLComponents(string: baseURL) else {
            throw WSURLError.invalidURL(baseURL)
        }
        
        // Validate and normalize scheme
        guard let scheme = components.scheme?.lowercased() else {
            throw WSURLError.invalidURL("Missing scheme in URL: \(baseURL)")
        }
        
        switch scheme {
        case "http":
            components.scheme = "ws"
            print("[WS] Normalized scheme: http → ws")
        case "https":
            components.scheme = "wss"
            print("[WS] Normalized scheme: https → wss")
        case "ws", "wss":
            // Already WebSocket scheme - no change needed
            break
        default:
            throw WSURLError.unsupportedScheme(scheme)
        }
        
        // Build path properly if provided
        if !path.isEmpty {
            let basePath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            let addPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            components.path = "/" + [basePath, addPath].filter { !$0.isEmpty }.joined(separator: "/")
        }
        
        // Fix localhost IPv6/IPv4 conflicts by forcing IPv4
        if components.host?.lowercased() == "localhost" {
            components.host = "127.0.0.1"
            print("[WS] Normalized host: localhost → 127.0.0.1 (IPv4)")
        }
        
        // Add query items if provided
        if !queryItems.isEmpty {
            components.queryItems = (components.queryItems ?? []) + queryItems
        }
        
        guard let finalURL = components.url else {
            throw WSURLError.nilComponents
        }
        
        print("[WS] Normalized URL: \(finalURL.absoluteString)")
        return finalURL
    }
    
    /// Create WebSocket task with normalized URL
    /// 
    /// This is the SINGLE point for creating WebSocket tasks in the app.
    /// All WebSocket connections MUST use this method.
    /// 
    /// - Parameters:
    ///   - session: URLSession to use
    ///   - baseURL: Base URL (will be normalized)
    ///   - path: Optional path to append
    ///   - queryItems: Optional query parameters
    /// - Returns: Configured URLSessionWebSocketTask
    /// - Throws: WSURLError if URL normalization fails
    static func createWebSocketTask(
        with session: URLSession,
        baseURL: String,
        path: String = "",
        queryItems: [URLQueryItem] = []
    ) throws -> URLSessionWebSocketTask {
        
        let normalizedURL = try makeWebSocketURL(
            baseURL: baseURL,
            path: path,
            queryItems: queryItems
        )
        
        print("[WS] Creating WebSocket task for: \(normalizedURL.absoluteString)")
        return session.webSocketTask(with: normalizedURL)
    }
}

// MARK: - Unit Tests Support
extension WebSocketURLUtil {
    
    /// Comprehensive test suite for URL normalization
    static func runAllTests() {
        print("🧪 Running WebSocket URL normalization tests...")
        
        testSchemeNormalization()
        testHostNormalization()
        testPathHandling()
        testQueryParameters()
        testErrorCases()
        
        print("🎉 All WebSocket URL tests completed!")
    }
    
    private static func testSchemeNormalization() {
        print("  🔧 Testing scheme normalization...")
        
        do {
            // Test http → ws
            let ws1 = try makeWebSocketURL(baseURL: "http://localhost:8000")
            assert(ws1.scheme == "ws", "http should normalize to ws")
            assert(ws1.host == "127.0.0.1", "localhost should normalize to 127.0.0.1")
            
            // Test https → wss
            let ws2 = try makeWebSocketURL(baseURL: "https://api.example.com")
            assert(ws2.scheme == "wss", "https should normalize to wss")
            
            // Test ws unchanged
            let ws3 = try makeWebSocketURL(baseURL: "ws://localhost:8000")
            assert(ws3.scheme == "ws", "ws should remain unchanged")
            
            // Test wss unchanged
            let ws4 = try makeWebSocketURL(baseURL: "wss://secure.example.com")
            assert(ws4.scheme == "wss", "wss should remain unchanged")
            
            print("    ✅ Scheme normalization tests passed")
            
        } catch {
            print("    ❌ Scheme normalization test failed: \(error)")
        }
    }
    
    private static func testHostNormalization() {
        print("  🔧 Testing host normalization...")
        
        do {
            // Test localhost → 127.0.0.1
            let url1 = try makeWebSocketURL(baseURL: "ws://localhost:8000")
            assert(url1.host == "127.0.0.1", "localhost should normalize to 127.0.0.1")
            
            // Test LOCALHOST (case insensitive) → 127.0.0.1
            let url2 = try makeWebSocketURL(baseURL: "ws://LOCALHOST:3000")
            assert(url2.host == "127.0.0.1", "LOCALHOST should normalize to 127.0.0.1")
            
            // Test other hosts unchanged
            let url3 = try makeWebSocketURL(baseURL: "ws://api.example.com")
            assert(url3.host == "api.example.com", "Other hosts should remain unchanged")
            
            print("    ✅ Host normalization tests passed")
            
        } catch {
            print("    ❌ Host normalization test failed: \(error)")
        }
    }
    
    private static func testPathHandling() {
        print("  🔧 Testing path handling...")
        
        do {
            // Test path appending
            let url1 = try makeWebSocketURL(
                baseURL: "ws://localhost:8000",
                path: "/api/v1/ws"
            )
            assert(url1.path == "/api/v1/ws", "Path should be properly appended")
            
            // Test path with base path
            let url2 = try makeWebSocketURL(
                baseURL: "ws://localhost:8000/base",
                path: "/api/ws"
            )
            assert(url2.path == "/base/api/ws", "Paths should be properly combined")
            
            // Test trailing slashes handled
            let url3 = try makeWebSocketURL(
                baseURL: "ws://localhost:8000/",
                path: "/api/"
            )
            assert(url3.path == "/api", "Trailing slashes should be normalized")
            
            print("    ✅ Path handling tests passed")
            
        } catch {
            print("    ❌ Path handling test failed: \(error)")
        }
    }
    
    private static func testQueryParameters() {
        print("  🔧 Testing query parameters...")
        
        do {
            // Test query parameter addition
            let queryItems = [URLQueryItem(name: "token", value: "abc123")]
            let url = try makeWebSocketURL(
                baseURL: "ws://localhost:8000",
                path: "/api/ws",
                queryItems: queryItems
            )
            
            assert(url.query?.contains("token=abc123") == true, "Query parameters should be added")
            
            print("    ✅ Query parameter tests passed")
            
        } catch {
            print("    ❌ Query parameter test failed: \(error)")
        }
    }
    
    private static func testErrorCases() {
        print("  🔧 Testing error cases...")
        
        // Test invalid URL
        do {
            _ = try makeWebSocketURL(baseURL: "not-a-url")
            print("    ❌ Should have thrown error for invalid URL")
        } catch WSURLError.invalidURL {
            print("    ✅ Correctly caught invalid URL error")
        } catch {
            print("    ❌ Wrong error type for invalid URL: \(error)")
        }
        
        // Test unsupported scheme
        do {
            _ = try makeWebSocketURL(baseURL: "ftp://localhost:8000")
            print("    ❌ Should have thrown error for unsupported scheme")
        } catch WSURLError.unsupportedScheme {
            print("    ✅ Correctly caught unsupported scheme error")
        } catch {
            print("    ❌ Wrong error type for unsupported scheme: \(error)")
        }
    }
}
