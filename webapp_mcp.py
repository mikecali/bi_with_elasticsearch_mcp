#!/usr/bin/env python3

import asyncio
import json
import os
import logging
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class MCPClient:
    """Client to communicate with the MCP server"""
    
    def __init__(self):
        self.mcp_process = None
        self.start_mcp_server()
        
    def start_mcp_server(self):
        """Start the MCP server as a subprocess"""
        try:
            logger.info("Starting MCP server...")
            
            # Path to the actual MCP server script
            mcp_script = "mcp_server.py"
            
            # Check if the MCP server script exists
            if not os.path.exists(mcp_script):
                raise FileNotFoundError(f"MCP server script not found: {mcp_script}")
            
            # Start MCP server process
            self.mcp_process = subprocess.Popen(
                ['python', mcp_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Test the connection
            test_result = self.call_mcp_tool("tools/list", {})
            if test_result.get("tools"):
                logger.info(f"✅ MCP server started successfully with {len(test_result['tools'])} tools")
            else:
                logger.error("❌ MCP server started but no tools available")
                
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self.mcp_process = None
    
    def call_mcp_tool(self, method, params=None):
        """Call an MCP tool and get the response"""
        if not self.mcp_process:
            raise Exception("MCP server not running")
        
        try:
            # Prepare JSON-RPC request
            request_id = int(time.time() * 1000)  # Use timestamp as ID
            rpc_request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": request_id
            }
            
            # Send request to MCP server
            request_json = json.dumps(rpc_request) + "\n"
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read response
            response_line = self.mcp_process.stdout.readline()
            if not response_line:
                raise Exception("No response from MCP server")
            
            response = json.loads(response_line.strip())
            
            # Check for errors
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"MCP call failed: {e}")
            raise
    
    def search_business_data(self, query, search_type="keyword", size=10):
        """Search business data via MCP"""
        try:
            logger.info(f"MCP Search: '{query}' (type: {search_type}, size: {size})")
            
            result = self.call_mcp_tool("tools/call", {
                "name": "search_business_data",
                "arguments": {
                    "query": query,
                    "search_type": search_type,
                    "size": size
                }
            })
            
            # Parse the content from MCP response
            if "content" in result and result["content"]:
                content_text = result["content"][0]["text"]
                return json.loads(content_text)
            else:
                raise Exception("No content in MCP response")
                
        except Exception as e:
            logger.error(f"MCP search failed: {e}")
            raise
    
    def aggregate_business_metrics(self, metric, group_by, time_range=None):
        """Aggregate business metrics via MCP"""
        try:
            logger.info(f"MCP Aggregation: {metric} by {group_by} for {time_range}")
            
            result = self.call_mcp_tool("tools/call", {
                "name": "aggregate_business_metrics",
                "arguments": {
                    "metric": metric,
                    "group_by": group_by,
                    "time_range": time_range
                }
            })
            
            # Parse the content from MCP response
            if "content" in result and result["content"]:
                content_text = result["content"][0]["text"]
                return json.loads(content_text)
            else:
                raise Exception("No content in MCP response")
                
        except Exception as e:
            logger.error(f"MCP aggregation failed: {e}")
            raise
    
    def get_business_summary(self, time_range=None):
        """Get business summary via MCP"""
        try:
            logger.info(f"MCP Business Summary for {time_range}")
            
            result = self.call_mcp_tool("tools/call", {
                "name": "get_business_summary",
                "arguments": {
                    "time_range": time_range
                }
            })
            
            # Parse the content from MCP response
            if "content" in result and result["content"]:
                content_text = result["content"][0]["text"]
                return json.loads(content_text)
            else:
                raise Exception("No content in MCP response")
                
        except Exception as e:
            logger.error(f"MCP business summary failed: {e}")
            raise
    
    def ask_claude_about_data(self, question, context_data=None):
        """Use Claude inference endpoint to answer questions about business data"""
        try:
            logger.info(f"Asking Claude: '{question}'")
            
            # For now, provide a helpful response based on context
            if not context_data:
                return {
                    "answer": f"To answer '{question}', I would need to search your business data first. Try using the search function to get relevant data, then ask me to analyze it.",
                    "suggestion": "Search for relevant data first, then ask for analysis",
                    "needs_data": True
                }
            else:
                # Analyze the context data
                results = context_data.get('results', [])
                total_hits = context_data.get('total_hits', 0)
                
                # Create a basic analysis
                analysis_points = []
                if results:
                    # Analyze top results
                    top_product = results[0].get('product_name', 'Unknown')
                    top_sales = results[0].get('sales_amount', 0)
                    top_region = results[0].get('region', 'Unknown')
                    
                    analysis_points.append(f"Found {total_hits} relevant records in your business data.")
                    analysis_points.append(f"Top result: '{top_product}' with ${top_sales:,} in sales from {top_region}.")
                    
                    # Look for patterns
                    regions = list(set([r.get('region', 'Unknown') for r in results[:5]]))
                    categories = list(set([r.get('product_category', 'Unknown') for r in results[:5]]))
                    
                    if len(regions) > 1:
                        analysis_points.append(f"Data spans multiple regions: {', '.join(regions[:3])}{'...' if len(regions) > 3 else ''}.")
                    
                    if len(categories) > 1:
                        analysis_points.append(f"Multiple product categories found: {', '.join(categories[:3])}{'...' if len(categories) > 3 else ''}.")
                    
                    # Calculate totals
                    total_sales = sum([r.get('sales_amount', 0) for r in results])
                    total_orders = sum([r.get('order_count', 0) for r in results])
                    
                    if total_sales > 0:
                        analysis_points.append(f"Total sales across these records: ${total_sales:,}.")
                    if total_orders > 0:
                        analysis_points.append(f"Total orders: {total_orders:,}.")
                
                return {
                    "answer": f"Based on your question '{question}', here's what I found in your business data:\n\n" + "\n".join(analysis_points),
                    "data_summary": f"Analyzed {len(results)} of {total_hits} matching records",
                    "needs_data": False
                }
                
        except Exception as e:
            logger.error(f"Claude query failed: {e}")
            raise
    
    def get_health_info(self):
        """Get health information via MCP"""
        try:
            # Call MCP to get some basic info
            tools_result = self.call_mcp_tool("tools/list", {})
            
            return {
                "status": "healthy",
                "mcp_server": "running",
                "available_tools": len(tools_result.get("tools", [])),
                "tools": [tool["name"] for tool in tools_result.get("tools", [])],
                "claude_inference": "simulated",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "mcp_server": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def cleanup(self):
        """Clean up MCP server process"""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=5)
                logger.info("MCP server terminated")
            except:
                self.mcp_process.kill()
                logger.info("MCP server killed")

