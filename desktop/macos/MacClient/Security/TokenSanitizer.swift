import Foundation

/// Token sanitization utility for JWT tokens
/// Removes newlines, whitespace, and URL encoding issues that cause WebSocket handshake failures
enum TokenSanitizer {
    
    /// Sanitizes a raw JWT token by removing all whitespace and newlines
    /// This fixes issues where copy-paste introduces %0A (newline) characters
    /// that cause -1011 WebSocket handshake failures
    ///
    /// - Parameter raw: Raw token string (may contain whitespace/newlines)
    /// - Returns: Clean single-line token
    static func sanitize(_ raw: String) -> String {
        // Remove all whitespace, newlines, and tabs
        let cleaned = raw.components(separatedBy: .whitespacesAndNewlines).joined()
        
        // Additional cleanup for URL-encoded characters that might sneak in
        let urlDecoded = cleaned.removingPercentEncoding ?? cleaned
        
        return urlDecoded.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    /// Masks a token for safe logging (shows only last 6 characters)
    /// - Parameter token: Full JWT token
    /// - Returns: Masked token like "***abc123"
    static func maskForLogging(_ token: String) -> String {
        guard token.count > 6 else { return "***" }
        let suffix = String(token.suffix(6))
        return "***\(suffix)"
    }
    
    /// Validates basic JWT structure (3 parts separated by dots)
    /// - Parameter token: JWT token to validate
    /// - Returns: true if token has valid JWT structure
    static func hasValidJWTStructure(_ token: String) -> Bool {
        let parts = token.components(separatedBy: ".")
        return parts.count == 3 && parts.allSatisfy { !$0.isEmpty }
    }
}
