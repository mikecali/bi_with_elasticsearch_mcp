#!/usr/bin/env python3

import asyncio
import json
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class ElasticsearchHandler:
    """Direct Elasticsearch handler that's MCP-compatible"""
    
    def __init__(self):
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
        
        try:
            self.es_client = Elasticsearch(**es_config)
            self.index_name = os.getenv("ELASTICSEARCH_INDEX", "business_intelligence")
            
            # Inference endpoints
            self.inference_endpoints = {
                "elser": os.getenv("ELSER_INFERENCE_ID", ".elser-2-elasticsearch"),
                "embedding": os.getenv("EMBEDDING_INFERENCE_ID", ".multilingual-e5-small-elasticsearch"),
                "rerank": os.getenv("RERANK_INFERENCE_ID", ".rerank-v1-elasticsearch"),
                "completion": os.getenv("COMPLETION_INFERENCE_ID", "claude-completions")
            }
            
            # Test connection and check available fields
            info = self.es_client.info()
            logger.info(f"Connected to Elasticsearch {info['version']['number']}")
            
            # Check what fields are available
            self._check_available_fields()
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

    def _check_available_fields(self):
        """Check what fields are available in the index"""
        try:
            mapping = self.es_client.indices.get_mapping(index=self.index_name)
            properties = mapping[self.index_name]['mappings'].get('properties', {})
            
            # Check for ML inference fields
            self.has_elser_field = 'ml' in properties and 'inference' in properties['ml'].get('properties', {})
            self.has_embedding_field = self.has_elser_field
            
            logger.info(f"Index analysis:")
            logger.info(f"  - ELSER field available: {self.has_elser_field}")
            logger.info(f"  - Embedding field available: {self.has_embedding_field}")
            
            # Get sample document
            sample = self.es_client.search(index=self.index_name, body={"size": 1})
            if sample['hits']['hits']:
                sample_doc = sample['hits']['hits'][0]['_source']
                logger.info(f"  - Sample fields: {list(sample_doc.keys())}")
                
        except Exception as e:
            logger.warning(f"Could not analyze index structure: {e}")
            self.has_elser_field = False
            self.has_embedding_field = False

    def search_business_data(self, query, search_type="keyword", size=10):
        """Search business data - MCP-compatible format"""
        
        try:
            logger.info(f"Searching: '{query}' (type: {search_type}, size: {size})")
            
            # Build search query based on type with fallbacks
            if search_type == "keyword":
                search_query = self._build_keyword_query(query, size)
            elif search_type == "semantic" and self.has_elser_field:
                search_query = self._build_semantic_query(query, size)
            elif search_type == "embedding" and self.has_embedding_field:
                search_query = self._build_embedding_query(query, size)
            elif search_type == "hybrid" and self.has_elser_field:
                search_query = self._build_hybrid_query(query, size)
            else:
                # Fallback to keyword
                logger.warning(f"Search type '{search_type}' not available, using keyword")
                search_query = self._build_keyword_query(query, size)
                search_type = "keyword (fallback)"
            
            response = self.es_client.search(index=self.index_name, body=search_query)
            
            logger.info(f"Search response: {response['hits']['total']['value']} total hits")
            
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
            # Try keyword search as fallback
            if search_type != "keyword":
                logger.info("Attempting keyword search as fallback")
                return self.search_business_data(query, "keyword", size)
            else:
                raise

    def _build_keyword_query(self, query, size):
        """Optimized keyword search"""
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
            "size": min(size, 10),
            "sort": [
                {"_score": {"order": "desc"}},
                {"sales_amount": {"order": "desc"}}
            ],
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def _build_semantic_query(self, query, size):
        """Semantic search using ELSER"""
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
            "size": min(size, 10),
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def _build_embedding_query(self, query, size):
        """Dense vector search - simplified"""
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
                    "size": min(size, 10),
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
        """Hybrid search"""
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
            "size": min(size, 10),
            "_source": {
                "excludes": ["ml.inference.*", "ml.*"]
            }
        }

    def aggregate_business_metrics(self, metric, group_by, time_range=None):
        """Aggregate business metrics - MCP-compatible format"""
        
        try:
            logger.info(f"Aggregating {metric} by {group_by} for {time_range}")
            
            # Map metric names to field names
            metric_field_map = {
                "sales": "sales_amount",
                "revenue": "revenue", 
                "orders": "order_count",
                "customers": "customer_count"
            }
            
            aggregation_field = metric_field_map.get(metric, "sales_amount")
            
            # Build time filter - use generous ranges
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
            return {
                "metric": metric,
                "group_by": group_by,
                "time_range": time_range,
                "aggregation_type": "sum",
                "total_value": 0,
                "results": [],
                "error": str(e)
            }

    def ask_claude_about_data(self, question, context_data=None):
        """Ask Claude about data using the inference endpoint"""
        try:
            logger.info(f"Asking Claude: '{question}'")
            
            # Prepare context
            context = ""
            if context_data and context_data.get('results'):
                # Summarize the data for Claude
                results = context_data['results'][:5]  # Limit to first 5 results
                context = f"Based on this business data (showing {len(results)} of {context_data.get('total_hits', 0)} results):\n\n"
                
                for i, result in enumerate(results, 1):
                    context += f"{i}. {result.get('product_name', 'Unknown Product')}\n"
                    context += f"   Region: {result.get('region', 'N/A')}\n"
                    context += f"   Sales: ${result.get('sales_amount', 0):,.2f}\n"
                    context += f"   Orders: {result.get('order_count', 0)}\n"
                    context += f"   Rep: {result.get('sales_rep', 'N/A')}\n\n"
            
            # Create a comprehensive prompt for Claude
            prompt = f"""You are a business intelligence analyst. {context}

Question: {question}

Please provide a clear, insightful answer based on the data. Include specific numbers when relevant and highlight any trends or patterns you can identify. If you need more specific data to answer the question fully, suggest what type of search or analysis would be helpful."""

            # Use Claude inference endpoint
            try:
                inference_response = self.es_client.inference.inference(
                    inference_id=self.inference_endpoints["completion"],
                    body={"input": [prompt]}
                )
                
                if "completion" in inference_response and inference_response["completion"]:
                    claude_answer = inference_response["completion"][0]["result"]
                    
                    return {
                        "answer": claude_answer,
                        "has_context": bool(context_data),
                        "context_summary": f"Analyzed {len(context_data.get('results', []))} records" if context_data else "No context data provided",
                        "needs_data": not bool(context_data)
                    }
                else:
                    raise Exception("No completion in Claude response")
                    
            except Exception as e:
                logger.warning(f"Claude inference failed: {e}")
                # Fallback response
                if context_data:
                    return {
                        "answer": f"Based on the {len(context_data.get('results', []))} business records found, I can see data related to your question '{question}'. The data includes sales figures, regional information, and performance metrics that could help answer your question. For more detailed analysis, I'd recommend using the search and analytics features to get more specific data.",
                        "has_context": True,
                        "context_summary": f"Found {len(context_data.get('results', []))} relevant records",
                        "needs_data": False,
                        "note": "Claude inference endpoint not available, using data summary"
                    }
                else:
                    return {
                        "answer": f"To answer '{question}', I would need to search your business data first. Please use the search function to find relevant data, then I can analyze it for you.",
                        "has_context": False,
                        "suggestion": "Search for relevant business data first",
                        "needs_data": True
                    }
                    
        except Exception as e:
            logger.error(f"Claude query failed: {e}")
            raise

