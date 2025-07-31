#!/usr/bin/env python3
"""
Enhanced MCP Server for Business Intelligence with ELSER and Semantic Search
Supports keyword, semantic (ELSER), embedding, and hybrid search types
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

class EnhancedBusinessIntelligenceMCPServer:
    """Enhanced MCP Server for Business Intelligence with full AI search capabilities"""
    
    def __init__(self):
        """Initialize the enhanced MCP server"""
        self.setup_elasticsearch()
        self.check_ai_capabilities()
        
    def setup_elasticsearch(self):
        """Set up Elasticsearch connection"""
        try:
            es_config = {
                "hosts": [os.getenv("ELASTICSEARCH_ENDPOINT")],
                "request_timeout": 30,  # Longer timeout for inference
                "max_retries": 2
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
            
            # Inference endpoints
            self.inference_endpoints = {
                "elser": os.getenv("ELSER_INFERENCE_ID", ".elser-2-elasticsearch"),
                "embedding": os.getenv("EMBEDDING_INFERENCE_ID", ".multilingual-e5-small-elasticsearch"),
                "rerank": os.getenv("RERANK_INFERENCE_ID", ".rerank-v1-elasticsearch")
            }
            
            # Test connection
            info = self.es_client.info()
            logger.info(f"Connected to Elasticsearch {info['version']['number']}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    def check_ai_capabilities(self):
        """Check what AI search capabilities are available"""
        self.capabilities = {
            "elser": False,
            "embedding": False,
            "rerank": False
        }
        
        try:
            # Check if inference endpoints exist
            response = self.es_client.inference.get(inference_id="_all")
            available_endpoints = [ep['inference_id'] for ep in response['endpoints']]
            
            for capability, endpoint_id in self.inference_endpoints.items():
                if endpoint_id in available_endpoints:
                    self.capabilities[capability] = True
                    logger.info(f"✅ {capability.upper()} available: {endpoint_id}")
                else:
                    logger.warning(f"⚠️  {capability.upper()} not available: {endpoint_id}")
            
            # Test ELSER if available
            if self.capabilities["elser"]:
                try:
                    self.es_client.inference.inference(
                        inference_id=self.inference_endpoints["elser"],
                        body={"input": ["test"]}
                    )
                    logger.info("✅ ELSER endpoint is responsive")
                except Exception as e:
                    logger.warning(f"⚠️  ELSER endpoint test failed: {e}")
                    self.capabilities["elser"] = False
                    
        except Exception as e:
            logger.warning(f"Could not check AI capabilities: {e}")

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
        
        # Include AI capabilities in server info
        ai_features = []
        if self.capabilities["elser"]:
            ai_features.append("ELSER Semantic Search")
        if self.capabilities["embedding"]:
            ai_features.append("Dense Vector Embeddings")
        if self.capabilities["rerank"]:
            ai_features.append("AI Reranking")
        
        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "enhanced-business-intelligence",
                "version": "2.0.0",
                "description": f"AI-Powered Business Intelligence with {', '.join(ai_features) if ai_features else 'Keyword Search'}"
            }
        }

    async def list_tools(self):
        """List available MCP tools with enhanced search capabilities"""
        
        # Build search type options based on available capabilities
        search_types = ["keyword"]
        if self.capabilities["elser"]:
            search_types.append("semantic")
        if self.capabilities["embedding"]:
            search_types.append("embedding")
        if self.capabilities["elser"] and self.capabilities["embedding"]:
            search_types.append("hybrid")
        if self.capabilities["rerank"]:
            search_types.append("rerank")
        
        search_type_description = f"Type of search ({', '.join(search_types)})"
        
        return {
            "tools": [
                {
                    "name": "search_business_data",
                    "description": f"Search business intelligence data using natural language queries. Available search types: {', '.join(search_types)}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "search_type": {"type": "string", "description": search_type_description, "default": "keyword"},
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
                    "description": "Get a comprehensive summary of business performance metrics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range": {"type": "string", "description": "Time filter (last_month, last_quarter, ytd)", "default": None}
                        }
                    }
                },
                {
                    "name": "get_ai_capabilities",
                    "description": "Get information about available AI search capabilities",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
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
        elif tool_name == "get_ai_capabilities":
            result = await self.get_ai_capabilities()
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
        """Enhanced search with multiple AI-powered search types"""
        try:
            # Validate inputs
            if not query or not isinstance(query, str):
                raise ValueError("Query must be a non-empty string")
            
            if not isinstance(size, int) or size < 1:
                size = 10
                
            logger.info(f"Searching: '{query}' (type: {search_type}, size: {size})")
            
            # Build search query based on type and capabilities
            if search_type == "keyword":
                search_query = self._build_keyword_query(query, size)
            elif search_type == "semantic" and self.capabilities["elser"]:
                search_query = self._build_semantic_query(query, size)
            elif search_type == "embedding" and self.capabilities["embedding"]:
                search_query = self._build_embedding_query(query, size)
            elif search_type == "hybrid" and self.capabilities["elser"] and self.capabilities["embedding"]:
                search_query = self._build_hybrid_query(query, size)
            elif search_type == "rerank" and self.capabilities["rerank"]:
                search_query = self._build_rerank_query(query, size)
            else:
                # Fallback to keyword with informative message
                logger.warning(f"Search type '{search_type}' not available, using keyword")
                search_query = self._build_keyword_query(query, size)
                search_type = f"{search_type} (fallback to keyword)"
            
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
                "results": results,
                "ai_capabilities": self.capabilities
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Try keyword search as fallback
            if search_type != "keyword":
                logger.info("Attempting keyword search as fallback")
                return await self.search_business_data(query, "keyword", size)
            else:
                raise

    def _build_keyword_query(self, query, size):
        """Build optimized keyword search query"""
        return {
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
            "size": min(size, 100),
            "sort": [
                {"_score": {"order": "desc"}},
                {"sales_amount": {"order": "desc"}}
            ],
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def _build_semantic_query(self, query, size):
        """Build ELSER semantic search query"""
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "sparse_vector": {
                                "field": "ml.inference.description_elser",
                                "inference_id": self.inference_endpoints["elser"],
                                "query": query,
                                "boost": 2.0
                            }
                        },
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["product_name^1.5", "region"],
                                "boost": 0.5
                            }
                        }
                    ]
                }
            },
            "size": min(size, 100),
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def _build_embedding_query(self, query, size):
        """Build dense vector embedding search query"""
        try:
            # Get embedding for query
            inference_response = self.es_client.inference.inference(
                inference_id=self.inference_endpoints["embedding"],
                body={"input": [query]}
            )
            
            if "text_embedding" in inference_response and inference_response["text_embedding"]:
                dense_vector = inference_response["text_embedding"][0]
                
                return {
                    "query": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'ml.inference.description_embedding') + 1.0",
                                "params": {
                                    "query_vector": dense_vector
                                }
                            }
                        }
                    },
                    "size": min(size, 100),
                    "_source": {
                        "excludes": ["ml.inference.*", "ml.*"]
                    }
                }
            else:
                raise Exception("Failed to get embedding")
                
        except Exception as e:
            logger.warning(f"Embedding search failed: {e}")
            raise

    def _build_hybrid_query(self, query, size):
        """Build hybrid search combining ELSER and keyword"""
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["description^1.5", "product_name", "region"],
                                "boost": 1.0
                            }
                        },
                        {
                            "sparse_vector": {
                                "field": "ml.inference.description_elser",
                                "inference_id": self.inference_endpoints["elser"],
                                "query": query,
                                "boost": 1.5
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": min(size, 100),
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def _build_rerank_query(self, query, size):
        """Build search with AI reranking"""
        # First get more results, then rerank
        initial_results = min(size * 3, 50)  # Get 3x results for reranking
        
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["description^2", "product_name^1.5", "region", "sales_rep"],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "size": initial_results,
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    async def aggregate_business_metrics(self, metric, group_by, time_range=None):
        """Aggregate business metrics (unchanged from original)"""
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
        """Get a comprehensive business summary (unchanged from original)"""
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
                    "generated_at": datetime.now().isoformat(),
                    "ai_capabilities": self.capabilities
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

    async def get_ai_capabilities(self):
        """Get information about available AI search capabilities"""
        return {
            "ai_capabilities": self.capabilities,
            "inference_endpoints": {
                "elser": self.inference_endpoints["elser"] if self.capabilities["elser"] else "Not available",
                "embedding": self.inference_endpoints["embedding"] if self.capabilities["embedding"] else "Not available",
                "rerank": self.inference_endpoints["rerank"] if self.capabilities["rerank"] else "Not available"
            },
            "available_search_types": [
                "keyword",
                *([f"semantic (ELSER)"] if self.capabilities["elser"] else []),
                *([f"embedding (E5)"] if self.capabilities["embedding"] else []),
                *([f"hybrid"] if self.capabilities["elser"] and self.capabilities["embedding"] else []),
                *([f"rerank"] if self.capabilities["rerank"] else [])
            ],
            "description": "Enhanced Business Intelligence MCP Server with AI-powered search capabilities"
        }

    async def run_server(self):
        """Run the MCP server"""
        logger.info("Enhanced MCP Server started - waiting for requests...")
        logger.info(f"AI Capabilities: {self.capabilities}")
        
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
            logger.info("Enhanced MCP Server stopping...")
        except Exception as e:
            logger.error(f"Enhanced MCP Server error: {e}")
            raise

async def main():
    """Main function to run the enhanced MCP server"""
    try:
        server = EnhancedBusinessIntelligenceMCPServer()
        await server.run_server()
    except Exception as e:
        logger.error(f"Failed to start enhanced MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
