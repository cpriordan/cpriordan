#!/usr/bin/env python3
"""
Serena MCP Management Script for Fintests Project

This script provides utilities for managing the Serena MCP server integration,
including configuration validation, server status checks, and maintenance tasks.
"""

import os
import sys
import json
import yaml
import subprocess
import argparse
from pathlib import Path

# Add project to path for potential access
sys.path.append('/home/ubuntu/projects/fintests')

class SerenaManager:
    def __init__(self):
        self.project_root = Path('/home/ubuntu/projects/fintests')
        self.serena_config = self.project_root / 'serena_config.yml'
        self.project_config = self.project_root / '.serena' / 'project.yml'
        self.mcp_config = self.project_root / '.claude' / 'mcp_config.json'
        
    def check_installation(self):
        """Check if Serena and dependencies are properly installed."""
        print("🔍 Checking Serena MCP installation...")
        
        # Check uv installation
        try:
            result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
            print(f"✅ uv installed: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ uv not found. Please install uv first.")
            return False
            
        # Check if Serena can be accessed
        try:
            result = subprocess.run([
                'uvx', '--from', 'git+https://github.com/oraios/serena', 
                'serena', '--help'
            ], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Serena MCP server accessible")
            else:
                print("❌ Serena MCP server not accessible")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Error accessing Serena MCP server")
            return False
            
        return True
        
    def validate_config(self):
        """Validate Serena configuration files."""
        print("🔍 Validating configuration files...")
        
        configs_valid = True
        
        # Check main config
        if self.serena_config.exists():
            try:
                with open(self.serena_config, 'r') as f:
                    yaml.safe_load(f)
                print("✅ serena_config.yml is valid")
            except yaml.YAMLError as e:
                print(f"❌ serena_config.yml has YAML errors: {e}")
                configs_valid = False
        else:
            print("❌ serena_config.yml not found")
            configs_valid = False
            
        # Check project config
        if self.project_config.exists():
            try:
                with open(self.project_config, 'r') as f:
                    yaml.safe_load(f)
                print("✅ .serena/project.yml is valid")
            except yaml.YAMLError as e:
                print(f"❌ .serena/project.yml has YAML errors: {e}")
                configs_valid = False
        else:
            print("❌ .serena/project.yml not found")
            configs_valid = False
            
        # Check MCP config
        if self.mcp_config.exists():
            try:
                with open(self.mcp_config, 'r') as f:
                    json.load(f)
                print("✅ .claude/mcp_config.json is valid")
            except json.JSONDecodeError as e:
                print(f"❌ .claude/mcp_config.json has JSON errors: {e}")
                configs_valid = False
        else:
            print("⚠️  .claude/mcp_config.json not found (optional)")
            
        return configs_valid
        
    def check_dependencies(self):
        """Check language server dependencies."""
        print("🔍 Checking language server dependencies...")
        
        # Check Python language server
        try:
            result = subprocess.run(['pylsp', '--help'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Python Language Server (pylsp) available")
            else:
                print("❌ Python Language Server (pylsp) not working properly")
        except FileNotFoundError:
            print("⚠️  Python Language Server (pylsp) not found")
            print("   Install with: pip install python-lsp-server")
            
        # Check test dependencies
        print("\n🔍 Checking test framework dependencies...")
        
        # Check pytest
        try:
            result = subprocess.run(['pytest', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ pytest installed: {result.stdout.strip()}")
        except FileNotFoundError:
            print("⚠️  pytest not found")
            print("   Install with: pip install pytest pytest-asyncio")
            
        # Check playwright
        try:
            result = subprocess.run(['playwright', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Playwright installed: {result.stdout.strip()}")
        except FileNotFoundError:
            print("⚠️  Playwright not found")
            print("   Install with: pip install playwright && playwright install --with-deps")
            
    def show_project_info(self):
        """Display information about the current project setup."""
        print("📋 Fintests Project Information for Serena MCP")
        print("=" * 50)
        
        print(f"Project Root: {self.project_root}")
        print(f"Framework: Playwright + pytest")
        print(f"Test Directories:")
        print(f"  • fin-tests/PROD/ - Production tests")
        print(f"  • fin-tests/QA/ - QA environment tests")
        print(f"  • pytests/ADMINSITETESTS/ - Admin portal tests")
        
        print("\n🎯 Key Test Categories for Serena Analysis:")
        key_areas = [
            "Tag Validation (Finalytics JS/CSS tags)",
            "JavaScript Error Detection",
            "Ad Content Validation (Hero, Card ads)",
            "OCR Visual Validation",
            "2FA Admin Authentication",
            "Campaign Management Tests",
            "CI/CD GitHub Actions Workflows"
        ]
        
        for area in key_areas:
            print(f"  • {area}")
            
        print("\n🔒 Protected Files (excluded from Serena access):")
        protected_files = [
            ".env (environment variables)",
            "**/*credentials*",
            "**/*secret*",
            "**/*password*"
        ]
        
        for file in protected_files:
            print(f"  • {file}")
            
        print("\n📝 Test Naming Convention:")
        print("  • UI Tests: test_[client]_[feature]_[environment]_[details].py")
        print("  • Admin Tests: test_findata_[env]_[account]_[feature].py")
            
    def start_server(self, transport='stdio'):
        """Start the Serena MCP server."""
        print(f"🚀 Starting Serena MCP server with {transport} transport...")
        
        # Ensure we're in the project directory
        os.chdir(self.project_root)
        
        try:
            if transport == 'stdio':
                # For stdio, we typically let the client (Claude Code) start the server
                print("For stdio transport, the server will be started by Claude Code.")
                print("Make sure your Claude Code configuration includes the Serena MCP server.")
            elif transport == 'sse':
                # For SSE, we start the server ourselves
                subprocess.run([
                    'uvx', '--from', 'git+https://github.com/oraios/serena',
                    'serena', 'start-mcp-server', '--transport', 'sse', '--port', '8002'
                ])
            else:
                print(f"❌ Unknown transport type: {transport}")
                
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            
    def run_diagnostics(self):
        """Run comprehensive diagnostics."""
        print("🔍 Running Serena MCP Diagnostics for Fintests Project")
        print("=" * 60)
        
        all_good = True
        
        # Check installation
        if not self.check_installation():
            all_good = False
            
        print()
        
        # Validate configuration
        if not self.validate_config():
            all_good = False
            
        print()
        
        # Check dependencies
        self.check_dependencies()
        
        print()
        
        if all_good:
            print("✅ All checks passed! Serena MCP is ready to use.")
        else:
            print("⚠️  Some issues found. Please address them before using Serena MCP.")
            
        return all_good

def main():
    parser = argparse.ArgumentParser(description='Manage Serena MCP for Fintests Project')
    parser.add_argument('command', choices=[
        'check', 'validate', 'info', 'start', 'diagnostics'
    ], help='Command to execute')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio',
                       help='Transport type for server (default: stdio)')
    
    args = parser.parse_args()
    
    manager = SerenaManager()
    
    if args.command == 'check':
        manager.check_installation()
    elif args.command == 'validate':
        manager.validate_config()
    elif args.command == 'info':
        manager.show_project_info()
    elif args.command == 'start':
        manager.start_server(args.transport)
    elif args.command == 'diagnostics':
        manager.run_diagnostics()

if __name__ == '__main__':
    main()