# Global handler
try:
    es_handler = ElasticsearchHandler()
    logger.info("Elasticsearch handler initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Elasticsearch handler: {e}")
    es_handler = None

@app.route('/')
def index():
    """Serve the main UI page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_business_data():
    """Handle search requests"""
    try:
        if not es_handler:
            return jsonify({"error": "Elasticsearch not connected"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        query = data.get('query', '')
        search_type = data.get('search_type', 'keyword')
        size = data.get('size', 10)
        
        if not query.strip():
            return jsonify({"error": "Query cannot be empty"}), 400
        
        result = es_handler.search_business_data(query, search_type, size)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@app.route('/api/aggregate', methods=['POST'])
def aggregate_metrics():
    """Handle aggregation requests"""
    try:
        if not es_handler:
            return jsonify({"error": "Elasticsearch not connected"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        metric = data.get('metric')
        group_by = data.get('group_by')
        time_range = data.get('time_range')
        
        if not metric or not group_by:
            return jsonify({"error": "Metric and group_by are required"}), 400
        
        result = es_handler.aggregate_business_metrics(metric, group_by, time_range)
        
        logger.info(f"Aggregation result: {len(result.get('results', []))} buckets, total_value={result.get('total_value', 0)}")
        
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
        if not es_handler:
            return jsonify({"error": "Elasticsearch not connected"}), 500
            
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
                # Use semantic search for better context
                search_result = es_handler.search_business_data(search_query, "semantic", 5)
                if search_result.get('results'):
                    context_data = search_result
            except Exception as e:
                logger.warning(f"Search for context failed: {e}")
                # Try keyword search as fallback
                try:
                    search_result = es_handler.search_business_data(search_query, "keyword", 5)
                    if search_result.get('results'):
                        context_data = search_result
                except:
                    pass
        
        # Ask Claude about the data
        claude_response = es_handler.ask_claude_about_data(question, context_data)
        
        # Combine response with search results
        response = {
            "question": question,
            "answer": claude_response["answer"],
            "context_data": context_data,
            "needs_more_data": claude_response.get("needs_data", False),
            "suggestion": claude_response.get("suggestion", ""),
            "context_summary": claude_response.get("context_summary", ""),
            "note": claude_response.get("note", "")
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Claude Q&A endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-search', methods=['POST'])
def smart_search():
    """Intelligent search with analysis"""
    try:
        if not es_handler:
            return jsonify({"error": "Elasticsearch not connected"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        query = data.get('query', '')
        
        if not query.strip():
            return jsonify({"error": "Query cannot be empty"}), 400
        
        logger.info(f"Smart search: '{query}'")
        
        # Search for relevant data using multiple methods
        search_results = []
        
        # Try semantic search first
        try:
            semantic_result = es_handler.search_business_data(query, "semantic", 5)
            if semantic_result.get('results'):
                search_results.extend(semantic_result['results'])
        except:
            pass
        
        # Try keyword search as backup
        try:
            keyword_result = es_handler.search_business_data(query, "keyword", 5)
            if keyword_result.get('results'):
                # Add keyword results that aren't already included
                for result in keyword_result['results']:
                    if not any(r.get('product_name') == result.get('product_name') and 
                              r.get('region') == result.get('region') for r in search_results):
                        search_results.append(result)
        except:
            pass
        
        # Get relevant aggregations
        aggregation_results = []
        common_aggregations = [
            ("sales", "region"),
            ("revenue", "product_category"),
            ("orders", "sales_rep")
        ]
        
        for metric, group_by in common_aggregations:
            try:
                agg_result = es_handler.aggregate_business_metrics(metric, group_by, None)
                if agg_result.get('results'):
                    aggregation_results.append(agg_result)
            except:
                continue
        
        # Analyze with Claude if possible
        analysis_context = {
            "results": search_results[:10],
            "total_hits": len(search_results)
        }
        
        try:
            claude_analysis = es_handler.ask_claude_about_data(
                f"Analyze this data for the query '{query}' and provide insights and recommendations",
                analysis_context
            )
            
            analysis = {
                "summary": claude_analysis["answer"],
                "ai_powered": True,
                "has_context": claude_analysis.get("has_context", False)
            }
            
        except Exception as e:
            logger.warning(f"Claude analysis failed: {e}")
            # Fallback analysis
            analysis = {
                "summary": f"Found {len(search_results)} relevant records and {len(aggregation_results)} aggregation results for query: '{query}'",
                "insights": [
                    f"Search identified {len(search_results)} relevant business records",
                    f"Aggregations show performance across {len(aggregation_results)} different dimensions",
                    "Data includes sales, revenue, and operational metrics"
                ],
                "recommendations": [
                    "Try semantic search for concept-based queries",
                    "Use keyword search for specific product or region names",
                    "Check Quick Analytics for pre-built reports"
                ],
                "ai_powered": False
            }
        
        return jsonify({
            "query": query,
            "search_results": search_results[:10],
            "aggregations": aggregation_results,
            "analysis": analysis
        }), 200
    
    except Exception as e:
        logger.error(f"Smart search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-agg')
def test_aggregation():
    """Test aggregation endpoint"""
    try:
        if not es_handler:
            return jsonify({"error": "Elasticsearch not connected"}), 500
        
        result = es_handler.aggregate_business_metrics("sales", "region", None)
        
        return jsonify({
            "test": "direct_elasticsearch_aggregation",
            "raw_result": result,
            "has_results": len(result.get('results', [])) > 0,
            "total_value": result.get('total_value', 0),
            "error": result.get('error', None),
            "mcp_compatible": True
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check"""
    try:
        if not es_handler:
            return jsonify({
                "status": "unhealthy",
                "elasticsearch": "not_connected",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        info = es_handler.es_client.info()
        count_response = es_handler.es_client.count(index=es_handler.index_name)
        
        health_info = {
            "status": "healthy",
            "architecture": "Flask Web App → Direct Elasticsearch (MCP-Compatible)",
            "elasticsearch_endpoint": os.getenv("ELASTICSEARCH_ENDPOINT"),
            "elasticsearch_version": info['version']['number'],
            "cluster_name": info['cluster_name'],
            "index": es_handler.index_name,
            "document_count": count_response['count'],
            "has_elser_field": es_handler.has_elser_field,
            "has_embedding_field": es_handler.has_embedding_field,
            "claude_inference": es_handler.inference_endpoints["completion"],
            "features": ["search", "aggregations", "claude_qa", "smart_search"],
            "mcp_compatible": True,
            "timestamp": datetime.now().isoformat()
        }
        
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
    """List MCP-compatible tools (simulated)"""
    return jsonify({
        "tools": [
            {
                "name": "search_business_data",
                "description": "Search business intelligence data using natural language queries"
            },
            {
                "name": "aggregate_business_metrics", 
                "description": "Perform aggregations on business data"
            },
            {
                "name": "claude_qa",
                "description": "Ask Claude questions about business data with context"
            }
        ],
        "note": "This web app uses direct Elasticsearch but is MCP-compatible"
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('NODE_ENV', 'development') == 'development'
    
    print("🚀 Starting MCP-Compatible Business Intelligence Web App")
    print("=" * 60)
    print("🏗️  Architecture: Browser → Flask → Direct Elasticsearch")
    print("🔗  MCP Compatible: Ready for AI assistant integration")
    print(f"   Port: {port}")
    print(f"   Elasticsearch: {os.getenv('ELASTICSEARCH_ENDPOINT', 'Not configured')}")
    print(f"   Index: {os.getenv('ELASTICSEARCH_INDEX', 'business_intelligence')}")
    
    if es_handler:
        print("   Status: ✅ Elasticsearch Connected")
        print(f"   ELSER available: {es_handler.has_elser_field}")
        print(f"   Embeddings available: {es_handler.has_embedding_field}")
        print(f"   Claude Inference: {es_handler.inference_endpoints['completion']}")
    else:
        print("   Status: ❌ Elasticsearch Connection Failed")
    
    print("=" * 60)
    print("🔧 Available Features:")
    print("   • All search types (keyword, semantic, hybrid, embedding)")
    print("   • Quick Analytics with aggregations")
    print("   • Claude Q&A using your inference endpoint")
    print("   • Smart Search with AI analysis")
    print("   • MCP-compatible data formats")
    print("=" * 60)
    print("🤖 For Full MCP Integration:")
    print("   1. Run this web app for human users")
    print("   2. Run 'python elasticsearch_mcp_server_fixed.py' separately for AI")
    print("   3. Connect Claude Desktop to the MCP server")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
