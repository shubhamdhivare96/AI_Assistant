"""
Python 3.14 Documentation Ingestion Script
Ingests all Python documentation files from a folder into Qdrant with hierarchical chunking
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
import re
from datetime import datetime
import uuid

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import boto3
import json

from app.services.structure_parser import PythonDocStructureParser
from app.services.hierarchical_chunker import HierarchicalChunker
from app.config import get_settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PythonDocsIngestion:
    """Ingest Python 3.14 documentation into Qdrant"""
    
    def __init__(self, docs_folder: str):
        self.docs_folder = Path(docs_folder)
        self.settings = get_settings()
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url=self.settings.QDRANT_URL,
            api_key=self.settings.QDRANT_API_KEY
        )
        
        # Initialize embedding models
        self.bedrock_client = None
        self.fallback_embedding = None
        self._initialize_embeddings()
        
        # Initialize chunking services
        self.structure_parser = PythonDocStructureParser()
        self.hierarchical_chunker = HierarchicalChunker(
            parent_chunk_size=self.settings.PARENT_CHUNK_SIZE,
            child_chunk_size=self.settings.CHILD_CHUNK_SIZE,
            parent_overlap=self.settings.PARENT_OVERLAP,
            child_overlap=self.settings.CHILD_OVERLAP
        )
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_chunks': 0,
            'parent_chunks': 0,
            'child_chunks': 0,
            'start_time': datetime.now()
        }
    
    def _initialize_embeddings(self):
        """Initialize embedding models"""
        try:
            # Try AWS Nova 2
            if self.settings.AWS_ACCESS_KEY_ID and self.settings.AWS_ACCESS_KEY_ID != "your_aws_access_key_here":
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                    region_name=self.settings.AWS_REGION
                )
                logger.info("✓ AWS Nova 2 embedding initialized")
            else:
                logger.warning("⚠ AWS credentials not configured, using fallback only")
        except Exception as e:
            logger.warning(f"⚠ AWS Nova initialization failed: {e}")
        
        # Fallback: Sentence Transformers
        try:
            self.fallback_embedding = SentenceTransformer(
                self.settings.FALLBACK_EMBEDDING_MODEL
            )
            logger.info("✓ Fallback embedding (Sentence Transformers) initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize fallback embedding: {e}")
            raise
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with fallback"""
        try:
            # Try primary (AWS Nova)
            if self.bedrock_client:
                return await self._generate_nova_embedding(text)
        except Exception as e:
            logger.warning(f"Nova embedding failed: {e}, using fallback")
        
        # Fallback to Sentence Transformers
        embedding = self.fallback_embedding.encode(text).tolist()
        # Pad to 1024 dimensions if needed
        if len(embedding) < self.settings.EMBEDDING_DIMENSIONS:
            embedding = embedding + [0.0] * (self.settings.EMBEDDING_DIMENSIONS - len(embedding))
        return embedding[:self.settings.EMBEDDING_DIMENSIONS]
    
    async def _generate_nova_embedding(self, text: str) -> List[float]:
        """Generate embedding using AWS Nova 2"""
        # Truncate if needed (max 8172 tokens ≈ 32,688 chars)
        max_chars = self.settings.EMBEDDING_MAX_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars]
        
        response = self.bedrock_client.invoke_model(
            modelId=self.settings.EMBEDDING_MODEL,
            body=json.dumps({
                "inputText": text,
                "embeddingConfig": {
                    "outputEmbeddingLength": self.settings.EMBEDDING_DIMENSIONS
                }
            })
        )
        
        result = json.loads(response['body'].read())
        return result['embedding']
    
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_name = "documents"
            
            if collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Creating collection: {collection_name}")
                self.qdrant_client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.settings.EMBEDDING_DIMENSIONS,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ Collection '{collection_name}' created")
            else:
                logger.info(f"✓ Collection '{collection_name}' already exists")
        except Exception as e:
            logger.error(f"✗ Failed to ensure collection exists: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim
        text = text.strip()
        
        return text
    
    def _find_all_text_files(self) -> List[Path]:
        """Find all text files in folder and subfolders"""
        text_files = []
        
        # Common text file extensions for documentation
        extensions = ['.txt', '.md', '.rst', '.text']
        
        logger.info(f"Scanning folder: {self.docs_folder}")
        
        for ext in extensions:
            files = list(self.docs_folder.rglob(f'*{ext}'))
            text_files.extend(files)
            logger.info(f"  Found {len(files)} {ext} files")
        
        logger.info(f"✓ Total files found: {len(text_files)}")
        return text_files
    
    async def _process_file(self, file_path: Path) -> int:
        """Process a single file and return number of chunks created"""
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Read file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Clean text
            content = self._clean_text(content)
            
            if not content or len(content) < 100:
                logger.warning(f"  ⚠ Skipping {file_path.name} (too short or empty)")
                return 0
            
            # Parse structure
            structure = self.structure_parser.parse(content)
            
            # Create hierarchical chunks
            chunks = self.hierarchical_chunker.create_chunks(content, structure)
            
            if not chunks:
                logger.warning(f"  ⚠ No chunks created for {file_path.name}")
                return 0
            
            # Prepare points for Qdrant
            points = []
            
            for chunk in chunks:
                # Generate embedding
                embedding = await self._generate_embedding(chunk.text)
                
                # Prepare metadata
                metadata = {
                    'filename': file_path.name,
                    'filepath': str(file_path.relative_to(self.docs_folder)),
                    'chunk_type': chunk.chunk_type,
                    'parent_id': chunk.parent_id,
                    'module': chunk.metadata.get('module'),
                    'class_name': chunk.metadata.get('class'),
                    'function': chunk.metadata.get('function'),
                    'content_type': chunk.metadata.get('content_type'),
                    'doc_type': 'python-3.14-docs',
                    'start_pos': chunk.start,
                    'end_pos': chunk.end,
                    'text_length': len(chunk.text),
                    'ingestion_date': datetime.now().isoformat()
                }
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        'text': chunk.text,
                        'metadata': metadata
                    }
                )
                points.append(point)
                
                # Update stats
                if chunk.chunk_type == 'parent':
                    self.stats['parent_chunks'] += 1
                else:
                    self.stats['child_chunks'] += 1
            
            # Batch upsert to Qdrant
            if points:
                self.qdrant_client.upsert(
                    collection_name="documents",
                    points=points
                )
                
                self.stats['total_chunks'] += len(points)
                logger.info(f"  ✓ Ingested {len(points)} chunks ({self.stats['parent_chunks']} parents, {self.stats['child_chunks']} children)")
            
            self.stats['files_processed'] += 1
            return len(points)
            
        except Exception as e:
            logger.error(f"  ✗ Failed to process {file_path.name}: {e}")
            self.stats['files_failed'] += 1
            return 0
    
    async def ingest_all(self):
        """Ingest all documentation files"""
        logger.info("=" * 80)
        logger.info("Python 3.14 Documentation Ingestion")
        logger.info("=" * 80)
        
        # Ensure collection exists
        self._ensure_collection_exists()
        
        # Find all files
        files = self._find_all_text_files()
        
        if not files:
            logger.error("✗ No text files found!")
            return
        
        logger.info(f"\nStarting ingestion of {len(files)} files...")
        logger.info("-" * 80)
        
        # Process files
        for i, file_path in enumerate(files, 1):
            logger.info(f"\n[{i}/{len(files)}] {file_path.relative_to(self.docs_folder)}")
            await self._process_file(file_path)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print ingestion summary"""
        duration = datetime.now() - self.stats['start_time']
        
        logger.info("\n" + "=" * 80)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration}")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Files failed: {self.stats['files_failed']}")
        logger.info(f"Total chunks: {self.stats['total_chunks']}")
        logger.info(f"  - Parent chunks: {self.stats['parent_chunks']}")
        logger.info(f"  - Child chunks: {self.stats['child_chunks']}")
        
        if self.stats['files_processed'] > 0:
            avg_chunks = self.stats['total_chunks'] / self.stats['files_processed']
            logger.info(f"Average chunks per file: {avg_chunks:.1f}")
        
        # Get collection stats
        try:
            collection_info = self.qdrant_client.get_collection("documents")
            logger.info(f"\nQdrant Collection Stats:")
            logger.info(f"  - Total vectors: {collection_info.vectors_count}")
            logger.info(f"  - Status: {collection_info.status}")
        except Exception as e:
            logger.warning(f"Could not get collection stats: {e}")
        
        logger.info("=" * 80)
        
        if self.stats['files_failed'] > 0:
            logger.warning(f"\n⚠ {self.stats['files_failed']} files failed. Check ingestion.log for details.")
        else:
            logger.info("\n✓ All files processed successfully!")


async def main():
    """Main entry point"""
    # Get docs folder from command line or use default
    if len(sys.argv) > 1:
        docs_folder = sys.argv[1]
    else:
        docs_folder = r"C:\Users\RDRL\Downloads\AI_Assistant\python-3.14-docs-text\python-3.14-docs-text"
    
    # Validate folder exists
    if not os.path.exists(docs_folder):
        logger.error(f"✗ Folder not found: {docs_folder}")
        sys.exit(1)
    
    # Create ingestion instance
    ingestion = PythonDocsIngestion(docs_folder)
    
    # Run ingestion
    await ingestion.ingest_all()


if __name__ == "__main__":
    asyncio.run(main())
