# Business Intelligence MCP Server

 **AI-Powered Business Intelligence Assistant** with Elasticsearch and Claude integration via Model Context Protocol (MCP)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.15+-green.svg)](https://elastic.co)
[![MCP](https://img.shields.io/badge/MCP-2025--06--18-purple.svg)](https://modelcontextprotocol.io)
[![Claude](https://img.shields.io/badge/Claude-Sonnet%204-orange.svg)](https://anthropic.com)

##  Overview

This project provides an intelligent business data analysis system that combines:

- **Advanced Search**: Keyword, semantic (ELSER), dense vector embeddings, and hybrid search
- **Analytics**: Real-time aggregations and business metrics
- **AI Integration**: Claude-powered Q&A and insights via MCP
- **Web Interface**: User-friendly dashboard for data exploration
- **Claude Desktop**: Direct AI assistant integration through MCP protocol

### Architecture Options

```
Direct Mode:          Browser → Flask → Elasticsearch
MCP Mode:             Browser → Flask → MCP Server → Elasticsearch  
Claude Desktop:       Claude Desktop → MCP Server → Elasticsearch
```
## Architecture

### Components

<img width="915" height="511" alt="Screenshot 2025-08-01 at 7 50 08 AM" src="https://github.com/user-attachments/assets/53c63beb-01af-4898-a7a5-500147526e1d" />

### Data Flow

1. **User Query** → Web interface or Claude Desktop
2. **Processing** → Flask app or MCP server handles request
3. **Search/Analysis** → Elasticsearch with ML inference
4. **AI Enhancement** → Claude provides insights (optional)
5. **Response** → Formatted results returned to user

##  Prerequisites

### 1. Elasticsearch Cloud Setup

You need an **Elasticsearch Cloud deployment** (version 8.15+) with the following models and inference endpoints configured:

#### Required ML Models
- **ELSER v2** (`.elser_model_2_linux-x86_64`) - Sparse vector semantic search
- **E5 Multilingual Small** (`.multilingual-e5-small_linux-x86_64`) - Dense vector embeddings  
- **Rerank v1** (`.rerank-v1`) - Search result reranking
- **Language Identification** (`lang_ident_model_1`) - Built-in model

#### Required Inference Endpoints
```json
{
  "endpoints": [
    {
      "inference_id": ".elser-2-elasticsearch",
      "task_type": "sparse_embedding", 
      "service": "elasticsearch",
      "service_settings": {
        "model_id": ".elser_model_2_linux-x86_64",
        "adaptive_allocations": { "enabled": true, "min_number_of_allocations": 0, "max_number_of_allocations": 32 }
      }
    },
    {
      "inference_id": ".multilingual-e5-small-elasticsearch",
      "task_type": "text_embedding",
      "service": "elasticsearch", 
      "service_settings": {
        "model_id": ".multilingual-e5-small_linux-x86_64",
        "adaptive_allocations": { "enabled": true, "min_number_of_allocations": 0, "max_number_of_allocations": 32 }
      }
    },
    {
      "inference_id": ".rerank-v1-elasticsearch",
      "task_type": "rerank",
      "service": "elasticsearch",
      "service_settings": {
        "model_id": ".rerank-v1",
        "adaptive_allocations": { "enabled": true, "min_number_of_allocations": 0, "max_number_of_allocations": 32 }
      }
    },
    {
      "inference_id": "claude-completions",
      "task_type": "completion", 
      "service": "anthropic",
      "service_settings": {
        "model_id": "claude-sonnet-4-20250514",
        "rate_limit": { "requests_per_minute": 50 }
      }
    }
  ]
}
```

#### Index Mapping
Your Elasticsearch index must have this mapping structure:

```json
{
  "business_intelligence": {
    "mappings": {
      "properties": {
        "date": { "type": "date" },
        "sales_rep": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
        "region": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
        "product_name": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
        "product_category": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
        "sales_amount": { "type": "double" },
        "revenue": { "type": "double" },
        "order_count": { "type": "integer" },
        "customer_count": { "type": "integer" },
        "description": { "type": "text" },
        "notes": { "type": "text" },
        "ml": {
          "properties": {
            "inference": {
              "properties": {
                "description_elser": { "type": "sparse_vector" },
                "description_embedding": { 
                  "type": "dense_vector", "dims": 384, "index": true, "similarity": "cosine"
                },
                "model_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } }
              }
            }
          }
        }
      }
    }
  }
}
```

### 2. Python Environment

- **Python 3.8+**
- **Virtual environment** (recommended)

### 3. Claude API Access

- **Anthropic API key** for Claude Sonnet 4
- **Configured in Elasticsearch** as an inference endpoint

### 4. Demo Data (Essential)

- **Run `python complete_setup_data.py`** after configuration
- **Generates 500+ realistic business records** spanning 2023-2024
- **Includes comprehensive AI inference processing** for semantic search capabilities
- ** Required for meaningful demo experience**
- **Fallback option**: Use `--skip-inference` if ML models unavailable

##  Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/business-intelligence-mcp.git
cd business-intelligence-mcp
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```env
# Elasticsearch Cloud Configuration
ELASTICSEARCH_ENDPOINT=https://your-deployment.es.region.aws.elastic-cloud.com
ELASTICSEARCH_API_KEY="your-api-key-here"

# Alternative: Username/Password Authentication
# ELASTICSEARCH_USERNAME=elastic
# ELASTICSEARCH_PASSWORD=your-password

# Index Configuration
ELASTICSEARCH_INDEX=business_intelligence

# Inference Endpoint IDs
ELSER_INFERENCE_ID=.elser-2-elasticsearch
EMBEDDING_INFERENCE_ID=.multilingual-e5-small-elasticsearch
RERANK_INFERENCE_ID=.rerank-v1-elasticsearch
COMPLETION_INFERENCE_ID=claude-completions

# Web Server Configuration
PORT=5000
NODE_ENV=development

# Optional: Logging
LOG_LEVEL=INFO
```

### 5. Setup Demo Data

** IMPORTANT**: You need sample data to demo the system effectively.

#### Automated Setup (Recommended)

```bash
python complete_setup_data.py
```

This will:
-  Test Elasticsearch connection
-  Create the index with comprehensive field mappings
-  Generate 500 realistic business records (2023-2024)  
-  Index sample data with proper structure
-  Add AI inference processing (ELSER + E5 embeddings)
-  Verify all search capabilities
-  Test keyword, semantic, and aggregation features

#### What Sample Data is Generated

The setup creates realistic business data including:

| Field | Sample Values |
|-------|---------------|
| **Regions** | North America, Europe, Asia Pacific, Latin America, Middle East & Africa |
| **Products** | Enterprise Software, Cloud Services, Professional Services, Hardware, Training, Support |
| **Sales Reps** | Alice Johnson, Bob Smith, Carol Davis, David Wilson, Eva Martinez, Frank Chen, Grace Kim, Henry Lopez |
| **Date Range** | January 2023 - December 2024 (500 records) |
| **Metrics** | Sales amounts ($1K-$300K), Revenue, Order counts, Customer counts |
| **AI Features** | ELSER sparse vectors, E5 dense embeddings for semantic search |

#### Setup Options

```bash
# Full setup with AI inference (recommended)
python complete_setup_data.py

# Basic setup without AI inference (if ML models not available)
python complete_setup_data.py --skip-inference

# Add data to existing index (don't reset)
python complete_setup_data.py --no-reset

# View all options
python complete_setup_data.py --help
```

#### If ML Models Aren't Available

If you don't have ELSER or E5 models deployed, use:

```bash
python complete_setup_data.py --skip-inference
```

This provides:
-  All basic functionality (keyword search, analytics)
-  Complete demo data for meaningful exploration  
-  No semantic search (ELSER/E5 features disabled)

### 6. Verify Complete Setup

```bash
python start.py
```

Select option **4** (Test Connection) to verify your Elasticsearch setup and data.

##  Quick Start

### Essential Steps for Demo

1. **Complete the Installation** (sections 1-4 above)
2. **⚠ CRITICAL: Run Data Setup** - `python complete_setup_data.py`
3. **Launch the Application** - `python start.py` → Choose option 1 or 2
4. **Open Browser** - http://localhost:5000
5. **Try Sample Queries**:
   - *"Show me enterprise software sales"*
   - *"Top regions by revenue"*  
   - *"Professional services in Asia Pacific"*

##  Usage

### Option 1: Interactive Startup Menu

```bash
python start.py
```

Choose from:
1. **Direct Mode** - Simple web app with direct Elasticsearch access
2. **MCP Mode** - Web app + MCP server for AI integration  
3. **Setup & Configuration** - Configuration helper
4. **Test Connection** - Verify Elasticsearch connectivity
5. **Help & Documentation** - Detailed help

### Option 2: Direct Launch

#### Web Interface (Direct Mode)
```bash
python webapp.py
```
- **URL**: http://localhost:5000
- **Features**: All search types, analytics, Claude Q&A
- **Architecture**: Browser → Flask → Elasticsearch

#### MCP-Powered Mode
```bash
python webapp_mcp.py
```
- **URL**: http://localhost:5000  
- **Features**: Full MCP integration, enhanced AI capabilities
- **Architecture**: Browser → Flask → MCP Server → Elasticsearch

#### Standalone MCP Server
```bash
python mcp_server.py
```
- **Protocol**: JSON-RPC over stdin/stdout
- **Usage**: For Claude Desktop or other MCP clients

## Claude Desktop Integration

### 1. Configure Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "business-intelligence": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/your/project/mcp_server.py"],
      "cwd": "/path/to/your/project/"
    }
  }
}
```

### 2. Enhanced MCP Server Features

The MCP server now includes **full AI search capabilities**:

| Search Type | Description | Requires |
|-------------|-------------|----------|
| **Keyword** | Traditional text matching | Always available |
| **Semantic (ELSER)** | AI-powered concept understanding | ELSER model deployed |
| **Embedding (E5)** | Dense vector similarity search | E5 model deployed |  
| **Hybrid** | Combines keyword + semantic | Both ELSER + E5 models |
| **Rerank** | AI-powered result reranking | Rerank model deployed |

The server automatically detects which AI capabilities are available and adjusts accordingly.

### 3. Example Claude Queries

Once connected, you can ask Claude:

**Basic Business Questions:**
- *"What are our top 5 regions by sales revenue?"*
- *"Show me Q4 performance trends by product category"*
- *"Which sales rep has the highest customer conversion rate?"*

**Semantic Search (if ELSER available):**
- *"Find profitable enterprise solutions"* (understands concepts, not just keywords)
- *"Show me underperforming product lines"* (semantic understanding)
- *"Identify growth opportunities in emerging markets"* (conceptual matching)

**Advanced Analytics:**
- *"Analyze our enterprise software performance vs hardware sales"*
- *"Compare regional performance and suggest expansion strategies"*
- *"Find all deals over $50K in the last quarter with growth potential"*

### 4. Check AI Capabilities

You can ask Claude: *"What AI search capabilities are available?"* to see which features are active.

## Features

### Advanced Search Types

| Search Type | Description | Use Case |
|-------------|-------------|-----------|
| **Keyword** | Traditional text matching | Exact product names, regions |
| **Semantic (ELSER)** | AI-powered concept understanding | "profitable products", "underperforming regions" |
| **Dense Vector (E5)** | Multilingual similarity search | Cross-language queries, fuzzy matching |
| **Hybrid** | Combines keyword + semantic | Best of both approaches |
| **Rerank** | AI-powered result reranking | Improved relevance scoring |

### Business Analytics

- **Sales by Region** - Geographic performance analysis
- **Revenue by Category** - Product line profitability  
- **Orders by Sales Rep** - Individual performance metrics
- **Time-filtered Reports** - Last month, quarter, YTD analysis
- **Custom Aggregations** - Flexible metric combinations

### AI-Powered Features

- **Claude Q&A** - Natural language queries about your data
- **Smart Search** - Intelligent query interpretation and analysis
- **Contextual Insights** - AI-generated business recommendations
- **Automated Reporting** - AI-summarized performance metrics

## API Endpoints

### Web API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Advanced search with multiple types |
| `/api/aggregate` | POST | Business metric aggregations |
| `/api/claude-qa` | POST | AI-powered Q&A with context |
| `/api/smart-search` | POST | Intelligent search + analysis |
| `/api/health` | GET | System health and configuration |
| `/api/mcp-tools` | GET | List available MCP tools |

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_business_data` | **Enhanced search** with keyword, semantic (ELSER), embedding (E5), hybrid, and rerank options |
| `aggregate_business_metrics` | Perform business data aggregations with time filtering |
| `get_business_summary` | Comprehensive business overview with AI capability info |
| `get_ai_capabilities` | **New**: Check available AI search features and inference endpoints |

## Sample Data Structure

The following data structure is automatically generated by `python setup_data.py`:

```json
{
  "date": "2024-12-29T00:00:00",
  "sales_rep": "Eva Martinez", 
  "region": "Asia Pacific",
  "product_name": "Professional Services",
  "product_category": "Services",
  "sales_amount": 150857.65,
  "revenue": 128229,
  "order_count": 9,
  "customer_count": 5,
  "description": "Professional Services sale in Asia Pacific handled by Eva Martinez...",
  "notes": "Q4 2024 performance. Strong Asia Pacific market presence.",
  "ml": {
    "inference": {
      "description_elser": { "professional": 1.69, "services": 1.14, "asia": 1.37, "..." },
      "description_embedding": [0.028, -0.027, -0.068, "...384 dimensions"],
      "model_id": [".elser-2-elasticsearch", ".multilingual-e5-small-elasticsearch"]
    }
  }
}
```

**Generated by setup script**: 500 records across 10 product types, 5 regions, 8 sales reps, spanning 2023-2024, with comprehensive AI inference processing.


## 📁 Project Structure

### Key Files

| File | Purpose |
|------|---------|
| `complete_setup_data.py` | **Complete data setup** - Creates index, generates sample data, adds AI inference |
| `start.py` | **Interactive launcher** - Choose between different run modes |
| `webapp.py` | **Direct mode** - Flask app with direct Elasticsearch access |
| `webapp_mcp.py` | **MCP mode** - Flask app + MCP server integration |
| `mcp_server.py` | **Enhanced MCP server** - Full AI search capabilities for Claude Desktop |
| `requirements.txt` | **Dependencies** - Python package requirements |
| `.env` | **⚙Configuration** - Environment variables and settings |
| `templates/index.html` | **Web interface** - Modern Tailwind CSS dashboard |

### Recommended Workflow

1. **Setup**: `python complete_setup_data.py` (creates comprehensive demo data)
2. **Launch**: `python start.py` (interactive menu)
3. **Demo**: Open http://localhost:5000 and explore
4. **Claude Integration**: Configure enhanced MCP server for full AI assistant access

### Enhanced MCP Server

The `mcp_server.py` now includes:
-  **Auto-detection** of available AI models (ELSER, E5, Rerank)
-  **Graceful fallbacks** when AI models aren't available
-  **Full search types** (keyword, semantic, embedding, hybrid, rerank)
-  **AI capability reporting** for debugging and optimization


## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

