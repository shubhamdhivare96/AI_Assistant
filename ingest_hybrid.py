import os
import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from app.services.rag_service import RAGService
from app.config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridIngestor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.rag_service = RAGService()

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines).strip()

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap using logical boundaries"""
        separators = ['\nclass ', '\ndef ', '\n    def ', '\n\n', '\n', '. ', ' ']
        
        def split_recursive(text: str, current_separators: List[str]) -> List[str]:
            if not current_separators:
                return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
            
            sep = current_separators[0]
            parts = text.split(sep)
            result = []
            current_chunk = ""
            
            for i, part in enumerate(parts):
                if i > 0: part = sep + part
                if len(current_chunk) + len(part) > self.chunk_size and current_chunk:
                    result.append(current_chunk)
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:] + part
                else:
                    current_chunk += part
            
            if current_chunk: result.append(current_chunk)
            
            final = []
            for chunk in result:
                if len(chunk) > self.chunk_size * 1.5:
                    final.extend(split_recursive(chunk, current_separators[1:]))
                else:
                    final.append(chunk)
            return final

        chunks = split_recursive(text, separators)
        return [c.strip() for c in chunks if len(c.strip()) > 50]

    async def run_ingestion(self, docs_folder: Path):
        await self.rag_service.initialize()
        files = list(docs_folder.rglob("*.txt"))
        logger.info(f"Starting ingestion for {len(files)} files...")

        file_batch_size = 50
        for i in range(0, len(files), file_batch_size):
            file_batch = files[i : i + file_batch_size]
            all_docs = []
            
            for file_path in file_batch:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    content = self.clean_text(content)
                    chunks = self.chunk_text(content)
                    
                    for j, chunk in enumerate(chunks):
                        all_docs.append({
                            "text": chunk,
                            "metadata": {
                                "filename": file_path.name,
                                "filepath": str(file_path.relative_to(docs_folder)),
                                "chunk_index": j,
                                "doc_type": "python-3.14-docs"
                            }
                        })
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")

            if all_docs:
                logger.info(f"Uploading {len(all_docs)} chunks from batch {i//50 + 1}...")
                await self.rag_service.add_documents(all_docs)

        logger.info("Full hybrid ingestion complete!")

async def main():
    load_dotenv()
    docs_folder = Path(r"C:\Users\RDRL\Downloads\AI_Assistant\python-3.14-docs-text")
    if not docs_folder.exists():
        logger.error(f"Folder not found: {docs_folder}")
        return

    ingestor = HybridIngestor()
    await ingestor.run_ingestion(docs_folder)

if __name__ == "__main__":
    asyncio.run(main())
