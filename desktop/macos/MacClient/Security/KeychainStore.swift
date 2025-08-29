import Foundation
import Security

/// Keychain utility for secure JWT token storage
enum KeychainStore {
    
    /// Save JWT token to Keychain
    static func saveJWT(_ token: String) {
        let account = "jwtToken"
        let service = "com.yourcompany.macclient"
        let data = token.data(using: .utf8)!

        // Delete existing item first
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)

        // Add new item
        let add: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data
        ]
        let status = SecItemAdd(add as CFDictionary, nil)
        
        if status == errSecSuccess {
            print("[Keychain] ✅ JWT token saved successfully")
        } else {
            print("[Keychain] ❌ Failed to save JWT token: \(status)")
        }
    }

    /// Load JWT token from Keychain
    static func loadJWT() -> String {
        let account = "jwtToken"
        let service = "com.yourcompany.macclient"
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: kCFBooleanTrue!,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var out: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &out)
        
        if status == errSecSuccess,
           let data = out as? Data,
           let str = String(data: data, encoding: .utf8) {
            print("[Keychain] ✅ JWT token loaded successfully")
            return str
        } else {
            print("[Keychain] ⚠️ No JWT token found in Keychain")
            return ""
        }
    }
    
    /// Delete JWT token from Keychain
    static func deleteJWT() {
        let account = "jwtToken"
        let service = "com.yourcompany.macclient"
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        
        let status = SecItemDelete(query as CFDictionary)
        if status == errSecSuccess {
            print("[Keychain] ✅ JWT token deleted successfully")
        } else {
            print("[Keychain] ⚠️ JWT token not found or failed to delete: \(status)")
        }
    }
}
