"""
Simple Python 3.14 Documentation Ingestion Script
Standalone script that doesn't require full app setup
"""
import os
import sys
import re
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding for Windows
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class SimpleDocIngestion:
    """Simple document ingestion with cleaning and chunking"""
    
    def __init__(self, docs_folder: str):
        self.docs_folder = Path(docs_folder)
        
        # Get config from environment
        self.qdrant_url = os.getenv('QDRANT_URL')
        self.qdrant_api_key = os.getenv('QDRANT_API_KEY')
        self.chunk_size = int(os.getenv('CHILD_CHUNK_SIZE', '500'))
        self.chunk_overlap = int(os.getenv('CHILD_OVERLAP', '50'))
        
        # Initialize Qdrant
        logger.info(f"Connecting to Qdrant: {self.qdrant_url}")
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            timeout=60  # Increase timeout to prevent disconnections
        )
        
        # Initialize embedding model (local, no API key needed)
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_chunks': 0,
            'start_time': datetime.now()
        }
    
    def ensure_collection(self):
        """Ensure Qdrant collection exists"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_name = "documents"
            
            if collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Creating collection: {collection_name}")
                self.qdrant_client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"[OK] Collection created")
            else:
                logger.info(f"[OK] Collection exists")
        except Exception as e:
            logger.error(f"✗ Collection error: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Trim overall
        text = text.strip()
        
        return text
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        chunks = []
        
        # Python-specific separators (try to split at logical boundaries)
        separators = [
            '\nclass ',
            '\ndef ',
            '\n    def ',
            '\n\n',
            '\n',
            '. ',
            ' '
        ]
        
        # Simple recursive splitting
        def split_text(text: str, separators: List[str]) -> List[str]:
            if not separators:
                # Base case: split by character
                return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
            
            separator = separators[0]
            remaining_separators = separators[1:]
            
            # Split by current separator
            parts = text.split(separator)
            
            result = []
            current_chunk = ""
            
            for i, part in enumerate(parts):
                # Add separator back (except for first part)
                if i > 0:
                    part = separator + part
                
                # If adding this part would exceed chunk size
                if len(current_chunk) + len(part) > self.chunk_size and current_chunk:
                    result.append(current_chunk)
                    # Start new chunk with overlap
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:] + part
                else:
                    current_chunk += part
            
            # Add remaining chunk
            if current_chunk:
                result.append(current_chunk)
            
            # If chunks are still too large, split further
            final_result = []
            for chunk in result:
                if len(chunk) > self.chunk_size * 1.5:
                    final_result.extend(split_text(chunk, remaining_separators))
                else:
                    final_result.append(chunk)
            
            return final_result
        
        chunks = split_text(text, separators)
        
        # Clean up chunks
        chunks = [c.strip() for c in chunks if c.strip() and len(c.strip()) > 50]
        
        return chunks
    
    def find_text_files(self) -> List[Path]:
        """Find all text files"""
        extensions = ['.txt', '.md', '.rst', '.text']
        files = []
        
        for ext in extensions:
            found = list(self.docs_folder.rglob(f'*{ext}'))
            files.extend(found)
            logger.info(f"Found {len(found)} {ext} files")
        
        logger.info(f"[OK] Total: {len(files)} files")
        return files
    
    def process_file(self, file_path: Path) -> int:
        """Process a single file"""
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Read file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Clean
            content = self.clean_text(content)
            
            if len(content) < 100:
                logger.warning(f"  [SKIP] Too short")
                return 0
            
            # Chunk
            chunks = self.chunk_text(content)
            
            if not chunks:
                logger.warning(f"  [SKIP] No chunks created")
                return 0
            
            # Create points
            points = []
            for i, chunk_text in enumerate(chunks):
                # Generate embedding
                embedding = self.embedding_model.encode(chunk_text).tolist()
                
                # Metadata
                metadata = {
                    'filename': file_path.name,
                    'filepath': str(file_path.relative_to(self.docs_folder)),
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'doc_type': 'python-3.14-docs',
                    'ingestion_date': datetime.now().isoformat()
                }
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        'text': chunk_text,
                        'metadata': metadata
                    }
                )
                points.append(point)
            
            # Upload to Qdrant (batch)
            if points:
                self.qdrant_client.upsert(
                    collection_name="documents",
                    points=points
                )
                logger.info(f"  [OK] Uploaded {len(points)} chunks")
            
            self.stats['files_processed'] += 1
            self.stats['total_chunks'] += len(points)
            return len(points)
            
        except Exception as e:
            logger.error(f"  [ERROR] {e}")
            self.stats['files_failed'] += 1
            return 0
    
    def ingest_all(self):
        """Ingest all files"""
        logger.info("=" * 80)
        logger.info("Python 3.14 Documentation Ingestion (Simple)")
        logger.info("=" * 80)
        
        # Ensure collection
        self.ensure_collection()
        
        # Find files
        files = self.find_text_files()
        
        if not files:
            logger.error("✗ No files found!")
            return
        
        logger.info(f"\nProcessing {len(files)} files...")
        logger.info("-" * 80)
        
        # Process each file
        for i, file_path in enumerate(files, 1):
            logger.info(f"\n[{i}/{len(files)}]")
            self.process_file(file_path)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        duration = datetime.now() - self.stats['start_time']
        
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration}")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Files failed: {self.stats['files_failed']}")
        logger.info(f"Total chunks: {self.stats['total_chunks']}")
        
        try:
            info = self.qdrant_client.get_collection("documents")
            logger.info(f"\nQdrant Collection:")
            logger.info(f"  Total vectors: {info.points_count}")
            logger.info(f"  Status: {info.status}")
        except Exception as e:
            logger.warning(f"Could not get stats: {e}")
        
        logger.info("=" * 80)
        
        if self.stats['files_failed'] == 0:
            logger.info("\n[SUCCESS] All files processed!")
        else:
            logger.warning(f"\n[WARNING] {self.stats['files_failed']} files failed")


def main():
    """Main entry point"""
    # Get folder from command line or use default
    if len(sys.argv) > 1:
        docs_folder = sys.argv[1]
    else:
        docs_folder = r"C:\Users\RDRL\Downloads\AI_Assistant\python-3.14-docs-text\python-3.14-docs-text"
    
    # Validate
    if not os.path.exists(docs_folder):
        logger.error(f"[ERROR] Folder not found: {docs_folder}")
        sys.exit(1)
    
    logger.info(f"Docs folder: {docs_folder}")
    
    # Run ingestion
    ingestion = SimpleDocIngestion(docs_folder)
    ingestion.ingest_all()


if __name__ == "__main__":
    main()
