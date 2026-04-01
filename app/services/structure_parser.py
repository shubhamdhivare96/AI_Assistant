"""
Structure Parser for Python Documentation
Extracts hierarchical structure from Python docs
"""
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentStructure:
    """Represents parsed document structure"""
    module: Optional[str] = None
    classes: List[str] = None
    functions: List[str] = None
    sections: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.classes is None:
            self.classes = []
        if self.functions is None:
            self.functions = []
        if self.sections is None:
            self.sections = []
        if self.metadata is None:
            self.metadata = {}


class PythonDocStructureParser:
    """Parse Python documentation structure"""
    
    def __init__(self):
        # Patterns for Python documentation
        self.patterns = {
            'module': r'^#\s+(.+?)\s+module',
            'class': r'^class\s+(\w+)',
            'function': r'^def\s+(\w+)',
            'method': r'^\s+def\s+(\w+)',
            'heading_h1': r'^#\s+(.+)$',
            'heading_h2': r'^##\s+(.+)$',
            'heading_h3': r'^###\s+(.+)$',
            'code_block': r'^```python\n(.*?)\n```',
            'parameter': r'^\s*:param\s+(\w+):',
            'returns': r'^\s*:returns?:',
            'example': r'^\s*Example:',
        }
    
    def parse_document(self, text: str, filename: str = "") -> DocumentStructure:
        """
        Parse Python documentation structure
        
        Args:
            text: Document text
            filename: Source filename
        
        Returns:
            DocumentStructure with hierarchy
        """
        try:
            structure = DocumentStructure()
            
            # Extract module name
            structure.module = self._extract_module_name(text, filename)
            
            # Extract classes
            structure.classes = self._extract_classes(text)
            
            # Extract functions
            structure.functions = self._extract_functions(text)
            
            # Extract sections
            structure.sections = self._extract_sections(text)
            
            # Build metadata
            structure.metadata = {
                'filename': filename,
                'module': structure.module,
                'num_classes': len(structure.classes),
                'num_functions': len(structure.functions),
                'num_sections': len(structure.sections),
                'doc_type': self._infer_doc_type(text)
            }
            
            logger.info(
                f"Parsed {filename}: {len(structure.classes)} classes, "
                f"{len(structure.functions)} functions, {len(structure.sections)} sections"
            )
            
            return structure
            
        except Exception as e:
            logger.error(f"Error parsing document structure: {e}")
            return DocumentStructure(metadata={'filename': filename, 'error': str(e)})
    
    def _extract_module_name(self, text: str, filename: str) -> Optional[str]:
        """Extract module name from text or filename"""
        # Try to find module declaration in text
        match = re.search(self.patterns['module'], text, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try to extract from filename
        if filename:
            # e.g., "os.rst" -> "os", "collections.abc.rst" -> "collections.abc"
            module = filename.replace('.rst', '').replace('.md', '').replace('.txt', '')
            return module
        
        return None
    
    def _extract_classes(self, text: str) -> List[str]:
        """Extract class names from text"""
        classes = []
        for match in re.finditer(self.patterns['class'], text, re.MULTILINE):
            class_name = match.group(1)
            classes.append(class_name)
        return list(set(classes))  # Remove duplicates
    
    def _extract_functions(self, text: str) -> List[str]:
        """Extract function names from text"""
        functions = []
        for match in re.finditer(self.patterns['function'], text, re.MULTILINE):
            func_name = match.group(1)
            # Skip private functions (starting with _)
            if not func_name.startswith('_'):
                functions.append(func_name)
        return list(set(functions))
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract document sections with hierarchy"""
        sections = []
        lines = text.split('\n')
        
        current_h1 = None
        current_h2 = None
        current_h3 = None
        
        for i, line in enumerate(lines):
            # H1 heading
            h1_match = re.match(self.patterns['heading_h1'], line)
            if h1_match:
                current_h1 = h1_match.group(1).strip()
                current_h2 = None
                current_h3 = None
                sections.append({
                    'level': 1,
                    'title': current_h1,
                    'line': i,
                    'parent': None
                })
                continue
            
            # H2 heading
            h2_match = re.match(self.patterns['heading_h2'], line)
            if h2_match:
                current_h2 = h2_match.group(1).strip()
                current_h3 = None
                sections.append({
                    'level': 2,
                    'title': current_h2,
                    'line': i,
                    'parent': current_h1
                })
                continue
            
            # H3 heading
            h3_match = re.match(self.patterns['heading_h3'], line)
            if h3_match:
                current_h3 = h3_match.group(1).strip()
                sections.append({
                    'level': 3,
                    'title': current_h3,
                    'line': i,
                    'parent': current_h2 or current_h1
                })
        
        return sections
    
    def _infer_doc_type(self, text: str) -> str:
        """Infer document type from content"""
        text_lower = text.lower()
        
        if 'class ' in text and 'def ' in text:
            return 'api_reference'
        elif 'tutorial' in text_lower or 'guide' in text_lower:
            return 'tutorial'
        elif 'example' in text_lower and '```python' in text:
            return 'example'
        elif ':param' in text or ':returns:' in text:
            return 'docstring'
        else:
            return 'general'
    
    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from documentation"""
        code_blocks = []
        pattern = r'```python\n(.*?)\n```'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            code = match.group(1)
            code_blocks.append({
                'code': code,
                'start': match.start(),
                'end': match.end()
            })
        
        return code_blocks
    
    def extract_function_signature(self, text: str, function_name: str) -> Optional[str]:
        """Extract function signature and docstring"""
        pattern = rf'^def\s+{function_name}\s*\([^)]*\).*?(?=\ndef\s|\nclass\s|$)'
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        
        if match:
            return match.group(0)
        return None
    
    def extract_class_definition(self, text: str, class_name: str) -> Optional[str]:
        """Extract complete class definition"""
        pattern = rf'^class\s+{class_name}\s*[:\(].*?(?=\nclass\s|^def\s|$)'
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        
        if match:
            return match.group(0)
        return None
