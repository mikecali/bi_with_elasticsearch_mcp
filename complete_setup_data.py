#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from elasticsearch import AsyncElasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteDataSetup:
    """Complete Elasticsearch Business Intelligence setup with data generation and AI inference"""
    
    def __init__(self):
        # Initialize Elasticsearch client with extended timeout
        es_config = {
            "hosts": [os.getenv("ELASTICSEARCH_ENDPOINT", "http://localhost:9200")],
            "request_timeout": 120,  # Extended timeout for inference processing
            "max_retries": 3,
            "retry_on_timeout": True
        }
        
        if os.getenv("ELASTICSEARCH_API_KEY"):
            api_key = os.getenv("ELASTICSEARCH_API_KEY").strip('"')
            es_config["api_key"] = api_key
        else:
            es_config["basic_auth"] = (
                os.getenv("ELASTICSEARCH_USERNAME", "elastic"),
                os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
            )
        
        self.es_client = AsyncElasticsearch(**es_config)
        self.index_name = os.getenv("ELASTICSEARCH_INDEX", "business_intelligence")
        
        # Inference endpoints
        self.inference_endpoints = {
            "elser": os.getenv("ELSER_INFERENCE_ID", ".elser-2-elasticsearch"),
            "embedding": os.getenv("EMBEDDING_INFERENCE_ID", ".multilingual-e5-small-elasticsearch"),
            "rerank": os.getenv("RERANK_INFERENCE_ID", ".rerank-v1-elasticsearch")
        }
        
        # Setup configuration
        self.inference_available = False
        self.batch_size = 10  # Process documents in small batches
    
    async def setup_complete_demo(self, reset: bool = True, skip_inference: bool = False):
        """Complete setup: index, data generation, and AI inference processing"""
        
        logger.info(f"🚀 Starting complete Elasticsearch Business Intelligence setup...")
        logger.info(f"   Index: {self.index_name}")
        logger.info(f"   Reset existing data: {reset}")
        logger.info(f"   Skip AI inference: {skip_inference}")
        
        try:
            # Step 1: Connection test
            await self._test_connection()
            
            # Step 2: Check inference availability
            if not skip_inference:
                self.inference_available = await self._check_inference_endpoints()
            
            # Step 3: Handle existing index
            if reset:
                await self._delete_index_if_exists()
            
            # Step 4: Create index with proper mappings
            await self._create_index_with_mapping()
            
            # Step 5: Generate and index sample data
            sample_data = await self._generate_sample_business_data()
            await self._index_sample_data(sample_data)
            
            # Step 6: Add AI inference if available
            if self.inference_available and not skip_inference:
                await self._add_inference_to_documents()
            elif not skip_inference:
                logger.warning("⚠️  AI inference not available - continuing with basic search only")
            
            # Step 7: Verify setup
            await self._verify_complete_setup()
            
            logger.info("✅ Complete setup finished successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise
        finally:
            await self.es_client.close()
    
    async def _test_connection(self):
        """Test Elasticsearch connection"""
        try:
            info = await self.es_client.info()
            logger.info(f"🔗 Connected to Elasticsearch {info['version']['number']}")
            logger.info(f"   Cluster: {info['cluster_name']}")
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise
    
    async def _check_inference_endpoints(self) -> bool:
        """Check if AI inference endpoints are available"""
        try:
            logger.info("🧠 Checking AI inference endpoints...")
            
            # Get all inference endpoints
            response = await self.es_client.inference.get(inference_id="_all")
            available_endpoints = [ep['inference_id'] for ep in response['endpoints']]
            
            # Check each required endpoint
            endpoints_ok = True
            for name, endpoint_id in self.inference_endpoints.items():
                if name == "rerank":  # Rerank is optional
                    continue
                    
                if endpoint_id in available_endpoints:
                    logger.info(f"   ✅ {name.capitalize()}: {endpoint_id}")
                else:
                    logger.warning(f"   ❌ {name.capitalize()}: {endpoint_id} - NOT FOUND")
                    endpoints_ok = False
            
            if not endpoints_ok:
                return False
            
            # Test ELSER endpoint responsiveness
            try:
                await self.es_client.inference.inference(
                    inference_id=self.inference_endpoints["elser"],
                    body={"input": ["test"]}
                )
                logger.info("   ✅ ELSER endpoint is responsive")
                return True
                
            except Exception as e:
                logger.warning(f"   ⚠️  ELSER endpoint test failed: {e}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  Could not check inference endpoints: {e}")
            return False
    
    async def _delete_index_if_exists(self):
        """Delete index if it exists"""
        try:
            exists = await self.es_client.indices.exists(index=self.index_name)
            if exists:
                await self.es_client.indices.delete(index=self.index_name)
                logger.info(f"🗑️  Deleted existing index: {self.index_name}")
        except Exception as e:
            logger.warning(f"Could not delete index: {e}")
    
    async def _create_index_with_mapping(self):
        """Create index with comprehensive field mappings"""
        mapping = {
            "mappings": {
                "properties": {
                    "date": {"type": "date"},
                    "region": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "product_name": {
                        "type": "text", 
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "product_category": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "sales_rep": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "sales_amount": {"type": "double"},
                    "revenue": {"type": "double"},
                    "order_count": {"type": "integer"},
                    "customer_count": {"type": "integer"},
                    "description": {"type": "text"},
                    "notes": {"type": "text"},
                    # AI inference fields - will be populated later
                    "ml": {
                        "properties": {
                            "inference": {
                                "properties": {
                                    "description_elser": {"type": "sparse_vector"},
                                    "description_embedding": {
                                        "type": "dense_vector",
                                        "dims": 384,  # E5-small embedding dimensions
                                        "index": True,
                                        "similarity": "cosine"
                                    },
                                    "model_id": {
                                        "type": "text",
                                        "fields": {"keyword": {"type": "keyword"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        await self.es_client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"🏗️  Created index with comprehensive field mappings: {self.index_name}")
        
        # Log field count
        field_count = len(mapping["mappings"]["properties"])
        logger.info(f"   📋 Configured {field_count} fields including AI inference fields")
    
    async def _generate_sample_business_data(self) -> List[Dict[str, Any]]:
        """Generate realistic sample business data"""
        logger.info("📊 Generating sample business data...")
        
        regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
        products = [
            {"name": "Enterprise Software License", "category": "Software", "base_price": 50000},
            {"name": "Cloud Storage Subscription", "category": "Cloud Services", "base_price": 1200},
            {"name": "Professional Services", "category": "Services", "base_price": 15000},
            {"name": "Hardware Appliance", "category": "Hardware", "base_price": 25000},
            {"name": "Training Program", "category": "Education", "base_price": 5000},
            {"name": "Support Contract", "category": "Support", "base_price": 8000},
            {"name": "Consulting Services", "category": "Services", "base_price": 12000},
            {"name": "Mobile App License", "category": "Software", "base_price": 8000},
            {"name": "Data Analytics Platform", "category": "Software", "base_price": 75000},
            {"name": "Security Appliance", "category": "Hardware", "base_price": 35000}
        ]
        sales_reps = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eva Martinez", "Frank Chen", "Grace Kim", "Henry Lopez"]
        
        data = []
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 12, 31)
        date_range = (end_date - start_date).days
        
        # Generate 500 sample records
        for i in range(500):
            random_days = random.randint(0, date_range)
            random_date = start_date + timedelta(days=random_days)
            
            region = random.choice(regions)
            product = random.choice(products)
            sales_rep = random.choice(sales_reps)
            
            order_count = random.randint(1, 10)
            customer_count = random.randint(1, min(5, order_count))
            
            # Add some variability to pricing
            price_multiplier = 0.7 + random.random() * 0.6  # 0.7 to 1.3
            sales_amount = product["base_price"] * order_count * price_multiplier
            revenue = sales_amount * (0.8 + random.random() * 0.15)  # 80-95% gross margin
            
            # Create detailed descriptions for better AI inference
            performance_terms = ["strong", "excellent", "outstanding", "solid", "impressive", "remarkable"]
            market_terms = ["growing", "expanding", "competitive", "dynamic", "emerging", "established"]
            
            performance = random.choice(performance_terms)
            market = random.choice(market_terms)
            quarter = f"Q{(random_date.month - 1) // 3 + 1}"
            
            record = {
                "date": random_date.isoformat(),
                "region": region,
                "product_name": product["name"],
                "product_category": product["category"],
                "sales_rep": sales_rep,
                "sales_amount": round(sales_amount, 2),
                "revenue": round(revenue, 2),
                "order_count": order_count,
                "customer_count": customer_count,
                "description": f"{product['name']} sale in {region} handled by {sales_rep}. {order_count} orders from {customer_count} customers generating ${sales_amount:,.0f} in sales revenue.",
                "notes": f"{quarter} {random_date.year} performance shows {performance} results in the {market} {region} market. {product['category']} segment continues to demonstrate solid growth potential."
            }
            data.append(record)
        
        logger.info(f"   Generated {len(data)} business records spanning {start_date.year}-{end_date.year}")
        return data
    
    async def _index_sample_data(self, sample_data: List[Dict[str, Any]]):
        """Index sample data without inference pipeline"""
        logger.info("🔄 Indexing sample business data...")
        
        # Prepare bulk indexing body
        bulk_body = []
        for doc in sample_data:
            bulk_body.extend([
                {"index": {"_index": self.index_name}},
                doc
            ])
        
        # Bulk index the data
        response = await self.es_client.bulk(body=bulk_body, refresh=True)
        
        # Check for errors
        if response.get("errors"):
            error_count = sum(1 for item in response["items"] if "error" in item.get("index", {}))
            logger.warning(f"⚠️  {error_count} documents had indexing errors")
            
            # Log first few errors for debugging
            for item in response["items"][:3]:
                if "error" in item.get("index", {}):
                    error = item["index"]["error"]
                    logger.error(f"   Indexing error: {error.get('reason', 'Unknown error')}")
        else:
            logger.info(f"✅ Successfully indexed {len(sample_data)} documents")
    
    async def _add_inference_to_documents(self):
        """Add AI inference processing to all documents"""
        logger.info("🧠 Adding AI inference to documents...")
        
        try:
            # Get total document count
            count_response = await self.es_client.count(index=self.index_name)
            total_docs = count_response['count']
            logger.info(f"   📊 Processing {total_docs} documents in batches of {self.batch_size}")
            
            processed_count = 0
            batch_num = 0
            
            # Use scroll to process all documents
            search_body = {
                "size": self.batch_size,
                "query": {"match_all": {}},
                "_source": ["description"]  # Only get description field for processing
            }
            
            # Initial search
            response = await self.es_client.search(
                index=self.index_name,
                body=search_body,
                scroll="10m"
            )
            
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            
            while hits:
                batch_num += 1
                logger.info(f"   🔄 Processing batch {batch_num} ({len(hits)} documents)...")
                
                try:
                    # Process this batch
                    batch_processed = await self._process_inference_batch(hits)
                    processed_count += batch_processed
                    
                    # Get next batch
                    response = await self.es_client.scroll(
                        scroll_id=scroll_id,
                        scroll="10m"
                    )
                    hits = response["hits"]["hits"]
                    
                    # Small delay between batches to avoid overwhelming the inference endpoints
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"   ❌ Batch {batch_num} failed: {e}")
                    # Continue with next batch
                    try:
                        response = await self.es_client.scroll(
                            scroll_id=scroll_id,
                            scroll="10m"
                        )
                        hits = response["hits"]["hits"]
                    except:
                        break
            
            # Clear scroll
            try:
                await self.es_client.clear_scroll(scroll_id=scroll_id)
            except:
                pass
            
            logger.info(f"✅ AI inference processing completed! Processed {processed_count} documents")
            
        except Exception as e:
            logger.error(f"❌ AI inference processing failed: {e}")
            raise
    
    async def _process_inference_batch(self, hits) -> int:
        """Process a batch of documents for AI inference"""
        update_body = []
        
        for hit in hits:
            doc_id = hit["_id"]
            description = hit["_source"].get("description", "")
            
            if not description:
                continue
            
            try:
                update_doc = {}
                
                # Get ELSER inference (sparse embedding)
                try:
                    elser_response = await self.es_client.inference.inference(
                        inference_id=self.inference_endpoints["elser"],
                        body={"input": [description]}
                    )
                    
                    if "sparse_embedding" in elser_response and elser_response["sparse_embedding"]:
                        update_doc["ml.inference.description_elser"] = elser_response["sparse_embedding"][0]
                
                except Exception as e:
                    logger.warning(f"      ELSER failed for doc {doc_id}: {e}")
                
                # Get E5 embedding inference (dense embedding)
                try:
                    embedding_response = await self.es_client.inference.inference(
                        inference_id=self.inference_endpoints["embedding"],
                        body={"input": [description]}
                    )
                    
                    if "text_embedding" in embedding_response and embedding_response["text_embedding"]:
                        update_doc["ml.inference.description_embedding"] = embedding_response["text_embedding"][0]
                
                except Exception as e:
                    logger.warning(f"      Embedding failed for doc {doc_id}: {e}")
                
                # Add model IDs for tracking
                if update_doc:
                    update_doc["ml.inference.model_id"] = [
                        self.inference_endpoints["elser"],
                        self.inference_endpoints["embedding"]
                    ]
                    
                    update_body.extend([
                        {"update": {"_index": self.index_name, "_id": doc_id}},
                        {"doc": update_doc}
                    ])
                
            except Exception as e:
                logger.warning(f"      ⚠️  Failed to process document {doc_id}: {e}")
                continue
        
        # Bulk update if we have any updates
        if update_body:
            try:
                response = await self.es_client.bulk(body=update_body, refresh=False)
                
                # Count successful updates
                successful = 0
                for item in response["items"]:
                    if "update" in item and item["update"].get("result") == "updated":
                        successful += 1
                
                logger.info(f"      ✅ Updated {successful} documents with AI inference")
                return successful
                
            except Exception as e:
                logger.error(f"      ❌ Bulk update failed: {e}")
                return 0
        
        return 0
    
    async def _verify_complete_setup(self):
        """Verify the complete setup was successful"""
        logger.info("🔍 Verifying complete setup...")
        
        # Check document count
        count_response = await self.es_client.count(index=self.index_name)
        doc_count = count_response['count']
        logger.info(f"   📊 Total documents: {doc_count}")
        
        # Get a sample document to check all features
        search_response = await self.es_client.search(
            index=self.index_name,
            body={"size": 1, "sort": [{"date": {"order": "desc"}}]}
        )
        
        if search_response['hits']['hits']:
            sample_doc = search_response['hits']['hits'][0]['_source']
            
            # Check if inference fields are present
            has_elser = self._check_nested_field(sample_doc, "ml.inference.description_elser")
            has_embedding = self._check_nested_field(sample_doc, "ml.inference.description_embedding")
            
            logger.info(f"   🧠 ELSER inference populated: {'✅' if has_elser else '❌'}")
            logger.info(f"   🧠 Dense embedding populated: {'✅' if has_embedding else '❌'}")
            
            # Log sample document info
            logger.info(f"   📄 Sample document:")
            logger.info(f"      Product: {sample_doc.get('product_name', 'N/A')}")
            logger.info(f"      Region: {sample_doc.get('region', 'N/A')}")
            logger.info(f"      Sales: ${sample_doc.get('sales_amount', 0):,.2f}")
            logger.info(f"      Description: {sample_doc.get('description', 'N/A')[:100]}...")
        
        # Test different search types
        await self._test_search_capabilities()
    
    def _check_nested_field(self, doc: dict, field_path: str) -> bool:
        """Check if a nested field exists and has content"""
        parts = field_path.split('.')
        current = doc
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return current is not None and (
            (isinstance(current, dict) and len(current) > 0) or
            (isinstance(current, list) and len(current) > 0) or
            (not isinstance(current, (dict, list)) and current != "")
        )
    
    async def _test_search_capabilities(self):
        """Test different search capabilities"""
        logger.info("   🔍 Testing search capabilities...")
        
        # Test basic keyword search
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "query": {"match": {"product_name": "software"}},
                    "size": 1
                }
            )
            keyword_hits = response['hits']['total']['value']
            logger.info(f"      ✅ Keyword search: {keyword_hits} matches for 'software'")
        except Exception as e:
            logger.warning(f"      ❌ Keyword search failed: {e}")
        
        # Test semantic search (ELSER) if available
        if self.inference_available:
            try:
                response = await self.es_client.search(
                    index=self.index_name,
                    body={
                        "query": {
                            "sparse_vector": {
                                "field": "ml.inference.description_elser",
                                "inference_id": self.inference_endpoints["elser"],
                                "query": "enterprise solutions"
                            }
                        },
                        "size": 1
                    }
                )
                semantic_hits = response['hits']['total']['value']
                logger.info(f"      ✅ Semantic search: {semantic_hits} matches for 'enterprise solutions'")
            except Exception as e:
                logger.warning(f"      ❌ Semantic search failed: {e}")
        
        # Test aggregation
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "by_region": {
                            "terms": {"field": "region.keyword", "size": 3}
                        }
                    }
                }
            )
            
            if "aggregations" in response and "by_region" in response["aggregations"]:
                buckets = response["aggregations"]["by_region"]["buckets"]
                logger.info(f"      ✅ Aggregations: {len(buckets)} regions found")
            
        except Exception as e:
            logger.warning(f"      ❌ Aggregation test failed: {e}")

async def main():
    """Main function"""
    import sys
    
    # Parse command line arguments
    reset = True
    skip_inference = False
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--no-reset":
                reset = False
            elif arg == "--skip-inference":
                skip_inference = True
            elif arg == "--help":
                print("""
Complete Elasticsearch Business Intelligence Setup

Usage: python complete_setup_data.py [options]

Options:
  --no-reset        Don't delete existing index (append mode)
  --skip-inference  Skip AI inference processing (faster, basic search only)
  --help            Show this help message

Examples:
  python complete_setup_data.py                    # Full setup with AI inference
  python complete_setup_data.py --skip-inference   # Basic setup without AI inference
  python complete_setup_data.py --no-reset         # Add data to existing index
                """)
                return
    
    # Run complete setup
    setup = CompleteDataSetup()
    
    try:
        success = await setup.setup_complete_demo(reset=reset, skip_inference=skip_inference)
        
        if success:
            print("\n🎉 Complete Business Intelligence setup finished successfully!")
            print("\n✅ What's now available:")
            print("   • 500 realistic business records (2023-2024)")
            print("   • Comprehensive field mappings for analytics")
            print("   • Business metrics: sales, revenue, orders, customers")
            print("   • Geographic and product category analysis")
            
            if not skip_inference:
                print("   • 🧠 AI-powered semantic search (ELSER)")
                print("   • 🧠 Multilingual dense embeddings (E5)")
                print("   • 🧠 Hybrid search capabilities")
                print("   • 🧠 All 5 search types fully functional")
            else:
                print("   • ⚠️  AI inference skipped - keyword search only")
            
            print("\n🚀 Next steps:")
            print("   1. Launch web app: python start.py")
            print("   2. Open browser: http://localhost:5000")
            print("   3. Try sample queries:")
            print("      - 'enterprise software sales in North America'")
            print("      - 'professional services performance by region'")
            print("      - 'top performing sales representatives'")
            
            if not skip_inference:
                print("   4. Test AI features:")
                print("      - Switch to 'Semantic (ELSER)' search type")
                print("      - Use 'Ask Claude (MCP)' tab for AI insights")
                print("      - Try 'Smart Search' for comprehensive analysis")
            
        else:
            print("\n❌ Setup failed - check logs above for details")
            return 1
            
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify .env file configuration")
        print("  2. Check Elasticsearch endpoint accessibility")
        print("  3. Ensure inference endpoints are deployed (if using AI features)")
        print("  4. Try with --skip-inference for basic setup")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    if exit_code:
        exit(exit_code)
