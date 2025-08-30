#!/usr/bin/env python3
"""
Repository Audit Tool
Detects multiple Redis definitions, handshake misuse, and env drift.
"""

import os
import re
import glob
from pathlib import Path
from typing import List, Tuple, Dict

class RepoAuditor:
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.findings: List[Tuple[str, str, str]] = []  # (path, match, hint)
        
    def scan_redis_definitions(self):
        """Scan for Redis URL definitions and configurations."""
        print("🔍 Scanning for Redis definitions...")
        
        # Scan for redis:// URLs in project files only
        project_files = self._find_files_with_extensions(['.py', '.env', '.env.example', '.md', '.sh', '.yml', '.yaml'])
        
        for file_path in project_files:
            # Skip if it's in ignored directories
            path_str = str(file_path)
            if any(ignore in path_str for ignore in ['venv', 'node_modules', '__pycache__', '.git']):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for redis:// URLs (only meaningful ones)
                redis_urls = re.findall(r'redis://[^\s\'"]*', content)
                for url in redis_urls:
                    # Skip documentation examples and tool references
                    if not any(skip in url for skip in ['example', 'localhost:6379', '[[', '`']):
                        self.findings.append((
                            str(file_path.relative_to(self.repo_root)),
                            f"redis URL: {url[:30]}{'...' if len(url) > 30 else ''}",
                            "Check for password consistency"
                        ))
                    
                # Look for REDIS_URL definitions
                redis_url_defs = re.findall(r'REDIS_URL\s*[=:]\s*[^\n]*', content)
                for definition in redis_url_defs:
                    self.findings.append((
                        str(file_path.relative_to(self.repo_root)),
                        f"REDIS_URL def: {definition.strip()[:30]}{'...' if len(definition.strip()) > 30 else ''}",
                        "Verify env consistency"
                    ))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
    def scan_docker_redis_services(self):
        """Scan for Redis services in Docker Compose files."""
        print("🐳 Scanning for Docker Redis services...")
        
        docker_files = list(self.repo_root.glob("**/docker-compose*.yml")) + \
                      list(self.repo_root.glob("**/docker-compose*.yaml"))
        
        for file_path in docker_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for redis service definitions
                if re.search(r'^\s*redis:\s*$', content, re.MULTILINE):
                    # Extract redis service block
                    redis_match = re.search(r'^\s*redis:\s*\n((?:\s+.*\n)*)', content, re.MULTILINE)
                    if redis_match:
                        redis_config = redis_match.group(1)
                        
                        # Check for password configuration
                        if 'requirepass' in redis_config or 'REDIS_PASSWORD' in redis_config:
                            hint = "Password-protected Redis found"
                        else:
                            hint = "Passwordless Redis service"
                            
                        self.findings.append((
                            str(file_path.relative_to(self.repo_root)),
                            "Redis service definition",
                            hint
                        ))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
    def scan_redis_server_scripts(self):
        """Scan for shell scripts starting redis-server."""
        print("📜 Scanning for Redis server scripts...")
        
        shell_files = list(self.repo_root.glob("**/*.sh"))
        
        for file_path in shell_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for redis-server commands
                redis_server_matches = re.findall(r'redis-server[^\n]*', content)
                for match in redis_server_matches:
                    hint = "Password required" if "--requirepass" in match else "No password"
                    self.findings.append((
                        str(file_path.relative_to(self.repo_root)),
                        f"redis-server: {match.strip()}",
                        hint
                    ))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
    def scan_finalize_in_device_code(self):
        """Scan for 'finalize' type in device change code paths."""
        print("🔄 Scanning for finalize in device change code...")
        
        code_files = self._find_files_with_extensions(['.swift', '.py', '.js', '.ts'])
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    # Look for "type":"finalize" in device-related contexts
                    if '"type":"finalize"' in line or "'type':'finalize'" in line:
                        # Check surrounding context for device/pause keywords
                        context_start = max(0, i-5)
                        context_end = min(len(lines), i+5)
                        context = ''.join(lines[context_start:context_end]).lower()
                        
                        if any(keyword in context for keyword in ['device', 'pause', 'restart', 'coordinator']):
                            self.findings.append((
                                str(file_path.relative_to(self.repo_root)),
                                f"Line {i}: finalize in device context",
                                "Check if finalize should be handshake"
                            ))
                            
            except (UnicodeDecodeError, PermissionError):
                continue
                
    def scan_websocket_handshake_issues(self):
        """Scan for WebSocket handshake vs isReady guard issues."""
        print("🔌 Scanning for WebSocket handshake issues...")
        
        code_files = self._find_files_with_extensions(['.swift', '.py', '.js', '.ts'])
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for handshake-related patterns
                handshake_patterns = [
                    (r'STEP 4.*Reading handshake', "Backend handshake handler"),
                    (r'handshake.*validation.*error', "Handshake validation issue"),
                    (r'isReady.*guard', "isReady guard pattern"),
                    (r'canSend.*guard', "canSend guard pattern"),
                    (r'state.*connecting.*connected', "Connection state management")
                ]
                
                for pattern, description in handshake_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        self.findings.append((
                            str(file_path.relative_to(self.repo_root)),
                            f"Line {line_num}: {description}",
                            "Review handshake flow"
                        ))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
    def scan_env_drift(self):
        """Scan for environment configuration drift."""
        print("⚙️ Scanning for environment drift...")
        
        env_files = list(self.repo_root.glob("**/.env*"))
        env_configs = {}
        
        for file_path in env_files:
            if file_path.name.startswith('.env'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Extract key-value pairs
                    config = {}
                    for line in content.split('\n'):
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
                            
                    env_configs[str(file_path.relative_to(self.repo_root))] = config
                    
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # Compare configurations
        if len(env_configs) > 1:
            redis_keys = ['REDIS_URL', 'REDIS_PASSWORD', 'REDIS_REQUIRED']
            
            for key in redis_keys:
                values = {}
                for file_path, config in env_configs.items():
                    if key in config:
                        values[file_path] = config[key]
                        
                if len(set(values.values())) > 1:  # Different values found
                    self.findings.append((
                        "env_drift",
                        f"{key} differs across env files",
                        f"Values: {values}"
                    ))
                    
    def _find_files_with_extensions(self, extensions: List[str]) -> List[Path]:
        """Find all files with given extensions, excluding common ignore patterns."""
        files = []
        ignore_patterns = [
            '**/venv/**', '**/.venv/**', '**/node_modules/**', 
            '**/__pycache__/**', '**/.git/**', '**/build/**',
            '**/dist/**', '**/*.egg-info/**'
        ]
        
        for ext in extensions:
            for file_path in self.repo_root.glob(f"**/*{ext}"):
                # Check if file should be ignored
                should_ignore = any(
                    file_path.match(pattern) for pattern in ignore_patterns
                )
                if not should_ignore:
                    files.append(file_path)
        return files
        
    def print_findings(self):
        """Print findings in a concise table format."""
        if not self.findings:
            print("✅ No issues found!")
            return
            
        print(f"\n📋 Audit Results ({len(self.findings)} findings):")
        print("=" * 80)
        print(f"{'Path':<40} {'Match':<25} {'Hint':<15}")
        print("-" * 80)
        
        # Group findings by category
        categories = {
            'Redis Config': [],
            'Docker': [],
            'Scripts': [],
            'WebSocket': [],
            'Device Code': [],
            'Env Drift': []
        }
        
        for path, match, hint in self.findings:
            if 'redis' in match.lower() and 'docker' not in path:
                categories['Redis Config'].append((path, match, hint))
            elif 'docker-compose' in path:
                categories['Docker'].append((path, match, hint))
            elif path.endswith('.sh'):
                categories['Scripts'].append((path, match, hint))
            elif 'websocket' in match.lower() or 'handshake' in match.lower():
                categories['WebSocket'].append((path, match, hint))
            elif 'finalize' in match.lower() or 'device' in match.lower():
                categories['Device Code'].append((path, match, hint))
            elif 'env_drift' in path:
                categories['Env Drift'].append((path, match, hint))
            else:
                categories['Redis Config'].append((path, match, hint))
        
        for category, findings in categories.items():
            if findings:
                print(f"\n🔍 {category}:")
                for path, match, hint in findings:
                    print(f"  {path:<38} {match[:23]:<25} {hint[:13]}")
                    
    def run_audit(self):
        """Run complete audit."""
        print("🚀 Starting repository audit...")
        print(f"📁 Scanning: {self.repo_root.absolute()}")
        
        self.scan_redis_definitions()
        self.scan_docker_redis_services()
        self.scan_redis_server_scripts()
        self.scan_finalize_in_device_code()
        self.scan_websocket_handshake_issues()
        self.scan_env_drift()
        
        self.print_findings()
        
        # Summary
        redis_findings = len([f for f in self.findings if 'redis' in f[1].lower()])
        ws_findings = len([f for f in self.findings if 'handshake' in f[1].lower() or 'websocket' in f[1].lower()])
        
        print(f"\n📊 Summary:")
        print(f"  Redis-related issues: {redis_findings}")
        print(f"  WebSocket/Handshake issues: {ws_findings}")
        print(f"  Total findings: {len(self.findings)}")
        
        if redis_findings > 3:
            print("⚠️  Multiple Redis configurations detected - check for conflicts")
        if ws_findings > 0:
            print("⚠️  WebSocket handshake issues detected - review connection flow")

def main():
    auditor = RepoAuditor()
    auditor.run_audit()

if __name__ == "__main__":
    main()
