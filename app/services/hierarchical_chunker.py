"""
Hierarchical Chunker for Python Documentation
Implements structure-aware chunking with parent-child relationships
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    id: str
    text: str
    chunk_type: str  # 'parent' or 'child'
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    token_count: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HierarchicalChunker:
    """
    Structure-aware chunker for Python documentation
    Creates parent-child chunk relationships
    """
    
    # Python-specific separators (order matters!)
    PYTHON_SEPARATORS = [
        "\nclass ",      # Split between classes
        "\ndef ",        # Split between functions
        "\n    def ",    # Split between methods
        "\n\n",          # Split between paragraphs
        "\n",            # Split between lines
        ". ",            # Split between sentences
        " ",             # Split between words
        ""               # Character split (last resort)
    ]
    
    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        parent_overlap: int = 200,
        child_overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize hierarchical chunker
        
        Args:
            parent_chunk_size: Max tokens for parent chunks (large context)
            child_chunk_size: Max tokens for child chunks (precise retrieval)
            parent_overlap: Token overlap for parent chunks
            child_overlap: Token overlap for child chunks
            encoding_name: Tiktoken encoding name
        """
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.parent_overlap = parent_overlap
        self.child_overlap = child_overlap
        
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}, using len() fallback")
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4
    
    def chunk_document(
        self,
        text: str,
        structure: Any,  # DocumentStructure from structure_parser
        create_parent_child: bool = True
    ) -> List[Chunk]:
        """
        Chunk document with structure awareness
        
        Args:
            text: Document text
            structure: Parsed document structure
            create_parent_child: Whether to create parent-child relationships
        
        Returns:
            List of Chunk objects
        """
        try:
            if create_parent_child:
                return self._create_parent_child_chunks(text, structure)
            else:
                return self._create_flat_chunks(text, structure)
        
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            # Fallback to simple chunking
            return self._fallback_chunking(text, structure)
    
    def _create_parent_child_chunks(
        self,
        text: str,
        structure: Any
    ) -> List[Chunk]:
        """Create parent and child chunks with relationships"""
        all_chunks = []
        
        # Step 1: Create parent chunks (large context)
        parent_chunks = self._split_into_parents(text, structure)
        
        # Step 2: For each parent, create child chunks
        for parent in parent_chunks:
            all_chunks.append(parent)
            
            # Create children from parent text
            children = self._split_into_children(parent.text, parent.id, structure)
            all_chunks.extend(children)
        
        logger.info(
            f"Created {len([c for c in all_chunks if c.chunk_type == 'parent'])} parent chunks, "
            f"{len([c for c in all_chunks if c.chunk_type == 'child'])} child chunks"
        )
        
        return all_chunks
    
    def _split_into_parents(self, text: str, structure: Any) -> List[Chunk]:
        """Split text into parent chunks (large context)"""
        parent_chunks = []
        
        # Try to split by major sections first
        sections = self._split_by_sections(text, structure)
        
        if sections:
            # We have clear sections, use them as parents
            for section in sections:
                chunk_id = str(uuid.uuid4())
                token_count = self.count_tokens(section['text'])
                
                # If section is too large, split it
                if token_count > self.parent_chunk_size:
                    sub_chunks = self._recursive_split(
                        section['text'],
                        self.parent_chunk_size,
                        self.parent_overlap
                    )
                    for i, sub_text in enumerate(sub_chunks):
                        parent_chunks.append(Chunk(
                            id=f"{chunk_id}_{i}",
                            text=sub_text,
                            chunk_type='parent',
                            metadata={
                                'module': structure.module,
                                'section': section.get('title'),
                                'section_level': section.get('level'),
                                'chunk_index': i,
                                'total_chunks': len(sub_chunks)
                            },
                            token_count=self.count_tokens(sub_text)
                        ))
                else:
                    parent_chunks.append(Chunk(
                        id=chunk_id,
                        text=section['text'],
                        chunk_type='parent',
                        metadata={
                            'module': structure.module,
                            'section': section.get('title'),
                            'section_level': section.get('level')
                        },
                        token_count=token_count
                    ))
        else:
            # No clear sections, use recursive splitting
            chunks_text = self._recursive_split(
                text,
                self.parent_chunk_size,
                self.parent_overlap
            )
            for i, chunk_text in enumerate(chunks_text):
                parent_chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    text=chunk_text,
                    chunk_type='parent',
                    metadata={
                        'module': structure.module,
                        'chunk_index': i,
                        'total_chunks': len(chunks_text)
                    },
                    token_count=self.count_tokens(chunk_text)
                ))
        
        return parent_chunks
    
    def _split_into_children(
        self,
        parent_text: str,
        parent_id: str,
        structure: Any
    ) -> List[Chunk]:
        """Split parent text into child chunks (precise retrieval)"""
        child_chunks = []
        
        # Split parent into smaller children
        chunks_text = self._recursive_split(
            parent_text,
            self.child_chunk_size,
            self.child_overlap
        )
        
        for i, chunk_text in enumerate(chunks_text):
            # Extract metadata from chunk content
            chunk_metadata = self._extract_chunk_metadata(chunk_text, structure)
            chunk_metadata['parent_id'] = parent_id
            chunk_metadata['child_index'] = i
            chunk_metadata['total_children'] = len(chunks_text)
            
            child_chunks.append(Chunk(
                id=str(uuid.uuid4()),
                text=chunk_text,
                chunk_type='child',
                parent_id=parent_id,
                metadata=chunk_metadata,
                token_count=self.count_tokens(chunk_text)
            ))
        
        return child_chunks
    
    def _recursive_split(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int
    ) -> List[str]:
        """
        Recursively split text using Python-specific separators
        
        This is the core of structure-aware chunking
        """
        if self.count_tokens(text) <= max_tokens:
            return [text]
        
        chunks = []
        
        # Try each separator in order
        for separator in self.PYTHON_SEPARATORS:
            if separator in text:
                splits = text.split(separator)
                
                # Reconstruct with separator
                current_chunk = ""
                
                for i, split in enumerate(splits):
                    # Add separator back (except for first split)
                    if i > 0:
                        split = separator + split
                    
                    # Check if adding this split exceeds max_tokens
                    test_chunk = current_chunk + split
                    
                    if self.count_tokens(test_chunk) <= max_tokens:
                        current_chunk = test_chunk
                    else:
                        # Current chunk is full, save it
                        if current_chunk:
                            chunks.append(current_chunk)
                        
                        # Start new chunk with overlap
                        if overlap_tokens > 0 and current_chunk:
                            # Get last N tokens from previous chunk
                            overlap_text = self._get_last_n_tokens(
                                current_chunk,
                                overlap_tokens
                            )
                            current_chunk = overlap_text + split
                        else:
                            current_chunk = split
                
                # Add remaining chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If we successfully split, return
                if len(chunks) > 1:
                    return chunks
        
        # If no separator worked, force split by tokens
        return self._force_split_by_tokens(text, max_tokens, overlap_tokens)
    
    def _force_split_by_tokens(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int
    ) -> List[str]:
        """Force split text by token count (last resort)"""
        if self.encoding:
            tokens = self.encoding.encode(text)
            chunks = []
            
            start = 0
            while start < len(tokens):
                end = start + max_tokens
                chunk_tokens = tokens[start:end]
                chunk_text = self.encoding.decode(chunk_tokens)
                chunks.append(chunk_text)
                start = end - overlap_tokens
            
            return chunks
        else:
            # Fallback: split by characters
            chunk_size_chars = max_tokens * 4
            overlap_chars = overlap_tokens * 4
            chunks = []
            
            start = 0
            while start < len(text):
                end = start + chunk_size_chars
                chunks.append(text[start:end])
                start = end - overlap_chars
            
            return chunks
    
    def _get_last_n_tokens(self, text: str, n: int) -> str:
        """Get last N tokens from text for overlap"""
        if self.encoding:
            tokens = self.encoding.encode(text)
            if len(tokens) <= n:
                return text
            last_tokens = tokens[-n:]
            return self.encoding.decode(last_tokens)
        else:
            # Fallback: last N*4 characters
            return text[-(n * 4):]
    
    def _split_by_sections(self, text: str, structure: Any) -> List[Dict[str, Any]]:
        """Split text by document sections"""
        if not structure.sections:
            return []
        
        sections = []
        lines = text.split('\n')
        
        for i, section in enumerate(structure.sections):
            start_line = section['line']
            
            # Find end line (next section or end of document)
            if i < len(structure.sections) - 1:
                end_line = structure.sections[i + 1]['line']
            else:
                end_line = len(lines)
            
            section_text = '\n'.join(lines[start_line:end_line])
            
            sections.append({
                'title': section['title'],
                'level': section['level'],
                'text': section_text,
                'start_line': start_line,
                'end_line': end_line
            })
        
        return sections
    
    def _extract_chunk_metadata(
        self,
        chunk_text: str,
        structure: Any
    ) -> Dict[str, Any]:
        """Extract metadata from chunk content"""
        metadata = {
            'module': structure.module,
            'doc_type': structure.metadata.get('doc_type', 'general')
        }
        
        # Check if chunk contains a class
        for class_name in structure.classes:
            if f"class {class_name}" in chunk_text:
                metadata['class'] = class_name
                metadata['content_type'] = 'class_definition'
                break
        
        # Check if chunk contains a function
        for func_name in structure.functions:
            if f"def {func_name}" in chunk_text:
                metadata['function'] = func_name
                metadata['content_type'] = 'function_definition'
                break
        
        # Check for code examples
        if '```python' in chunk_text or '>>>' in chunk_text:
            metadata['has_code_example'] = True
        
        # Check for parameters
        if ':param' in chunk_text:
            metadata['has_parameters'] = True
        
        # Check for return values
        if ':return' in chunk_text or ':returns:' in chunk_text:
            metadata['has_returns'] = True
        
        return metadata
    
    def _create_flat_chunks(self, text: str, structure: Any) -> List[Chunk]:
        """Create flat chunks without parent-child relationships"""
        chunks_text = self._recursive_split(
            text,
            self.parent_chunk_size,
            self.parent_overlap
        )
        
        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            metadata = self._extract_chunk_metadata(chunk_text, structure)
            metadata['chunk_index'] = i
            metadata['total_chunks'] = len(chunks_text)
            
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                text=chunk_text,
                chunk_type='flat',
                metadata=metadata,
                token_count=self.count_tokens(chunk_text)
            ))
        
        return chunks
    
    def _fallback_chunking(self, text: str, structure: Any) -> List[Chunk]:
        """Fallback to simple chunking if structure-aware fails"""
        logger.warning("Using fallback chunking")
        
        # Simple fixed-size chunking
        chunk_size_chars = self.parent_chunk_size * 4
        overlap_chars = self.parent_overlap * 4
        
        chunks = []
        start = 0
        i = 0
        
        while start < len(text):
            end = start + chunk_size_chars
            chunk_text = text[start:end]
            
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                text=chunk_text,
                chunk_type='fallback',
                metadata={
                    'module': structure.module,
                    'chunk_index': i,
                    'fallback': True
                },
                token_count=self.count_tokens(chunk_text)
            ))
            
            start = end - overlap_chars
            i += 1
        
        return chunks
