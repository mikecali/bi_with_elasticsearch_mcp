#!/usr/bin/env python3
"""
Business Intelligence Assistant Startup Script
Choose between Direct mode or MCP mode
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Print application banner"""
    print("\n" + "="*60)
    print("🧠 Business Intelligence Assistant")
    print("="*60)
    print("Choose your deployment mode:")
    print()

def check_requirements():
    """Check if required files exist"""
    required_files = [
        ('.env', 'Environment configuration'),
        ('webapp.py', 'Direct mode application'),
        ('webapp_mcp.py', 'MCP mode application'),
        ('mcp_server.py', 'MCP server'),
        ('templates/index.html', 'Web interface')
    ]
    
    missing_files = []
    for file_path, description in required_files:
        if not Path(file_path).exists():
            missing_files.append(f"  ❌ {file_path} - {description}")
        else:
            print(f"  ✅ {file_path}")
    
    if missing_files:
        print("\n⚠️  Missing required files:")
        for missing in missing_files:
            print(missing)
        return False
    
    return True

def show_menu():
    """Show startup menu"""
    print("\n📋 Deployment Options:")
    print()
    print("1. 🚀 Direct Mode (Recommended for getting started)")
    print("   - Simple: Browser → Flask → Elasticsearch")
    print("   - Faster startup, easier debugging")
    print("   - Run: webapp.py")
    print()
    print("2. 🤖 MCP Mode (For AI assistant integration)")
    print("   - Advanced: Browser → Flask → MCP Server → Elasticsearch") 
    print("   - Enables Claude Desktop integration")
    print("   - Run: webapp_mcp.py + mcp_server.py")
    print()
    print("3. 🛠️  Setup & Configuration")
    print("   - Run setup script and configuration check")
    print()
    print("4. 🔍 Test Connection")
    print("   - Test Elasticsearch connection")
    print()
    print("5. ❓ Help & Documentation")
    print("   - View available commands and troubleshooting")
    print()

def run_direct_mode():
    """Run the application in direct mode"""
    print("\n🚀 Starting Business Intelligence Assistant (Direct Mode)")
    print("   Architecture: Browser → Flask → Elasticsearch")
    print("   URL: http://localhost:5000")
    print("   Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        subprocess.run([sys.executable, 'webapp.py'])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except FileNotFoundError:
        print("❌ Error: webapp.py not found")

def run_mcp_mode():
    """Run the application in MCP mode"""
    print("\n🤖 Starting Business Intelligence Assistant (MCP Mode)")
    print("   Architecture: Browser → Flask → MCP Server → Elasticsearch")
    print("   URL: http://localhost:5000")
    print("   MCP Server: Running in background")
    print("   Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        subprocess.run([sys.executable, 'webapp_mcp.py'])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except FileNotFoundError:
        print("❌ Error: webapp_mcp.py not found")

def run_setup():
    """Run setup script"""
    print("\n🛠️  Running setup and configuration...")
    
    try:
        subprocess.run([sys.executable, 'setup.py'])
    except FileNotFoundError:
        print("❌ Error: setup.py not found")
        print("💡 Please create the setup script or configure manually")

def test_connection():
    """Test Elasticsearch connection"""
    print("\n🔍 Testing Elasticsearch connection...")
    
    try:
        from dotenv import load_dotenv
        from elasticsearch import Elasticsearch
        
        load_dotenv()
        
        endpoint = os.getenv('ELASTICSEARCH_ENDPOINT')
        if not endpoint:
            print("❌ ELASTICSEARCH_ENDPOINT not configured in .env")
            return
            
        print(f"📡 Connecting to: {endpoint}")
        
        # Configure client
        es_config = {
            "hosts": [endpoint],
            "request_timeout": 10,
            "max_retries": 1
        }
        
        if os.getenv("ELASTICSEARCH_API_KEY"):
            es_config["api_key"] = os.getenv("ELASTICSEARCH_API_KEY").strip('"')
        else:
            es_config["basic_auth"] = (
                os.getenv("ELASTICSEARCH_USERNAME", "elastic"),
                os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
            )
        
        es = Elasticsearch(**es_config)
        
        # Test connection
        info = es.info()
        print(f"✅ Connected to Elasticsearch {info['version']['number']}")
        print(f"📊 Cluster: {info['cluster_name']}")
        
        # Test index
        index_name = os.getenv("ELASTICSEARCH_INDEX", "business_intelligence")
        if es.indices.exists(index=index_name):
            count = es.count(index=index_name)['count']
            print(f"✅ Index '{index_name}' found with {count:,} documents")
        else:
            print(f"⚠️  Index '{index_name}' not found")
            print("💡 You may need to create and populate your index")
        
    except ImportError:
        print("❌ Elasticsearch library not installed")
        print("💡 Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Check your .env configuration")

def show_help():
    """Show help and documentation"""
    print("\n❓ Help & Documentation")
    print("=" * 40)
    print()
    print("📁 Key Files:")
    print("  • webapp.py         - Direct mode application")
    print("  • webapp_mcp.py     - MCP mode application  ")
    print("  • mcp_server.py     - Standalone MCP server")
    print("  • .env              - Environment configuration")
    print("  • templates/        - Web interface files")
    print()
    print("⚙️  Configuration:")
    print("  • Copy .env.example to .env")
    print("  • Set ELASTICSEARCH_ENDPOINT and credentials")
    print("  • Optional: Configure ML inference endpoints")
    print()
    print("🐛 Troubleshooting:")
    print("  • Connection issues: Check .env configuration")
    print("  • Missing files: Run setup.py or check repository")
    print("  • Port conflicts: Change PORT in .env")
    print("  • MCP issues: Ensure mcp_server.py exists")
    print()
    print("📚 More Info:")
    print("  • README.md - Complete documentation")
    print("  • /api/health - Runtime health check")
    print("  • /api/mcp-tools - Available MCP tools")
    print()

def main():
    """Main startup function"""
    print_banner()
    
    # Check requirements
    print("🔍 Checking required files...")
    if not check_requirements():
        print("\n💡 Run option 3 (Setup) to resolve missing files")
    
    while True:
        show_menu()
        
        try:
            choice = input("👉 Select option (1-5, or 'q' to quit): ").strip().lower()
            
            if choice in ['q', 'quit', 'exit']:
                print("\n👋 Goodbye!")
                break
            elif choice == '1':
                run_direct_mode()
            elif choice == '2':
                run_mcp_mode()
            elif choice == '3':
                run_setup()
            elif choice == '4':
                test_connection()
            elif choice == '5':
                show_help()
            else:
                print("\n❌ Invalid choice. Please select 1-5 or 'q' to quit.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        
        # Pause before showing menu again
        input("\n⏸️  Press Enter to continue...")

if __name__ == "__main__":
    main()