# Global MCP client
try:
    mcp_client = MCPClient()
    logger.info("MCP client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize MCP client: {e}")
    mcp_client = None

@app.route('/')
def index():
    """Serve the main UI page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_business_data():
    """Handle search requests via MCP"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        query = data.get('query', '')
        search_type = data.get('search_type', 'keyword')
        size = data.get('size', 10)
        
        if not query.strip():
            return jsonify({"error": "Query cannot be empty"}), 400
        
        result = mcp_client.search_business_data(query, search_type, size)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@app.route('/api/aggregate', methods=['POST'])
def aggregate_metrics():
    """Handle aggregation requests via MCP"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        metric = data.get('metric')
        group_by = data.get('group_by')
        time_range = data.get('time_range')
        
        logger.info(f"Aggregation request via MCP: metric={metric}, group_by={group_by}, time_range={time_range}")
        
        if not metric or not group_by:
            return jsonify({"error": "Metric and group_by are required"}), 400
        
        result = mcp_client.aggregate_business_metrics(metric, group_by, time_range)
        
        # Debug log the result
        logger.info(f"MCP Aggregation result: {len(result.get('results', []))} buckets, total_value={result.get('total_value', 0)}")
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Aggregation endpoint error: {e}")
        return jsonify({
            "metric": metric if 'metric' in locals() else "unknown",
            "group_by": group_by if 'group_by' in locals() else "unknown", 
            "results": [],
            "error": str(e)
        }), 500

@app.route('/api/claude-qa', methods=['POST'])
def claude_qa():
    """Ask Claude questions about business data"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        question = data.get('question', '')
        include_search = data.get('include_search', True)
        search_query = data.get('search_query', question)
        
        if not question.strip():
            return jsonify({"error": "Question cannot be empty"}), 400
        
        # First, search for relevant data if requested
        context_data = None
        if include_search and search_query:
            try:
                # Use keyword search for context (since semantic might not be available)
                search_result = mcp_client.search_business_data(search_query, "keyword", 5)
                if search_result.get('results'):
                    context_data = search_result
            except Exception as e:
                logger.warning(f"Search for context failed: {e}")
        
        # Ask Claude about the data
        claude_response = mcp_client.ask_claude_about_data(question, context_data)
        
        # Combine response with search results
        response = {
            "question": question,
            "answer": claude_response["answer"],
            "context_data": context_data,
            "needs_more_data": claude_response.get("needs_data", False),
            "suggestion": claude_response.get("suggestion", "")
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Claude Q&A endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-search', methods=['POST'])
def smart_search():
    """Intelligent search that combines data retrieval with analysis"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        query = data.get('query', '')
        
        if not query.strip():
            return jsonify({"error": "Query cannot be empty"}), 400
        
        logger.info(f"Smart search: '{query}'")
        
        # Step 1: Search for relevant data
        search_results = []
        try:
            search_result = mcp_client.search_business_data(query, "keyword", 10)
            if search_result.get('results'):
                search_results = search_result['results']
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        
        # Step 2: Get business summary for context
        try:
            business_summary = mcp_client.get_business_summary()
        except Exception as e:
            logger.warning(f"Business summary failed: {e}")
            business_summary = None
        
        # Step 3: Try some relevant aggregations
        aggregation_results = []
        common_aggregations = [
            ("sales", "region"),
            ("revenue", "product_category"),
            ("orders", "sales_rep")
        ]
        
        for metric, group_by in common_aggregations:
            try:
                agg_result = mcp_client.aggregate_business_metrics(metric, group_by, None)
                if agg_result.get('results'):
                    aggregation_results.append(agg_result)
            except:
                continue
        
        # Step 4: Analyze results
        analysis = {
            "summary": f"Smart search analyzed your query '{query}' and found {len(search_results)} relevant records.",
            "insights": [
                f"Search identified {len(search_results)} matching business records",
                f"Generated {len(aggregation_results)} metric summaries",
                "Data includes sales, revenue, and operational metrics across regions and categories"
            ],
            "recommendations": [
                "Review the search results for specific data points",
                "Check the aggregations for high-level trends",
                "Use the Claude Q&A feature for detailed analysis",
                "Try more specific search terms for targeted results"
            ]
        }
        
        # Add business summary insights if available
        if business_summary:
            total_records = business_summary.get('summary', {}).get('total_records', 0)
            analysis["insights"].insert(0, f"Database contains {total_records:,} total business records")
        
        return jsonify({
            "query": query,
            "search_results": search_results[:10],
            "aggregations": aggregation_results,
            "business_summary": business_summary,
            "analysis": analysis
        }), 200
    
    except Exception as e:
        logger.error(f"Smart search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-agg')
def test_aggregation():
    """Test aggregation endpoint via MCP"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
        
        # Test a simple aggregation
        result = mcp_client.aggregate_business_metrics("sales", "region", None)
        
        return jsonify({
            "test": "mcp_aggregation",
            "raw_result": result,
            "has_results": len(result.get('results', [])) > 0,
            "total_value": result.get('total_value', 0),
            "error": result.get('error', None)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Enhanced health check via MCP"""
    try:
        if not mcp_client:
            return jsonify({
                "status": "unhealthy",
                "mcp_client": "not_available",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        health_info = mcp_client.get_health_info()
        health_info.update({
            "architecture": "Flask Web App → MCP Server → Elasticsearch",
            "elasticsearch_endpoint": os.getenv("ELASTICSEARCH_ENDPOINT", "Not configured"),
            "index": os.getenv("ELASTICSEARCH_INDEX", "business_intelligence"),
            "features": ["search", "aggregations", "claude_qa", "smart_search", "business_summary"]
        })
        
        return jsonify(health_info)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/mcp-tools')
def list_mcp_tools():
    """List available MCP tools"""
    try:
        if not mcp_client:
            return jsonify({"error": "MCP client not available"}), 500
        
        result = mcp_client.call_mcp_tool("tools/list", {})
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Cleanup function
def cleanup():
    if mcp_client:
        mcp_client.cleanup()

# Register cleanup
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('NODE_ENV', 'development') == 'development'
    
    print("🚀 Starting MCP-Powered Business Intelligence App")
    print("=" * 60)
    print("🏗️  Architecture: Browser → Flask → MCP Server → Elasticsearch")
    print(f"   Port: {port}")
    print(f"   Elasticsearch: {os.getenv('ELASTICSEARCH_ENDPOINT', 'Not configured')}")
    print(f"   Index: {os.getenv('ELASTICSEARCH_INDEX', 'business_intelligence')}")
    
    if mcp_client:
        print("   Status: ✅ MCP Client Connected")
        try:
            health = mcp_client.get_health_info()
            print(f"   MCP Tools: {health.get('available_tools', 0)} available")
            print(f"   Tools: {', '.join(health.get('tools', []))}")
        except:
            print("   MCP Status: ⚠️  Connected but health check failed")
    else:
        print("   Status: ❌ MCP Client Failed")
    
    print("=" * 60)
    print("🔧 Available Endpoints:")
    print("   • /api/health - System health with MCP status")
    print("   • /api/mcp-tools - List available MCP tools")
    print("   • /api/search - Search via MCP")
    print("   • /api/aggregate - Analytics via MCP") 
    print("   • /api/claude-qa - Ask questions about your data")
    print("   • /api/smart-search - Intelligent search with analysis")
    print("=" * 60)
    print("🚀 Ready! Open http://localhost:5000 in your browser")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    finally:
        cleanup()
