#!/usr/bin/env python3
"""
Standalone MCP Server for Business Intelligence
This is the actual MCP server that implements the protocol
"""

import asyncio
import json
import sys
import os
import logging
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BusinessIntelligenceMCPServer:
    """MCP Server for Business Intelligence with Elasticsearch"""
    
    def __init__(self):
        """Initialize the MCP server"""
        self.setup_elasticsearch()
        
    def setup_elasticsearch(self):
        """Set up Elasticsearch connection"""
        try:
            es_config = {
                "hosts": [os.getenv("ELASTICSEARCH_ENDPOINT")],
                "request_timeout": 15,
                "max_retries": 1
            }
            
            if os.getenv("ELASTICSEARCH_API_KEY"):
                es_config["api_key"] = os.getenv("ELASTICSEARCH_API_KEY").strip('"')
            else:
                es_config["basic_auth"] = (
                    os.getenv("ELASTICSEARCH_USERNAME", "elastic"),
                    os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
                )
            
            self.es_client = Elasticsearch(**es_config)
            self.index_name = os.getenv("ELASTICSEARCH_INDEX", "business_intelligence")
            
            # Test connection
            info = self.es_client.info()
            logger.info(f"Connected to Elasticsearch {info['version']['number']}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

    async def handle_request(self, request):
        """Handle incoming MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Ensure request_id is never null for JSON-RPC compliance
            if request_id is None:
                request_id = 0
            
            # Handle MCP protocol initialization
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.list_tools()
            elif method == "tools/call":
                result = await self.call_tool(params)
            else:
                # Return proper error response
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            # Ensure we always have a valid request_id
            error_id = request.get("id") if request.get("id") is not None else 0
            
            return {
                "jsonrpc": "2.0",
                "id": error_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    async def handle_initialize(self, params):
        """Handle MCP initialization request"""
        logger.info("Handling MCP initialize request")
        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "business-intelligence",
                "version": "1.0.0"
            }
        }

    async def list_tools(self):
        """List available MCP tools"""
        return {
            "tools": [
                {
                    "name": "search_business_data",
                    "description": "Search business intelligence data using natural language queries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "search_type": {"type": "string", "description": "Type of search (keyword, semantic, embedding, hybrid)", "default": "keyword"},
                            "size": {"type": "integer", "description": "Number of results to return", "default": 10}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "aggregate_business_metrics",
                    "description": "Perform aggregations on business data (sales, revenue, orders, customers)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "metric": {"type": "string", "description": "Metric to aggregate (sales, revenue, orders, customers)"},
                            "group_by": {"type": "string", "description": "Field to group by (region, product_category, sales_rep)"},
                            "time_range": {"type": "string", "description": "Time filter (last_month, last_quarter, ytd)", "default": None}
                        },
                        "required": ["metric", "group_by"]
                    }
                },
                {
                    "name": "get_business_summary",
                    "description": "Get a summary of business performance metrics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range": {"type": "string", "description": "Time filter (last_month, last_quarter, ytd)", "default": None}
                        }
                    }
                }
            ]
        }

    async def call_tool(self, params):
        """Call a specific tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Validate tool name
        if not tool_name:
            raise ValueError("Tool name is required")
        
        if tool_name == "search_business_data":
            result = await self.search_business_data(**arguments)
        elif tool_name == "aggregate_business_metrics":
            result = await self.aggregate_business_metrics(**arguments)
        elif tool_name == "get_business_summary":
            result = await self.get_business_summary(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "content": [
                {
                    "type": "text", 
                    "text": json.dumps(result, indent=2)
                }
            ]
        }

    async def search_business_data(self, query, search_type="keyword", size=10):
        """Search business data"""
        try:
            # Validate inputs
            if not query or not isinstance(query, str):
                raise ValueError("Query must be a non-empty string")
            
            if not isinstance(size, int) or size < 1:
                size = 10
                
            logger.info(f"Searching: '{query}' (type: {search_type}, size: {size})")
            
            # Build search query based on type
            if search_type == "keyword":
                search_query = {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["description^2", "product_name^1.5", "region", "sales_rep"],
                                        "type": "best_fields",
                                        "fuzziness": "AUTO"
                                    }
                                },
                                {
                                    "match": {
                                        "product_category": {
                                            "query": query,
                                            "boost": 1.2
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "size": min(size, 100),  # Cap at 100 results
                    "sort": [
                        {"_score": {"order": "desc"}},
                        {"sales_amount": {"order": "desc"}}
                    ]
                }
            else:
                # Fallback to keyword for unsupported types
                logger.warning(f"Search type '{search_type}' not available, using keyword")
                return await self.search_business_data(query, "keyword", size)
            
            response = self.es_client.search(index=self.index_name, body=search_query)
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                result = {
                    "score": round(hit["_score"], 3),
                    "product_name": source.get("product_name", "N/A"),
                    "region": source.get("region", "N/A"),
                    "sales_rep": source.get("sales_rep", "N/A"),
                    "sales_amount": source.get("sales_amount", 0),
                    "revenue": source.get("revenue", 0),
                    "date": source.get("date", ""),
                    "order_count": source.get("order_count", 0),
                    "customer_count": source.get("customer_count", 0),
                    "product_category": source.get("product_category", "N/A"),
                    "description": source.get("description", "")[:200] + "..." if source.get("description", "") else ""
                }
                results.append(result)
            
            return {
                "search_type": search_type,
                "total_hits": response["hits"]["total"]["value"],
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def aggregate_business_metrics(self, metric, group_by, time_range=None):
        """Aggregate business metrics"""
        try:
            # Validate inputs
            if not metric or not isinstance(metric, str):
                raise ValueError("Metric must be a non-empty string")
            if not group_by or not isinstance(group_by, str):
                raise ValueError("Group_by must be a non-empty string")
                
            logger.info(f"Aggregating {metric} by {group_by} for {time_range}")
            
            # Map metric names to field names
            metric_field_map = {
                "sales": "sales_amount",
                "revenue": "revenue", 
                "orders": "order_count",
                "customers": "customer_count"
            }
            
            aggregation_field = metric_field_map.get(metric, "sales_amount")
            
            # Build time filter
            query_filter = {"match_all": {}}
            if time_range == "last_month":
                query_filter = {
                    "range": {
                        "date": {
                            "gte": "now-60d"
                        }
                    }
                }
            elif time_range == "last_quarter":
                query_filter = {
                    "range": {
                        "date": {
                            "gte": "now-180d"
                        }
                    }
                }
            elif time_range == "ytd":
                query_filter = {
                    "range": {
                        "date": {
                            "gte": "2024-01-01"
                        }
                    }
                }
            
            search_body = {
                "query": query_filter,
                "aggs": {
                    "grouped_data": {
                        "terms": {
                            "field": f"{group_by}.keyword",
                            "size": 10,
                            "missing": "Unknown"
                        },
                        "aggs": {
                            "metric_value": {
                                "sum": {
                                    "field": aggregation_field
                                }
                            },
                            "avg_value": {
                                "avg": {
                                    "field": aggregation_field
                                }
                            }
                        }
                    },
                    "total_metric": {
                        "sum": {
                            "field": aggregation_field
                        }
                    }
                },
                "size": 0
            }
            
            response = self.es_client.search(index=self.index_name, body=search_body)
            
            # Process results
            buckets = []
            total_value = response["aggregations"]["total_metric"]["value"]
            
            for bucket in response["aggregations"]["grouped_data"]["buckets"]:
                value = bucket["metric_value"]["value"]
                percentage = (value / total_value * 100) if total_value > 0 else 0
                
                result = {
                    group_by: bucket["key"],
                    metric: round(value, 2),
                    "percentage": round(percentage, 1),
                    "average": round(bucket["avg_value"]["value"], 2),
                    "doc_count": bucket["doc_count"]
                }
                buckets.append(result)
            
            # Sort by metric value descending
            buckets.sort(key=lambda x: x[metric], reverse=True)
            
            return {
                "metric": metric,
                "group_by": group_by,
                "time_range": time_range,
                "aggregation_type": "sum",
                "total_value": round(total_value, 2),
                "results": buckets
            }
            
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            raise

    async def get_business_summary(self, time_range=None):
        """Get a comprehensive business summary"""
        try:
            # Get key metrics
            sales_by_region = await self.aggregate_business_metrics("sales", "region", time_range)
            revenue_by_category = await self.aggregate_business_metrics("revenue", "product_category", time_range)
            orders_by_rep = await self.aggregate_business_metrics("orders", "sales_rep", time_range)
            
            # Get total counts
            count_response = self.es_client.count(index=self.index_name)
            
            return {
                "summary": {
                    "total_records": count_response["count"],
                    "time_range": time_range or "all_time",
                    "generated_at": datetime.now().isoformat()
                },
                "sales_by_region": sales_by_region["results"][:5],
                "revenue_by_category": revenue_by_category["results"][:5],
                "top_sales_reps": orders_by_rep["results"][:5],
                "totals": {
                    "total_sales": sales_by_region["total_value"],
                    "total_revenue": revenue_by_category["total_value"],
                    "total_orders": orders_by_rep["total_value"]
                }
            }
            
        except Exception as e:
            logger.error(f"Business summary failed: {e}")
            raise

    async def run_server(self):
        """Run the MCP server"""
        logger.info("MCP Server started - waiting for requests...")
        
        try:
            while True:
                # Read JSON-RPC request from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                    response = await self.handle_request(request)
                    
                    # Write response to stdout
                    print(json.dumps(response), flush=True)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": 0,  # Use 0 instead of null for invalid JSON
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
        except KeyboardInterrupt:
            logger.info("MCP Server stopping...")
        except Exception as e:
            logger.error(f"MCP Server error: {e}")
            raise

async def main():
    """Main function to run the MCP server"""
    try:
        server = BusinessIntelligenceMCPServer()
        await server.run_server()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
